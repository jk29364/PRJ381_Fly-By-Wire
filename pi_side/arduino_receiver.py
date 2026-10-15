"""Serial link to the Arduino (ping-pong at 9600 baud).

The Pi sends a control frame with the 7 servo angles; the Arduino answers each valid frame with
one telemetry frame (raw MPU6050 data). All port/baud/timeout settings come from config.py.
This module only does serial I/O in a background thread; it never touches pygame.

Frame layouts are documented at the top of arduino_side/arduino_side.ino.
"""
import struct
import threading
import time

import serial

import config

HEADER = bytes([0x5A, 0xA5])
TELEMETRY_LEN = 16            # 2 header + 1 status + 12 data + 1 checksum

# Link states
STATE_IDLE = "idle"
STATE_OPENING = "opening"     # trying to open the serial port
STATE_WAITING = "waiting"     # port open, waiting for the Arduino to answer
STATE_CONNECTED = "connected" # valid telemetry is arriving
STATE_LOST = "lost"           # was connected, telemetry stopped
STATE_ERROR = "error"         # port could not be opened / serial error (will retry)


def clamp_angle(angle):
    return max(config.SERVO_MIN, min(config.SERVO_MAX, int(round(angle))))


def build_control_frame(angles):
    """Pi -> Arduino: headers + 7 angle bytes (clamped to the servo limits) + XOR checksum & 0x7F."""
    if len(angles) != config.SERVO_COUNT:
        raise ValueError(f"expected {config.SERVO_COUNT} servo angles, got {len(angles)}")
    payload = bytes(clamp_angle(a) for a in angles)
    checksum = 0
    for b in payload:
        checksum ^= b
    return HEADER + payload + bytes([checksum & 0x7F])


def parse_telemetry(buf):
    """Pull the first valid telemetry frame out of `buf` (a bytearray, modified in place).

    Returns the decoded dict, or None if no complete valid frame is buffered yet.
    Garbage and corrupted frames are discarded so the parser always re-synchronises.
    """
    while True:
        start = buf.find(HEADER)
        if start < 0:
            # keep a trailing 0x5A: it may be the first half of the next header
            del buf[:-1 if buf.endswith(HEADER[:1]) else len(buf)]
            return None
        if start > 0:
            del buf[:start]
        if len(buf) < TELEMETRY_LEN:
            return None

        frame = bytes(buf[:TELEMETRY_LEN])
        checksum = 0
        for b in frame[2:TELEMETRY_LEN - 1]:
            checksum ^= b
        if checksum != frame[TELEMETRY_LEN - 1]:
            del buf[:1]                 # false header inside data: skip it and keep looking
            continue

        del buf[:TELEMETRY_LEN]
        status = frame[2]
        ax, ay, az, gx, gy, gz = struct.unpack(">6h", frame[3:15])
        return {
            "imu_ok": status == 0,
            "ax": ax / config.ACCEL_LSB_PER_G,
            "ay": ay / config.ACCEL_LSB_PER_G,
            "az": az / config.ACCEL_LSB_PER_G,
            "gx": gx / config.GYRO_LSB_PER_DPS,
            "gy": gy / config.GYRO_LSB_PER_DPS,
            "gz": gz / config.GYRO_LSB_PER_DPS,
        }


class ArduinoLink:
    def __init__(self):
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._port = None
        self._rx = bytearray()

        self._angles = [config.SERVO_NEUTRAL] * config.SERVO_COUNT
        self._state = STATE_IDLE
        self._message = ""
        self._last_good = 0.0
        self._telemetry = {
            "ax": 0.0, "ay": 0.0, "az": 1.0,
            "gx": 0.0, "gy": 0.0, "gz": 0.0,
            "imu_ok": False, "stream_active": False,
            "seq": 0, "t": 0.0,
        }

    # ------------------------------------------------------------------ public API
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="arduino-link", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        port = self._port
        if port is not None:
            try:                         # best effort: leave the servos centred
                port.write(build_control_frame([config.SERVO_NEUTRAL] * config.SERVO_COUNT))
                port.flush()
            except Exception:
                pass
        self._close_port()
        self._set_state(STATE_IDLE, "")

    def set_servo_angles(self, angles):
        """Latest 7 servo angles in degrees. Values are clamped to 45..135 before sending."""
        frame_angles = [clamp_angle(a) for a in angles]
        if len(frame_angles) != config.SERVO_COUNT:
            raise ValueError(f"expected {config.SERVO_COUNT} servo angles")
        with self._lock:
            self._angles = frame_angles

    def get_latest_data(self):
        with self._lock:
            return dict(self._telemetry)

    def get_status(self):
        """Returns (state, message)."""
        with self._lock:
            return self._state, self._message

    # ------------------------------------------------------------------ internals
    def _set_state(self, state, message=""):
        with self._lock:
            self._state = state
            self._message = message

    def _close_port(self):
        port, self._port = self._port, None
        if port is not None:
            try:
                port.close()
            except Exception:
                pass

    def _open_port(self):
        self._set_state(STATE_OPENING, f"Opening {config.SERIAL_PORT} at {config.BAUD_RATE} baud")
        try:
            self._port = serial.Serial(
                config.SERIAL_PORT,
                config.BAUD_RATE,
                timeout=config.SERIAL_TIMEOUT,
                write_timeout=config.SERIAL_WRITE_TIMEOUT,
            )
        except (serial.SerialException, OSError, ValueError) as e:
            self._port = None
            self._set_state(STATE_ERROR, f"Cannot open {config.SERIAL_PORT}: {e}")
            return False

        self._set_state(STATE_WAITING, "Port open, waiting for the Arduino to boot")
        if self._stop.wait(config.ARDUINO_RESET_DELAY):
            return False
        self._port.reset_input_buffer()
        self._rx.clear()
        self._set_state(STATE_WAITING, "Waiting for the Arduino to answer")
        return True

    def _run(self):
        while not self._stop.is_set():
            if self._port is None:
                if not self._open_port():
                    self._stop.wait(config.RECONNECT_INTERVAL)
                    continue
            try:
                self._exchange()
            except (serial.SerialException, OSError) as e:
                self._close_port()
                with self._lock:
                    self._telemetry["stream_active"] = False
                self._set_state(STATE_ERROR, f"Serial error: {e}")
                self._stop.wait(config.RECONNECT_INTERVAL)

    def _exchange(self):
        """Send one control frame, then wait (up to REPLY_TIMEOUT) for the telemetry answer."""
        with self._lock:
            angles = list(self._angles)
        self._port.write(build_control_frame(angles))

        deadline = time.monotonic() + config.REPLY_TIMEOUT
        while not self._stop.is_set() and time.monotonic() < deadline:
            chunk = self._port.read(max(1, self._port.in_waiting))
            if chunk:
                self._rx.extend(chunk)
            sample = None
            while True:                                  # keep only the newest complete frame
                parsed = parse_telemetry(self._rx)
                if parsed is None:
                    break
                sample = parsed
            if sample is not None:
                self._accept(sample)
                return

        # No answer in time. The frame is simply sent again on the next pass.
        if self._state == STATE_CONNECTED and time.monotonic() - self._last_good > config.LINK_LOST_TIMEOUT:
            with self._lock:
                self._telemetry["stream_active"] = False
            self._set_state(STATE_LOST, "No telemetry from the Arduino")

    def _accept(self, sample):
        now = time.monotonic()
        self._last_good = now
        with self._lock:
            self._telemetry.update(sample)
            self._telemetry["stream_active"] = sample["imu_ok"]
            self._telemetry["seq"] += 1
            self._telemetry["t"] = now
        self._set_state(STATE_CONNECTED, "Arduino connected" if sample["imu_ok"]
                        else "Arduino connected, MPU6050 not responding")

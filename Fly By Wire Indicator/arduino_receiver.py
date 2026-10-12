"""
arduino_receiver.py
--------------------
Separate module that connects to the Arduino (serial / USB / Bluetooth)
and exposes the latest gyroscopic / attitude data through simple variables.

Designed for Raspberry Pi 5. The module auto-discovers common serial ports.
Synthetic data is available only when explicitly enabled for development.

Public API
----------
    start_receiver(port=None, baudrate=9600)
    stop_receiver()
    get_latest_data()  -> dict with at least:
        pitch, roll, ax, ay, az, gx, gy, gz,
        airspeed, altitude, heading, turn_rate, vsi, ball,
        left_aileron_us, right_aileron_us, left_elevator_us,
        right_elevator_us, rudder_us, kill_switch
"""

from __future__ import annotations

import math
import threading
import time
from typing import Optional

# ---------------------------------------------------------------------------
# Optional real serial support
# ---------------------------------------------------------------------------
try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

# ---------------------------------------------------------------------------
# Shared state (updated by background reader thread)
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_running = False
_reader_thread: Optional[threading.Thread] = None
_ser = None

# Latest sensor / attitude values (degrees for pitch/roll)
_data = {
    "ax": 0.0,
    "ay": 0.0,
    "az": 1.0,
    "gx": 0.0,
    "gy": 0.0,
    "gz": 0.0,
    "pitch": 0.0,      # degrees
    "roll": 0.0,       # degrees
    "airspeed": None,
    "altitude": None,
    "heading": None,
    "turn_rate": None,
    "vsi": None,
    "ball": 0.0,
    "left_aileron_us": None,
    "right_aileron_us": None,
    "left_elevator_us": None,
    "right_elevator_us": None,
    "rudder_us": None,
    "kill_switch": None,
    "attitude_available": False,
    "connected": False,
    "last_update": 0.0,
    "receiver_error": None,
}

# Complementary-filter state
_cf_pitch = 0.0
_cf_roll = 0.0
_last_t = time.time()
_alpha = 0.96          # gyro weight (higher = trust gyro more)

# ---------------------------------------------------------------------------
# Attitude estimation from MPU-6050 style data
# ---------------------------------------------------------------------------
def _update_attitude(ax: float, ay: float, az: float,
                     gx: float, gy: float, gz: float) -> None:
    """Complementary filter → pitch & roll in degrees."""
    global _cf_pitch, _cf_roll, _last_t

    now = time.time()
    dt = max(0.001, min(0.1, now - _last_t))
    _last_t = now

    # Accel-only angles (degrees)
    # Convention: pitch positive nose-up, roll positive right-wing-down
    accel_pitch = math.degrees(math.atan2(ay, math.sqrt(ax * ax + az * az)))
    accel_roll  = math.degrees(math.atan2(-ax, az))

    # Integrate gyro (assuming gx/gy are in deg/s)
    _cf_pitch = _alpha * (_cf_pitch + gy * dt) + (1.0 - _alpha) * accel_pitch
    _cf_roll  = _alpha * (_cf_roll  + gx * dt) + (1.0 - _alpha) * accel_roll

    with _lock:
        _data["pitch"] = _cf_pitch
        _data["roll"]  = _cf_roll
        _data["attitude_available"] = True
        _data["ax"] = ax
        _data["ay"] = ay
        _data["az"] = az
        _data["gx"] = gx
        _data["gy"] = gy
        _data["gz"] = gz
        # Turn rate roughly follows yaw-rate gyro (gz)
        _data["turn_rate"] = gz / 30.0          # scale to ~2-min-turn units
        _data["ball"] = max(-1.0, min(1.0, ax * 2.0))  # lateral accel → slip

# ---------------------------------------------------------------------------
# Serial line parser – accepts several common formats
# ---------------------------------------------------------------------------
def _parse_line(line: str) -> None:
    """
    Supported formats (case-insensitive, whitespace ignored):

    1. CSV of six floats (MPU6050 raw):
           ax,ay,az,gx,gy,gz

    2. Keyed tokens:
           P:12.3,R:-4.5
           or pitch=12.3 roll=-4.5
           or AX:0.1 AY:0.2 AZ:0.98 GX:1.2 GY:-0.3 GZ:0.0

    3. Full telemetry (optional extra fields):
           ... AS:120 ALT:3000 HDG:045 VSI:200 ...
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return
    if line.startswith("ERR:"):
        error = line[4:]
        with _lock:
            is_new_error = _data["receiver_error"] != error
            _data["receiver_error"] = error
        if is_new_error:
            print(f"[arduino_receiver] Arduino reported {line}")
        return

    # ---- try pure CSV of 6 numbers first ----
    parts = [p.strip() for p in line.replace(";", ",").split(",")]
    if len(parts) >= 6:
        try:
            vals = [float(p) for p in parts[:6]]
            _update_attitude(*vals)
            # optional extra telemetry after the six sensor values
            if len(parts) >= 7:
                try:
                    with _lock:
                        _data["airspeed"] = float(parts[6])
                except ValueError:
                    pass
            if len(parts) >= 8:
                try:
                    with _lock:
                        _data["altitude"] = float(parts[7])
                except ValueError:
                    pass
            with _lock:
                _data["last_update"] = time.time()
                _data["receiver_error"] = None
            return
        except ValueError:
            pass

    # ---- keyed format ----
    tokens = {}
    for token in line.replace(",", " ").replace(";", " ").split():
        if ":" in token:
            k, v = token.split(":", 1)
        elif "=" in token:
            k, v = token.split("=", 1)
        else:
            continue
        try:
            tokens[k.strip().upper()] = float(v.strip())
        except ValueError:
            continue

    with _lock:
        ax = tokens.get("AX", tokens.get("ACCX", _data["ax"]))
        ay = tokens.get("AY", tokens.get("ACCY", _data["ay"]))
        az = tokens.get("AZ", tokens.get("ACCZ", _data["az"]))
        gx = tokens.get("GX", tokens.get("GYROX", _data["gx"]))
        gy = tokens.get("GY", tokens.get("GYROY", _data["gy"]))
        gz = tokens.get("GZ", tokens.get("GYROZ", _data["gz"]))

    sensor_tokens = ("AX", "AY", "AZ", "GX", "GY", "GZ",
                     "ACCX", "ACCY", "ACCZ", "GYROX", "GYROY", "GYROZ")
    if any(k in tokens for k in sensor_tokens):
        _update_attitude(ax, ay, az, gx, gy, gz)

    with _lock:
        _data["last_update"] = time.time()
        _data["receiver_error"] = None
        if "P" in tokens or "PITCH" in tokens:
            _data["pitch"] = tokens.get("P", tokens.get("PITCH", _data["pitch"]))
            _data["attitude_available"] = True
        if "R" in tokens or "ROLL" in tokens:
            _data["roll"]  = tokens.get("R", tokens.get("ROLL",  _data["roll"]))
            _data["attitude_available"] = True
        if "AS" in tokens or "AIRSPEED" in tokens:
            _data["airspeed"] = tokens.get("AS", tokens.get("AIRSPEED", _data["airspeed"]))
        if "ALT" in tokens or "ALTITUDE" in tokens:
            _data["altitude"] = tokens.get("ALT", tokens.get("ALTITUDE", _data["altitude"]))
        if "HDG" in tokens or "HEADING" in tokens:
            _data["heading"] = tokens.get("HDG", tokens.get("HEADING", _data["heading"]))
        if "VSI" in tokens:
            _data["vsi"] = tokens["VSI"]
        if "BALL" in tokens or "SLIP" in tokens:
            _data["ball"] = tokens.get("BALL", tokens.get("SLIP", _data["ball"]))
        for key in ("left_aileron_us", "right_aileron_us",
                    "left_elevator_us", "right_elevator_us", "rudder_us"):
            token = key.upper()
            if token in tokens:
                _data[key] = tokens[token]
        if "KILL" in tokens:
            _data["kill_switch"] = bool(tokens["KILL"])

# ---------------------------------------------------------------------------
# Background reader thread
# ---------------------------------------------------------------------------
def _reader_loop(port: str, baudrate: int) -> None:
    global _ser, _running
    try:
        _ser = serial.Serial(port, baudrate, timeout=0.05)
        print(f"[arduino_receiver] Connected to {port} @ {baudrate} baud")
        with _lock:
            _data["connected"] = True
        buf = ""
        while _running:
            try:
                chunk = _ser.read(256).decode("utf-8", errors="ignore")
                if chunk:
                    buf += chunk
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        _parse_line(line)
                else:
                    time.sleep(0.005)
            except Exception as e:
                print(f"[arduino_receiver] Read error: {e}")
                time.sleep(0.2)
    except Exception as e:
        print(f"[arduino_receiver] Could not open {port}: {e}")
    finally:
        with _lock:
            _data["connected"] = False
        if _ser and _ser.is_open:
            _ser.close()
        _ser = None

def _mock_loop() -> None:
    """Smooth synthetic motion so the UI can be developed without hardware."""
    global _running
    t0 = time.time()
    while _running:
        t = time.time() - t0
        ax = math.sin(t * 0.7) * 0.25
        ay = math.cos(t * 0.5) * 0.25
        az = 1.0
        gx = math.sin(t * 0.6) * 12.0
        gy = math.cos(t * 0.4) * 10.0
        gz = math.sin(t * 0.3) * 5.0
        _update_attitude(ax, ay, az, gx, gy, gz)
        with _lock:
            _data["airspeed"] = 110.0 + math.sin(t * 0.35) * 25.0
            _data["altitude"] = 2500.0 + math.sin(t * 0.2) * 400.0
            _data["heading"]  = (t * 3.5) % 360.0
            _data["vsi"]      = math.cos(t * 0.25) * 800.0
            _data["last_update"] = time.time()
        time.sleep(0.02)          # ~50 Hz

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def _find_port() -> Optional[str]:
    """Return the first plausible Arduino / serial port."""
    if not HAS_SERIAL:
        return None
    candidates = []
    for p in serial.tools.list_ports.comports():
        desc = (p.description or "").lower()
        dev  = p.device
        if any(x in desc for x in ("arduino", "ch340", "cp210", "ftdi",
                                   "usb serial", "bluetooth")):
            candidates.insert(0, dev)          # prefer known Arduino clones
        elif dev.startswith(("/dev/ttyACM", "/dev/ttyUSB", "/dev/ttyAMA")):
            candidates.append(dev)
        elif dev.startswith("/dev/rfcomm"):
            candidates.insert(0, dev)
    return candidates[0] if candidates else None

def start_receiver(port: Optional[str] = None, baudrate: int = 9600,
                   mock_data: bool = False) -> None:
    """
    Start the background receiver thread.
    If port is None the module auto-detects. Mock data is opt-in for
    development; by default, absent hardware remains visibly unavailable.
    """
    global _running, _reader_thread
    if _running:
        return

    if not HAS_SERIAL:
        if mock_data:
            print("[arduino_receiver] pyserial not installed – using mock data")
            _running = True
            _reader_thread = threading.Thread(target=_mock_loop, daemon=True)
            _reader_thread.start()
        else:
            print("[arduino_receiver] pyserial not installed – live data unavailable")
        return

    chosen = port or _find_port()
    if chosen is None:
        if mock_data:
            print("[arduino_receiver] No serial port found – using mock data")
            _running = True
            _reader_thread = threading.Thread(target=_mock_loop, daemon=True)
            _reader_thread.start()
        else:
            print("[arduino_receiver] No serial port found – live data unavailable")
    else:
        _running = True
        _reader_thread = threading.Thread(
            target=_reader_loop, args=(chosen, baudrate), daemon=True
        )
        _reader_thread.start()

def stop_receiver() -> None:
    """Stop the background thread and close the serial port."""
    global _running
    _running = False
    if _reader_thread and _reader_thread.is_alive():
        _reader_thread.join(timeout=1.5)
    if _ser and _ser.is_open:
        _ser.close()
    print("[arduino_receiver] Stopped")

def get_latest_data() -> dict:
    """
    Return a snapshot of the most recent sensor / attitude values.
    All angles are in degrees.  Safe to call from the main UI thread.
    """
    with _lock:
        snapshot = dict(_data)
    snapshot["stream_active"] = (
        snapshot["last_update"] > 0
        and time.time() - snapshot["last_update"] < 1.5
    )
    return snapshot

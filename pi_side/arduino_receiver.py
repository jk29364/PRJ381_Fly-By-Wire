import serial
import threading
import time
import config
import pygame # Added to poll joystick safely inside the synchronous flow

_serial_port = None
_running = False
_read_thread = None

_latest_telemetry = {
    "ax": 0.0, "ay": 0.0, "az": 1.0,
    "gx": 0.0, "gy": 0.0, "gz": 0.0,
    "stream_active": False
}
_lock = threading.Lock()

def calculate_angle(axis_val):
    angle = int(45 + ((axis_val + 1.0) / 2.0) * 90.0)
    return max(45, min(135, angle))

def _read_loop():
    global _running, _serial_port, _latest_telemetry
    try:
        _serial_port.reset_input_buffer()
        _serial_port.reset_output_buffer()
        
        # Kick off the alternating ping-pong flow by sending an initial dummy packet
        init_packet = [0x5A, 0xA5, 90, 90, 90, 90, 90, 90]
        _serial_port.write(bytes(init_packet))
    except:
        pass

    while _running:
        try:
            if _serial_port and _serial_port.in_waiting > 0:
                line = _serial_port.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith("TELEMETRY:"):
                    data_str = line.replace("TELEMETRY:", "")
                    parts = data_str.split(",")
                    if len(parts) == 6:
                        with _lock:
                            _latest_telemetry["ax"] = float(parts[0])
                            _latest_telemetry["ay"] = float(parts[1])
                            _latest_telemetry["az"] = float(parts[2])
                            _latest_telemetry["gx"] = float(parts[3])
                            _latest_telemetry["gy"] = float(parts[4])
                            _latest_telemetry["gz"] = float(parts[5])
                            _latest_telemetry["stream_active"] = True
                    
                    # TELEMETRY READ SUCCESSFUL -> IMMEDIATELY SEND INTERCEPTED JOYSTICK RESPONSE
                    pygame.event.pump()
                    if pygame.joystick.get_count() > 0:
                        js = pygame.joystick.Joystick(0)
                        yaw_angle   = calculate_angle(js.get_axis(0)) 
                        rollL_angle  = calculate_angle(js.get_axis(1)) 
                        rollR_angle   = calculate_angle(-js.get_axis(1)) 
                        pitch_angle = calculate_angle(js.get_axis(2)) 
                    else:
                        yaw_angle = rollL_angle = rollR_angle = pitch_angle = 90
                        
                    servo_angles = [
                        0x5A, 0xA5, # Safe 2-Byte Structural Alignment Headers
                        yaw_angle, 
                        rollL_angle, 
                        rollR_angle, 
                        pitch_angle, 
                        90, 90 # Structural auxiliary slots
                    ]
                    _serial_port.write(bytes(servo_angles))
                    
        except:
            with _lock:
                _latest_telemetry["stream_active"] = False
            time.sleep(0.01)
        time.sleep(0.001)

def start_receiver(port=None, baudrate=None):
    """Opens the hardware serial port cleanly without any network servers."""
    global _serial_port, _running, _read_thread
    if _running:
        return

    active_port = port if port is not None else config.SERIAL_PORT
    active_baud = baudrate if baudrate is not None else config.BAUD_RATE

    print(f"Connecting to hardware on {active_port} at {active_baud} baud...")
    try:
        _serial_port = serial.Serial(active_port, active_baud, timeout=0.5)
        time.sleep(2) 
        
        _running = True
        _read_thread = threading.Thread(target=_read_loop, daemon=True)
        _read_thread.start()
        print("Hardware tracking thread started successfully.")
    except Exception as e:
        print(f"CRITICAL: Connection failed: {e}")
        with _lock:
            _latest_telemetry["stream_active"] = False

def stop_receiver():
    global _running, _serial_port, _read_thread
    _running = False
    if _read_thread:
        _read_thread.join(timeout=1.0)
    if _serial_port and _serial_port.is_open:
        _serial_port.close()
        print("Serial port connection closed cleanly.")

def get_latest_data():
    with _lock:
        return _latest_telemetry.copy()

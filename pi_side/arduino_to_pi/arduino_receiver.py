import serial
import threading
import time

# --- HARDWARE CONNECTION CONFIGURATION ---
# Central location to adjust your serial port path and communication speeds
SERIAL_CONFIG = {
    "port": "COM8",       # Change to '/dev/ttyACM0' on Raspberry Pi or Linux
    "baudrate": 115200
}

# Threading storage and status variables
_serial_port = None
_running = False
_read_thread = None

# Thread safe dictionary layout holding clean float telemetry metric blocks
_latest_telemetry = {
    "ax": 0.0, "ay": 0.0, "az": 1.0,
    "gx": 0.0, "gy": 0.0, "gz": 0.0,
    "stream_active": False
}
_lock = threading.Lock()

def _read_loop():
    global _running, _serial_port, _latest_telemetry
    
    try:
        _serial_port.reset_input_buffer()
    except:
        pass

    while _running:
        try:
            if _serial_port and _serial_port.in_waiting > 0:
                line = _serial_port.readline().decode('utf-8', errors='ignore').strip()
                
                # Check for explicit telemetry prefix tag
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
        except (serial.SerialException, ValueError, IndexError):
            with _lock:
                _latest_telemetry["stream_active"] = False
            time.sleep(0.01)
        time.sleep(0.001)

def start_receiver(port=None, baudrate=None):
    """Establishes an active Serial connection using configured hardware paths."""
    global _serial_port, _running, _read_thread
    if _running:
        return

    # Use arguments if explicitly passed, otherwise fall back to the central SERIAL_CONFIG variable
    active_port = port if port is not None else SERIAL_CONFIG["port"]
    active_baud = baudrate if baudrate is not None else SERIAL_CONFIG["baudrate"]

    print(f"Connecting to hardware on {active_port} at {active_baud} baud...")
    try:
        _serial_port = serial.Serial(active_port, active_baud, timeout=0.5)
        # Prevent auto-reset crash loops
        time.sleep(2) 
        
        _running = True
        _read_thread = threading.Thread(target=_read_loop, daemon=True)
        _read_thread.start()
        print("Hardware tracking thread started successfully.")
    except Exception as e:
        print(f"CRITICAL: Failed connecting to serial interface: {e}")
        with _lock:
            _latest_telemetry["stream_active"] = False

def stop_receiver():
    """Stops thread loops and terminates active port lines securely."""
    global _running, _serial_port, _read_thread
    _running = False
    if _read_thread:
        _read_thread.join(timeout=1.0)
    if _serial_port and _serial_port.is_open:
        _serial_port.close()
        print("Serial interface connection closed down cleanly.")

def get_latest_data():
    """Returns the latest dictionary object extracted from serial telemetry frames."""
    with _lock:
        return _latest_telemetry.copy()

import serial
import threading
import time
from multiprocessing.managers import BaseManager
import config

_serial_port = None
_running = False
_read_thread = None
_manager_server = None

_latest_telemetry = {
    "ax": 0.0, "ay": 0.0, "az": 1.0,
    "gx": 0.0, "gy": 0.0, "gz": 0.0,
    "stream_active": False
}
_lock = threading.Lock()

# Proxy class so the external joystick file can send data down our open serial port
class SerialProxy:
    def write(self, data):
        global _serial_port
        if _serial_port and _serial_port.is_open:
            _serial_port.write(data)

# Register the proxy class early so the manager factory knows how to route instances
BaseManager.register('get_serial', callable=SerialProxy)

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
        except:
            with _lock:
                _latest_telemetry["stream_active"] = False
            time.sleep(0.01)
        time.sleep(0.001)

def start_receiver(port=None, baudrate=None):
    """OPENS THE HARDWARE PORT AND STARTS THE IPC SERVER"""
    global _serial_port, _running, _read_thread, _manager_server
    if _running:
        return

    active_port = port if port is not None else config.SERIAL_PORT
    active_baud = baudrate if baudrate is not None else config.BAUD_RATE

    print(f"Connecting to hardware on {active_port} at {active_baud} baud...")
    try:
        # HERE IS THE ONLY SERIAL CONNECTION IN THE ENTIRE PROJECT
        _serial_port = serial.Serial(active_port, active_baud, timeout=0.5)
        time.sleep(2) 
        
        _running = True
        _read_thread = threading.Thread(target=_read_loop, daemon=True)
        _read_thread.start()
        print("Hardware tracking thread started.")

        # Start the internal network server so the joystick file can connect to us
        _manager_server = BaseManager(address=('127.0.0.1', 50000), authkey=b'fbw_secret')
        _manager_server.start()
        print("Shared Serial IPC Server active on local port 50000.")

    except Exception as e:
        print(f"CRITICAL: Connection failed: {e}")
        with _lock:
            _latest_telemetry["stream_active"] = False

def stop_receiver():
    global _running, _serial_port, _read_thread, _manager_server
    _running = False
    if _read_thread:
        _read_thread.join(timeout=1.0)
    if _manager_server:
        _manager_server.shutdown()
    if _serial_port and _serial_port.is_open:
        _serial_port.close()
        print("Serial port connection closed cleanly.")

def get_latest_data():
    with _lock:
        return _latest_telemetry.copy()

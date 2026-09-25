import math
import time

def start_receiver(port='/dev/ttyACM0', baudrate=115200):
    """Simulates starting serial connection with Arduino."""
    print(f"Mock receiver started on {port} at {baudrate} baud.")

def stop_receiver():
    """Simulates stopping serial connection."""
    print("Mock receiver stopped.")

def get_latest_data():
    """
    Generates continuous smooth pitch and roll movement 
    for previewing and testing the Attitude Indicator UI layout.
    """
    t = time.time()
    return {
        "ax": math.sin(t) * 0.3,
        "ay": math.cos(t) * 0.3,
        "az": 1.0,
        "gx": math.sin(t) * 15.0,
        "gy": math.cos(t) * 15.0,
        "gz": 0.0
    }

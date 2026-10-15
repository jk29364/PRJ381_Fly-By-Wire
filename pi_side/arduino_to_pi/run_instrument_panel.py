import os
import sys
sys.path.append("attitude_display")

from arduino_receiver import get_latest_data, start_receiver, stop_receiver, SERIAL_CONFIG
from attitude_filter import AttitudeFilter
import instrument_panel

# Initialize filter and a persistent backup dictionary if data drops out
filter = AttitudeFilter()
last = {"pitch": 0.0, "roll": 0.0}

# Save a reference to the original telemetry method structure
original_get_telemetry = instrument_panel.FlightDataStream.get_telemetry

def real_get_telemetry(self):
    data = original_get_telemetry(self)
    raw = get_latest_data()

    # If stream_active is False, display the last verified metrics securely
    if not raw.get("stream_active", False):
        data["pitch"] = last["pitch"]
        data["roll"] = last["roll"]
        data["raw"] = None
        return data

    # Process live IMU frames using the complementary filter coefficients
    pitch, roll = filter.update(raw["ax"], raw["ay"], raw["az"],
                                raw["gx"], raw["gy"], raw["gz"])
    
    last["pitch"] = pitch
    last["roll"] = roll
    
    data["pitch"] = pitch
    data["roll"] = roll
    data["raw"] = raw
    return data

# Inject the real hardware telemetry processor function dynamically
instrument_panel.FlightDataStream.get_telemetry = real_get_telemetry

# Resolve port configurations from environment variables or central config defaults
port = os.environ.get("FBW_TELEMETRY_PORT", SERIAL_CONFIG["port"])
baud = int(os.environ.get("FBW_TELEMETRY_BAUD", str(SERIAL_CONFIG["baudrate"])))

start_receiver(port=port, baudrate=baud)
try:
    instrument_panel.main()
finally:
    stop_receiver()

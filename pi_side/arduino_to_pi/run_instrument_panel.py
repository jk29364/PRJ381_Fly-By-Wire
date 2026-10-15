import os
import sys
import time

# Ensure the script can locate config and arduino_receiver in parent directories if nested
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.append("attitude_display")

import config 
from arduino_receiver import get_latest_data, start_receiver, stop_receiver
from attitude_filter import AttitudeFilter
import instrument_panel

filter = AttitudeFilter()
last = {"pitch": 0.0, "roll": 0.0}

original_get_telemetry = instrument_panel.FlightDataStream.get_telemetry

def real_get_telemetry(self):
    data = original_get_telemetry(self)
    raw = get_latest_data()

    if not raw.get("stream_active", False):
        data["pitch"] = last["pitch"]
        data["roll"] = last["roll"]
        data["raw"] = None
        return data

    pitch, roll = filter.update(raw["ax"], raw["ay"], raw["az"],
                                  raw["gx"], raw["gy"], raw["gz"])
    last["pitch"] = pitch
    last["roll"] = roll
    data["pitch"] = pitch
    data["roll"] = roll
    data["raw"] = raw
    return data

instrument_panel.FlightDataStream.get_telemetry = real_get_telemetry

# --- FIXED: PROTECT RUNTIME EXECUTION FROM SUBPROCESS SPOOFING ---
if __name__ == "__main__":
    # Read environmental targets, falling back cleanly to the shared global config variables
    port = os.environ.get("FBW_TELEMETRY_PORT", config.SERIAL_PORT)
    baud = int(os.environ.get("FBW_TELEMETRY_BAUD", str(config.BAUD_RATE)))

    # START RECEIVER ONCE - This establishes COM8 and starts the IPC Server
    start_receiver(port=port, baudrate=baud)
    time.sleep(1.0) # Settle window for the background thread port allocation

    try:
        instrument_panel.main()
    finally:
        stop_receiver()

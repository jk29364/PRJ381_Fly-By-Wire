import os
import sys
sys.path.append("attitude_display")

from arduino_receiver import get_latest_data, start_receiver, stop_receiver
from attitude_filter import AttitudeFilter
import instrument_panel

filter = AttitudeFilter()

# Last good pitch and roll, shown if the sensor stream stops.
last = {"pitch": 0.0, "roll": 0.0}

original_get_telemetry = instrument_panel.FlightDataStream.get_telemetry

def real_get_telemetry(self):
    data = original_get_telemetry(self)
    raw = get_latest_data()

    # The real receiver has a "stream_active" flag. The old mock receiver doesn't, so we treat it as active.

    if not raw.get("stream_active", True):
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

# If the receiver can't find the Arduino by itself, set FBW_TELEMETRY_PORT
# (for example COM3). FBW_TELEMETRY_BAUD is optional (default 9600).
port = os.environ.get("FBW_TELEMETRY_PORT")
baud = int(os.environ.get("FBW_TELEMETRY_BAUD", "9600"))
start_receiver(port=port, baudrate=baud)
try:
    instrument_panel.main()
finally:
    stop_receiver()

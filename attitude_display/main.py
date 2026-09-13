import sys
sys.path.append("attitude_display")

from arduino_receiver import get_latest_data
from attitude_filter import AttitudeFilter
import instrument_panel

filter = AttitudeFilter()

original_get_telemetry = instrument_panel.FlightDataStream.get_telemetry

def real_get_telemetry(self):
    data = original_get_telemetry(self)
    raw = get_latest_data()
    pitch, roll = filter.update(raw["ax"], raw["ay"], raw["az"],
                                  raw["gx"], raw["gy"], raw["gz"])
    data["pitch"] = pitch
    data["roll"] = roll
    return data

instrument_panel.FlightDataStream.get_telemetry = real_get_telemetry

instrument_panel.main()

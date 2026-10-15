import os
import sys
import time
import pygame

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.append("attitude_display")

import config 
from arduino_receiver import get_latest_data, start_receiver, stop_receiver
from attitude_filter import AttitudeFilter
import instrument_panel

# --- 1. INITIALIZE GLOBAL JOYSTICK ENVIRONMENT ---
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"[SYSTEM] Flight Controls successfully linked: {joystick.get_name()}")
else:
    print("[SYSTEM] WARNING: No joystick detected! Instrument panel running in read-only mode.")

filter = AttitudeFilter()
last = {"pitch": 0.0, "roll": 0.0}

# Reference the original display loop generator
original_get_telemetry = instrument_panel.FlightDataStream.get_telemetry

def real_get_telemetry(self):
    data = original_get_telemetry(self)
    
    # --- PULL MPU6050 TELEMETRY DATA ---
    # The serial write-cycle loop is safely handled inside the background thread now.
    raw = get_latest_data()

    if not raw or not raw.get("stream_active", False):
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

# Inject the unified transceiver loop directly into the display panel
instrument_panel.FlightDataStream.get_telemetry = real_get_telemetry

if __name__ == "__main__":
    port = os.environ.get("FBW_TELEMETRY_PORT", config.SERIAL_PORT)
    baud = int(os.environ.get("FBW_TELEMETRY_BAUD", str(config.BAUD_RATE)))

    # Start the receiver thread (Only opens the port ONCE)
    start_receiver(port=port, baudrate=baud)
    time.sleep(1.0) 

    try:
        instrument_panel.main()
    finally:
        stop_receiver()
        pygame.quit()

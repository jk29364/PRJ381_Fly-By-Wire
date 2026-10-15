import os
import sys
import time
import pygame

# Adjust system path to look for modules in the parent directory structure
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.append("attitude_display")

import config 
from arduino_receiver import get_latest_data, start_receiver, stop_receiver
import arduino_receiver # Imported to access the active serial port object directly
from attitude_filter import AttitudeFilter
import instrument_panel

# --- 1. INITIALIZE GLOBAL JOYSTICK ENVIRONMENT ---
pygame.init()
pygame.joystick.init()

joystick = None
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"[SYSTEM] Flight Controls successfully linked: {joystick.get_name()}")
else:
    print("[SYSTEM] WARNING: No joystick detected! Instrument panel running in read-only mode.")

filter = AttitudeFilter()
last = {"pitch": 0.0, "roll": 0.0}

def calculate_angle(axis_val):
    # Maps a -1.0 -> 1.0 float to a 45 -> 135 integer safely, protecting mechanical linkages
    angle = int(45 + ((axis_val + 1.0) / 2.0) * 90.0)
    return max(45, min(135, angle))

# Reference the original display loop generator
original_get_telemetry = instrument_panel.FlightDataStream.get_telemetry

def real_get_telemetry(self):
    global joystick
    data = original_get_telemetry(self)
    
    # --- STEP A: READ JOYSTICK & TRANSMIT TO SERVOS ---
    # Intercept the single active hardware serial connection managed by the receiver thread
    if joystick and arduino_receiver._serial_port and arduino_receiver._serial_port.is_open:
        try:
            # Refresh pygame's internal joystick axis event states
            pygame.event.pump()
            
            axis_roll_val     = joystick.get_axis(0)
            axis_pitch_val    = joystick.get_axis(1)
            axis_yaw_val      = joystick.get_axis(2)
            
            yaw_angle   = calculate_angle(axis_yaw_val) 
            rollL_angle  = calculate_angle(axis_roll_val) 
            rollR_angle   = calculate_angle(-axis_roll_val) 
            pitch_angle = calculate_angle(axis_pitch_val) 
            aileronL_angle = 90 
            aileronR_angle = 90 
            
            servo_angles = [
                255, # Sync Byte Header
                yaw_angle, 
                rollL_angle, 
                rollR_angle, 
                pitch_angle, 
                aileronL_angle, 
                aileronR_angle
            ]
            
            # Send the payload out directly over the single hardware link
            arduino_receiver._serial_port.write(bytes(servo_angles))
            
            # Debugging printout to verify outputs locally
            print(f"Sending Angles -> Yaw: {yaw_angle}° | RollL: {rollL_angle}° | RollR: {rollR_angle}° | Pitch: {pitch_angle}°", end="   \r")
            
        except Exception as e:
            print(f"\n[SYSTEM] Serial transmission error: {e}")

    # --- STEP B: PULL MPU6050 TELEMETRY DATA ---
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

# Inject the consolidated hybrid transceiver loop directly into the display panel
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

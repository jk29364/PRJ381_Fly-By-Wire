import serial
import pygame
import time

# This file maps joystick axes directly to 0-180 servo angles and sends them as raw bytes
# Created by Johni with help from Gemini

# Change "COM8" to match the path to your Arduino's USB port. On the pi it will be tty something or other
ARDUINO_PORT = "COM8" 
BAUD_RATE = 115200
SERVO_COUNT = 6  # Must match the SERVO_COUNT variable on Arduino sketch

try:
    ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=0.1)
    time.sleep(2) # Give Arduino time to reset
    print(f"Connected to Arduino on {ARDUINO_PORT}")
except Exception as e:
    print(f"Error connecting to Serial: {e}")
    exit()

# Initialize Pygame and Joystick
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("No joystick detected! Plug one in and restart.")
    exit()

joystick = pygame.joystick.Joystick(0)
print(f"Tracking: {joystick.get_name()}")

running = True
clock = pygame.time.Clock()

def calculate_angle(axis_val):
    # Maps a -1.0 -> 1.0 float to a 45 -> 135 integer, clamped safely.
    # Formula: min_angle + ((axis_val + 1.0) / 2.0) * (max_angle - min_angle)
    # The total span is 90 degrees (135 - 45)
    angle = int(45 + ((axis_val + 1.0) / 2.0) * 90.0)
    
    # Clamp tightly to the new boundaries to protect physical linkages
    return max(45, min(135, angle))

while running:
    # Pygame requires checking events to update internal states
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
    # Read raw joystick axis floats (-1.0 to 1.0)
    axis_roll_val     = joystick.get_axis(0)
    axis_pitch_val    = joystick.get_axis(1)
    axis_yaw_val      = joystick.get_axis(2)
    axis_throttle_val = joystick.get_axis(3) # Will artificially control airspeed gauge if implemented.
    
    # 1. Map joystick ranges to final 0-180 degree angles right here in Python
    yaw_angle   = calculate_angle(axis_yaw_val) # Tail left/right
    rollL_angle  = calculate_angle(axis_roll_val) # Left wing up/down
    rollR_angle   = calculate_angle(-axis_roll_val) # Right wing up/down
    pitch_angle = calculate_angle(axis_pitch_val) # Tail up/down
    aileronL_angle = 90 # Left wing aileron up/down
    aileronR_angle = 90 # Right wing aileron up/down 
    # REMEMBER TO ADD BUTTON CONTROLS FOR AILERONS (if they're getting implemented, which they should)
    
    # This packages the angles into a single array. The 255 acts as a shield to soak up buffer startup latency
    servo_angles = [
        255,            # <-- DUMMY SYNC BYTE
        yaw_angle, 
        rollL_angle, 
        rollR_angle, 
        pitch_angle, 
        aileronL_angle, 
        aileronR_angle
    ]
    
    # Pack the integers directly into raw bytes
    payload = bytes(servo_angles)
    ser.write(payload)
    
    # Print locally for debugging (displays the final computed angles going to the hardware)
    print(f"Sending Angles -> Yaw: {yaw_angle}° | RollL: {rollL_angle}° | RollR: {rollR_angle}° | Pitch: {pitch_angle}° | AilL: {aileronL_angle}° | AilR: {aileronR_angle}°", end="   \r")
    
    # Limit to 30 packets per second to keep everything real-time and responsive
    clock.tick(30) 

ser.close()
pygame.quit()
print("\nDisconnected successfully.")

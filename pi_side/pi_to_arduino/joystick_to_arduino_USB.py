import serial
import pygame
import time

# This file should detect one axis of the joystick and send it to a servo connected to pin 8
# Might serve as a skeleton for bluetooth connection mode

# Created by Johni with help from Gemini

# Change "COM6" to match the path to the arduino's USb port (e.g., '/dev/ttyUSB0' on Linux/Mac)
ARDUINO_PORT = "COM6" 
BAUD_RATE = 115200

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
joystick.init()
print(f"Tracking: {joystick.get_name()}")

running = True
clock = pygame.time.Clock()

while running:
    # Pygame requires checking events to update internal states
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
    # Axes: 
    # 0 is tilt left/right
    # 1 is forward/back
    # 2 is rotate left/right
    # 3 is slider
    # Pygame returns a float from -1.0 to 1.0
    axis_val = joystick.get_axis(3) 
    
    # Map -1.0 -> 1.0 to a 0 -> 180 degree integer scale
    servo_angle = int((axis_val + 1.0) * 90)
    
    # Ensure it stays within bounds
    servo_angle = max(0, min(180, servo_angle))
    
    # Send as a single byte over serial with a newline delimiter
    # Adding string encoding prevents raw byte interpretation issues on the Arduino
    payload = f"{servo_angle}\n"
    ser.write(payload.encode('utf-8'))
    
    # Print locally for debugging
    print(f"Joystick: {axis_val:.2f} -> Sent Angle: {servo_angle}", end="\r")
    
    # Limit to 30 packets per second to prevent overloading the serial buffer
    clock.tick(30) 

ser.close()
pygame.quit()

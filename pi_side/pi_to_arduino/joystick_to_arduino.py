import pygame
import time
from multiprocessing.managers import BaseManager
import sys

# --- ACCESS THE SHARED SERIAL PORT IPC VIA CLIENT ---
BaseManager.register('get_serial')
manager = BaseManager(address=('127.0.0.1', 50000), authkey=b'fbw_secret')

print("Connecting to Instrument Panel's serial server...")
connected = False
for attempt in range(10):
    try:
        manager.connect()
        connected = True
        break
    except:
        # Give the instrument panel process a brief moment to boot its server first
        time.sleep(1.0)

if not connected:
    print("Error: Could not connect to the shared serial server! Is the instrument panel running?")
    sys.exit()

# Secure the virtual reference to our shared serial pipeline
ser = manager.get_serial()
print("Successfully hooked into shared Serial Port stream.")

# Initialize Pygame and Joystick
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("No joystick detected! Plug one in and restart.")
    sys.exit()

joystick = pygame.joystick.Joystick(0)
print(f"Tracking: {joystick.get_name()}")

running = True
clock = pygame.time.Clock()

def calculate_angle(axis_val):
    angle = int(45 + ((axis_val + 1.0) / 2.0) * 90.0)
    return max(45, min(135, angle))

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
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
        255, # Dummy Sync
        yaw_angle, 
        rollL_angle, 
        rollR_angle, 
        pitch_angle, 
        aileronL_angle, 
        aileronR_angle
    ]
    
    payload = bytes(servo_angles)
    
    try:
        # This writes data to the serial port managed securely inside the other file's thread!
        ser.write(payload)
    except Exception as e:
        print(f"IPC Write Failure: {e}")
        break
    
    print(f"Sending Angles -> Yaw: {yaw_angle}° | RollL: {rollL_angle}° | RollR: {rollR_angle}° | Pitch: {pitch_angle}° | AilL: {aileronL_angle}° | AilR: {aileronR_angle}°", end="   \r")
    clock.tick(30) 

pygame.quit()
print("\nDisconnected successfully.")

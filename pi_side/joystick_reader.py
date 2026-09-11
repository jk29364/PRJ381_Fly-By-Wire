import os
import sys
import time
import pygame

# Initialize pygame and the joystick module
pygame.init()
pygame.joystick.init()

# Check if a joystick is connected
joystick_count = pygame.joystick.get_count()
if joystick_count == 0:
    print("No joystick detected. Please plug in the Logitech joystick.")
    sys.exit()

# Select the first available joystick
joystick = pygame.joystick.Joystick(0)
joystick.init()

print(f"✅ Successfully connected to: {joystick.get_name()}")
print(f"📊 Number of Axes: {joystick.get_numaxes()}")
print(f"🔴 Number of Buttons: {joystick.get_numbuttons()}")
print(f"🕹️ Number of Hats (D-pads): {joystick.get_numhats()}")
print("-" * 50)
print("Listening for raw inputs... Press Ctrl+C to exit.\n")

try:
    while True:
        # Pump events to refresh the internal state of the joystick
        pygame.event.pump()

        # 1. Read Axes (Analog sticks, sliders, throttles)
        # Returns float values typically between -1.0 and 1.0
        axes_data = []
        for i in range(joystick.get_numaxes()):
            axis_value = joystick.get_axis(i)
            axes_data.append(f"Axis {i}: {axis_value:+.3f}")

        # 2. Read Buttons
        # Returns 1 if pressed, 0 if not pressed
        buttons_data = []
        for i in range(joystick.get_numbuttons()):
            button_value = joystick.get_button(i)
            if button_value:  # Only highlight if pressed for readability
                buttons_data.append(f"B{i}")

        # 3. Read Hats (D-pad)
        # Returns a tuple (x, y) like (0, 0), (-1, 1), etc.
        hats_data = []
        for i in range(joystick.get_numhats()):
            hat_value = joystick.get_hat(i)
            hats_data.append(f"Hat {i}: {hat_value}")

        # Construct the output line
        output = " | ".join(axes_data)
        if buttons_data:
            output += " | Pressed: " + ", ".join(buttons_data)
        if hats_data:
            output += " | " + " | ".join(hats_data)

        # Print to terminal on a single refreshing line
        sys.stdout.write(f"\r{output}")
        sys.stdout.flush()

        # Adjust delay to control output rate (0.05s = 20Hz refresh rate)
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\n\nExiting joystick reader.")
    pygame.quit()

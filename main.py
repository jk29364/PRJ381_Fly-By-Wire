import subprocess
import sys

a2p = subprocess.Popen([sys.executable, "./pi_side/arduino_to_pi/instrument_main.py"])
p2a = subprocess.Popen([sys.executable, "./pi_side/pi_to_arduino/joystick_to_arduino_USB.py"])

print("Both files are running! Press Ctrl+C to stop.")

try:
    # Keep main.py alive so the background files don't close instantly
    a2p.wait()
    p2a.wait()
except KeyboardInterrupt:
    print("\nStopping scripts...")

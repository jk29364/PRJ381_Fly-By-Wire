# --- CENTRAL HARDWARE CONFIGURATION ---
# Every serial setting lives in this file and nowhere else. Change the port here,
# not in arduino_receiver.py or main.py.

# ============================== SERIAL LINK ==============================
# For laptop testing (USB connection)
SERIAL_PORT = "COM6"

# For Raspberry Pi Bluetooth (uncomment when moving to the Pi)
# SERIAL_PORT = "/dev/rfcomm0"

BAUD_RATE = 9600                  # Locked by the project. The Arduino sketch uses Serial.begin(9600).
if BAUD_RATE != 9600:
    raise ValueError("BAUD_RATE must stay at 9600 (the Arduino firmware is fixed to 9600).")

SERIAL_TIMEOUT = 0.02             # s: read granularity inside the link thread
SERIAL_WRITE_TIMEOUT = 0.5        # s: give up on a blocked write
ARDUINO_RESET_DELAY = 2.0         # s: an Uno auto-resets when a USB port is opened, so wait for it to boot
REPLY_TIMEOUT = 0.25              # s: no telemetry this long after a frame -> send the frame again
LINK_LOST_TIMEOUT = 1.0           # s: no valid telemetry this long -> link is reported as LOST
RECONNECT_INTERVAL = 3.0          # s: wait between attempts to (re)open the port

# ============================== CONNECTION SCREEN ==============================
CONNECTED_SCREEN_HOLD = 0.5       # s: how long the screen stays up after the connection succeeds

# ============================== SERVOS ==============================
SERVO_COUNT = 7
# Order of the 7 values sent to the Arduino. The Arduino maps them, in this order, to pins
# D4, D6, D7, D8, D9, D11, D12 (see servoPins[] in arduino_side.ino).
#   byte  pin   control surface              driven by
#   1     D4    rudder                       yaw axis
#   2     D6    tail right                   pitch axis (mirrored)
#   3     D7    tail left                    pitch axis
#   4     D8    right wing inner (flap)      buttons 2 / 4
#   5     D9    right wing outer             roll axis (mirrored)
#   6     D11   left wing inner (flap)       buttons 2 / 4
#   7     D12   left wing outer              roll axis
SERVO_NAMES = ("RUDDER", "TAIL_R", "TAIL_L", "WING_R_INNER", "WING_R_OUTER", "WING_L_INNER", "WING_L_OUTER")
SERVO_MIN = 45                    # no servo may ever be commanded outside 45..135 degrees
SERVO_MAX = 135
SERVO_NEUTRAL = 90

# ============================== JOYSTICK ==============================
AXIS_ROLL = 0
AXIS_PITCH = 1
AXIS_YAW = 2
JOY_DEADZONE = 0.05               # ignore stick noise around centre (0.0 - 1.0)

BUTTON_GYRO_ZERO = 0              # zero the attitude display (local only, nothing is sent to the Arduino)
BUTTON_AILERON_ON = 2             # inner wing servos ("ailerons") 90 -> 45
BUTTON_AILERON_OFF = 4            # inner wing servos 45 -> 90

AILERON_REST_ANGLE = 90
AILERON_L_ACTIVE_ANGLE = 45       # left wing inner
AILERON_R_ACTIVE_ANGLE = 45       # right wing inner

# ============================== MPU6050 SCALE ==============================
# Must match the ranges the Arduino writes to the MPU6050 (+/-2 g, +/-250 deg/s).
ACCEL_LSB_PER_G = 16384.0
GYRO_LSB_PER_DPS = 131.0

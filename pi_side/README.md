# Pi side (ground station)

Run **`main.py`**. It opens a connection status screen, then (0.5 s after the Arduino link is up) the attitude
display. The joystick drives the 7 servos through the Arduino.

## Files

- `config.py`: **all** serial settings (port, baud rate fixed at 9600, timeouts) plus servo limits (45-135),
  joystick axis/button numbers and aileron angles.
- `arduino_receiver.py`: serial link thread. Sends the 7 servo angles, receives raw MPU6050 data.
- `connection_screen.py`: the status screen shown at start-up.
- `main.py`: entry point; joystick -> servo angles, telemetry -> attitude filter -> display.
- `attitude_filter.py`: complementary filter (accelerometer + gyro) by Tshiamo Maise.
- `instrument_panel.py`: pygame attitude indicator (Reabetswe Matake).
- `joystick_tester.py`: prints raw axes/buttons, useful for checking the numbers in `config.py`.
- `instrument_main.py`: old entry point, now just forwards to `main.py`.

## Controls

| Input | Action |
|---|---|
| Axis 0 | Roll: left wing outer (D12) and right wing outer (D9, mirrored) |
| Axis 1 | Pitch: tail left (D7) and tail right (D6, mirrored) |
| Axis 2 | Yaw: rudder (D4) |
| Button 0 | Zero the attitude display (local only, nothing is sent to the Arduino) |
| Button 2 | Inner wing flaps ON: left and right inner (D11, D8) 90° → 45° |
| Button 4 | Inner wing flaps OFF: back to 90° |
| ESC / close window | Quit (servos are centred) |

Servo order on the wire (and the Arduino pins D4, D6, D7, D8, D9, D11, D12):
`RUDDER, TAIL_R, TAIL_L, WING_R_INNER, WING_R_OUTER, WING_L_INNER, WING_L_OUTER`. Every angle is clamped to 45-135.

## Setup

Windows: `pip install pygame pyserial`, set `SERIAL_PORT` in `config.py` (e.g. `"COM8"`), then `python main.py`.

Raspberry Pi: `sudo apt install python3-full python3-pygame python3-pyserial`, connect the HC-06
(`sudo rfcomm connect /dev/rfcomm0 <MAC> 1`), set `SERIAL_PORT = "/dev/rfcomm0"` in `config.py`, then `python main.py`.

If the connection screen shows "CONNECTION FAILED" it retries every few seconds; ESC quits.

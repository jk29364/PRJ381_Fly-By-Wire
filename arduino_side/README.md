# Fly-by-Wire Prototype: Arduino Hardware

Arduino Uno sketches and wiring for the fly-by-wire prototype (7 servos, MPU6050, HC-06 Bluetooth link to the Raspberry Pi 5).

## ⚠️ Disconnect D0 and D1 before uploading

The HC-06 Bluetooth module is wired to **D0 (RX)** and **D1 (TX)**. These are the same pins the Uno uses to talk to the computer over USB, so an attached HC-06 blocks the upload.

**Before you click Upload in the Arduino IDE:**

1. Unplug the jumper wire on **D0** (HC-06 TXD).
2. Unplug the jumper wire on **D1** (to the HC-06 RXD resistor divider).
3. Upload the sketch and wait for **"Done uploading"**.
4. Plug **D0** and **D1** back in.
5. Press the **reset button** on the Uno so the sketch restarts with the HC-06 connected.

Compiling (Verify) works with the wires connected. It is the **upload** that fails.

If you see errors like these, the HC-06 is still connected:

```
not in sync: resp=0x00
unable to open port COM3 for programmer arduino
```

## Pin map

| Uno pin | Connected to |
|---|---|
| D0 (RX) | HC-06 TXD |
| D1 (TX) | 1 kΩ → HC-06 RXD (2 kΩ from that junction to GND) |
| D4 | Rudder signal |
| D6 | Tail right signal |
| D7 | Tail left signal |
| D8 | Right wing inner (button flap) signal |
| D9 | Right wing outer signal |
| D11 | Left wing inner (button flap) signal |
| D12 | Left wing outer signal |
| A4 | MPU6050 SDA |
| A5 | MPU6050 SCL |
| 5V | HC-06 VCC |
| 3.3V | MPU6050 VCC (5V also works) |
| GND | Common ground rail |

The 7 pins above are also the order of the 7 angle bytes the Pi sends (`SERVO_NAMES` in `pi_side/config.py`).
The servo signal wires are the only servo connections that go to the Arduino. See `wiring_diagram.svg`.

HC-06 STATE and EN, and MPU6050 XDA, XCL, AD0 and INT, are left unconnected.

### HC-06 RXD voltage divider

The HC-06 data pins are 3.3 V, but the Uno outputs 5 V:

```
Uno D1 ──[ 1 kΩ ]──┬── HC-06 RXD
                   │
                 [ 2 kΩ ]
                   │
                  GND
```

HC-06 TXD goes straight to Uno D0 with no resistor.

### Servo power

- Power all 7 servos from a separate 5-6 V supply rated 5 A or more, with a 1000 µF capacitor across its + and - rails. Do not use the Uno's 5V pin.
- Every servo: red (V+) to the supply +, brown/black (GND) to the supply -, signal (orange/yellow/white) to its Uno pin.
- The servo supply GND **must** be connected to the Uno GND, otherwise the signal wires have no reference and the servos jitter.
- Set a buck converter's output with a multimeter **before** connecting the servos.

## Serial link (9600 baud, fixed)

The Pi sends a 10-byte control frame (`5A A5`, 7 angles, checksum); the Arduino answers each valid frame with a
16-byte telemetry frame (`5A A5`, status, raw MPU6050 ax ay az gx gy gz, checksum). Details are at the top of
`arduino_side.ino`.

- Angles are clamped to 45-135 on the Pi **and** again on the Arduino.
- If no valid frame arrives for 1 s, all servos return to 90° (`FAILSAFE_MS`).
- Telemetry is binary, so it is not readable in the Serial Monitor.

## Bluetooth notes

- Default HC-06 PIN: `1234` (some modules use `0000`).
- Baud rate: `9600`.
- A fast-blinking HC-06 LED means it is waiting for a connection. A slow double-blink means it is paired.
- On the Pi, open the serial link with `sudo rfcomm connect /dev/rfcomm0 <MAC> 1`, then `screen /dev/rfcomm0 9600`.

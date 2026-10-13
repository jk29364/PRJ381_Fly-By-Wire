# Fly-by-Wire Prototype: Arduino Hardware

Arduino Uno sketches and wiring for the fly-by-wire prototype (5 servos, MPU6050, HC-05 Bluetooth link to the Raspberry Pi 5).

## ⚠️ Disconnect D0 and D1 before uploading

The HC-05 Bluetooth module is wired to **D0 (RX)** and **D1 (TX)**. These are the same pins the Uno uses to talk to the computer over USB, so an attached HC-05 blocks the upload.

**Before you click Upload in the Arduino IDE:**

1. Unplug the jumper wire on **D0** (HC-05 TXD).
2. Unplug the jumper wire on **D1** (to the HC-05 RXD resistor divider).
3. Upload the sketch and wait for **"Done uploading"**.
4. Plug **D0** and **D1** back in.
5. Press the **reset button** on the Uno so the sketch restarts with the HC-05 connected.

Compiling (Verify) works with the wires connected. It is the **upload** that fails.

If you see errors like these, the HC-05 is still connected:

```
not in sync: resp=0x00
unable to open port COM3 for programmer arduino
```

## Pin map

| Uno pin | Connected to |
|---|---|
| D0 (RX) | HC-05 TXD |
| D1 (TX) | 1 kΩ → HC-05 RXD (2 kΩ from that junction to GND) |
| D3 | Left aileron signal |
| D5 | Right aileron signal |
| D6 | Left elevator signal |
| D9 | Right elevator signal |
| D10 | Rudder signal |
| A4 | MPU6050 SDA |
| A5 | MPU6050 SCL |
| 5V | HC-05 VCC |
| 3.3V | MPU6050 VCC (5V also works) |
| GND | Common ground rail |

HC-05 STATE and EN, and MPU6050 XDA, XCL, AD0 and INT, are left unconnected.

### HC-05 RXD voltage divider

The HC-05 data pins are 3.3 V, but the Uno outputs 5 V:

```
Uno D1 ──[ 1 kΩ ]──┬── HC-05 RXD
                   │
                 [ 2 kΩ ]
                   │
                  GND
```

HC-05 TXD goes straight to Uno D0 with no resistor.

### Servo power

- Power the servos from a separate 5-6 V supply (3 A or more) with a 1000 µF capacitor across it. Do not use the Uno's 5V pin.
- The servo supply GND **must** be connected to the Uno GND.

## Bluetooth notes

- Default HC-05 PIN: `1234` (some modules use `0000`).
- Baud rate: `9600`.
- A fast-blinking HC-05 LED means it is waiting for a connection. A slow double-blink means it is paired.
- On the Pi, open the serial link with `sudo rfcomm connect /dev/rfcomm0 <MAC> 1`, then `screen /dev/rfcomm0 9600`.

// Fly-by-wire prototype: Arduino Uno firmware
//
// 7 servos (D4, D6, D7, D8, D9, D11, D12) + MPU6050 (A4 SDA / A5 SCL).
// All data travels over the hardware serial port (D0 RX / D1 TX) at 9600 baud.
//
// Link protocol (ping-pong: the Pi sends a control frame, the Arduino answers with telemetry)
//
//   Pi -> Arduino (10 bytes):
//     0x5A 0xA5 | a0 a1 a2 a3 a4 a5 a6 | checksum
//       a0..a6   servo angles in degrees, in the order of servoPins[] below
//       checksum XOR of a0..a6, then AND 0x7F (so it is always < 0x80)
//
//   Arduino -> Pi (16 bytes):
//     0x5A 0xA5 | status | axH axL ayH ayL azH azL gxH gxL gyH gyL gzH gzL | checksum
//       status   0 = MPU6050 OK, 1 = MPU6050 did not answer (data bytes are zero)
//       values   raw big-endian int16 straight from the MPU6050 (the Pi converts to g and deg/s)
//       checksum XOR of status and the 12 data bytes
//
// Valid angle bytes are <= 135 and the checksum is < 0x80, so 0xA5 can never appear inside a
// valid control frame. That is what lets the receiver re-synchronise cleanly after a lost byte.

#include <Servo.h>
#include <Wire.h>

// ---------------------------------------------------------------- servos
const uint8_t SERVO_COUNT = 7;
// Order = order of the 7 angle bytes sent by the Pi (see SERVO_NAMES in pi_side/config.py):
//   D4 rudder | D6 tail right | D7 tail left | D8 right wing inner | D9 right wing outer
//   D11 left wing inner | D12 left wing outer
const uint8_t servoPins[SERVO_COUNT] = {4, 6, 7, 8, 9, 11, 12};

const uint8_t SERVO_MIN = 45;      // hard mechanical limits: nothing is ever written outside this range
const uint8_t SERVO_MAX = 135;
const uint8_t SERVO_NEUTRAL = 90;

Servo servos[SERVO_COUNT];

// If no valid control frame arrives for this long (Pi crashed, Bluetooth dropped, cable pulled),
// every servo returns to neutral. Set to 0 to disable.
const unsigned long FAILSAFE_MS = 1000;

// ---------------------------------------------------------------- MPU6050
const uint8_t MPU_ADDR = 0x68;     // AD0 low / unconnected

// ---------------------------------------------------------------- link
const uint8_t HEADER_1 = 0x5A;
const uint8_t HEADER_2 = 0xA5;

enum RxState : uint8_t { WAIT_H1, WAIT_H2, PAYLOAD };
RxState rxState = WAIT_H1;
uint8_t rxBuf[SERVO_COUNT + 1];    // 7 angles + checksum
uint8_t rxIdx = 0;
uint8_t rxPrev = 0;

unsigned long lastFrameMs = 0;
bool failsafeActive = false;

// ---------------------------------------------------------------- helpers
uint8_t clampAngle(uint8_t a) {
  if (a < SERVO_MIN) return SERVO_MIN;
  if (a > SERVO_MAX) return SERVO_MAX;
  return a;
}

void writeAllServos(const uint8_t *angles) {
  for (uint8_t i = 0; i < SERVO_COUNT; i++) {
    servos[i].write(clampAngle(angles[i]));
  }
}

void centerAllServos() {
  for (uint8_t i = 0; i < SERVO_COUNT; i++) {
    servos[i].write(SERVO_NEUTRAL);
  }
}

void mpuWrite(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission(true);
}

// Reads two bytes in a fixed order. (Writing (read() << 8) | read() in one expression leaves the
// evaluation order up to the compiler, which can swap the bytes.)
int16_t readInt16() {
  uint8_t hi = Wire.read();
  uint8_t lo = Wire.read();
  return (int16_t)(((uint16_t)hi << 8) | lo);
}

// ---------------------------------------------------------------- setup
void setup() {
  Serial.begin(9600);              // fixed by the project: do not raise

  // Preload neutral so each servo starts on 90 degrees the moment it is attached.
  for (uint8_t i = 0; i < SERVO_COUNT; i++) {
    servos[i].write(SERVO_NEUTRAL);
    servos[i].attach(servoPins[i]);
  }

  Wire.begin();
#if defined(WIRE_HAS_TIMEOUT)
  Wire.setWireTimeout(3000, true); // never let a dead MPU6050 hang the whole sketch
#endif
  mpuWrite(0x6B, 0x00);            // wake up (clear sleep bit)
  mpuWrite(0x1A, 0x03);            // digital low-pass filter ~44 Hz: calmer gyro/accel noise
  mpuWrite(0x1B, 0x00);            // gyro range  +/-250 deg/s  -> 131 LSB per deg/s
  mpuWrite(0x1C, 0x00);            // accel range +/-2 g        -> 16384 LSB per g

  lastFrameMs = millis();
}

// ---------------------------------------------------------------- telemetry
void sendTelemetry() {
  uint8_t frame[16];
  frame[0] = HEADER_1;
  frame[1] = HEADER_2;

  uint8_t status = 1;
  int16_t v[6] = {0, 0, 0, 0, 0, 0};   // ax ay az gx gy gz

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) == 0 &&
      Wire.requestFrom(MPU_ADDR, (uint8_t)14, (uint8_t)true) == 14) {
    v[0] = readInt16();                // ax
    v[1] = readInt16();                // ay
    v[2] = readInt16();                // az
    readInt16();                       // temperature (skipped)
    v[3] = readInt16();                // gx
    v[4] = readInt16();                // gy
    v[5] = readInt16();                // gz
    status = 0;
  }

  frame[2] = status;
  uint8_t checksum = status;
  for (uint8_t i = 0; i < 6; i++) {
    uint8_t hi = (uint8_t)((uint16_t)v[i] >> 8);
    uint8_t lo = (uint8_t)((uint16_t)v[i] & 0xFF);
    frame[3 + i * 2] = hi;
    frame[4 + i * 2] = lo;
    checksum ^= hi ^ lo;
  }
  frame[15] = checksum;

  Serial.write(frame, sizeof(frame));
}

// ---------------------------------------------------------------- control frames
void handleCompleteFrame() {
  uint8_t checksum = 0;
  for (uint8_t i = 0; i < SERVO_COUNT; i++) checksum ^= rxBuf[i];
  if ((checksum & 0x7F) != rxBuf[SERVO_COUNT]) return;          // corrupted: ignore, the Pi will resend

  writeAllServos(rxBuf);
  lastFrameMs = millis();
  failsafeActive = false;
  sendTelemetry();                                      // reply only to a valid control frame
}

void processByte(uint8_t b) {
  switch (rxState) {
    case WAIT_H1:
      if (b == HEADER_1) rxState = WAIT_H2;
      break;

    case WAIT_H2:
      if (b == HEADER_2) {
        rxIdx = 0;
        rxState = PAYLOAD;
      } else if (b != HEADER_1) {
        rxState = WAIT_H1;
      }
      break;

    case PAYLOAD:
      if (b == HEADER_2 && rxPrev == HEADER_1) {        // a new frame started: restart
        rxIdx = 0;
      } else if (b > (rxIdx < SERVO_COUNT ? SERVO_MAX : 0x7F)) {
        rxState = WAIT_H1;                              // impossible in a valid frame: noise
      } else {
        rxBuf[rxIdx++] = b;
        if (rxIdx == SERVO_COUNT + 1) {
          handleCompleteFrame();
          rxState = WAIT_H1;
        }
      }
      break;
  }
  rxPrev = b;
}

void loop() {
  while (Serial.available() > 0) {
    processByte((uint8_t)Serial.read());
  }

  if (FAILSAFE_MS > 0 && !failsafeActive && (millis() - lastFrameMs) > FAILSAFE_MS) {
    centerAllServos();
    failsafeActive = true;
  }
}

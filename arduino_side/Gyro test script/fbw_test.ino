// Fly-by-wire hardware test sketch (Arduino Uno)
// Tests: 5 servos, MPU6050, kill switch, HC-05 link
//
// Serial commands (USB Serial Monitor or over Bluetooth, 9600 baud):
//   1-5 = sweep that servo (1 L aileron, 2 R aileron, 3 L elevator, 4 R elevator, 5 rudder)
//   c   = centre all servos
//   h   = help

#include <Wire.h>
#include <Servo.h>

const int MPU = 0x68;
const int KILL_PIN = 2;
const byte SERVO_PINS[5] = {3, 5, 6, 9, 10};
const char* NAMES[5] = {"Left aileron", "Right aileron", "Left elevator", "Right elevator", "Rudder"};

Servo servos[5];
bool mpuOk = false;
unsigned long lastPrint = 0;

void centerAll() {
  for (byte i = 0; i < 5; i++) servos[i].write(90);
}

void sweep(byte i) {
  Serial.print(F("Sweeping: "));
  Serial.println(NAMES[i]);
  for (int a = 90; a <= 120; a++) { servos[i].write(a); delay(15); }
  for (int a = 120; a >= 60; a--) { servos[i].write(a); delay(15); }
  for (int a = 60; a <= 90; a++)  { servos[i].write(a); delay(15); }
  Serial.println(F("Done"));
}

void printHelp() {
  Serial.println(F("Commands: 1-5 sweep servo, c centre all, h help"));
}

void setup() {
  Serial.begin(9600);
  pinMode(KILL_PIN, INPUT_PULLUP);
  Wire.begin();

  for (byte i = 0; i < 5; i++) servos[i].attach(SERVO_PINS[i]);
  centerAll();

  // MPU6050 check
  Wire.beginTransmission(MPU);
  mpuOk = (Wire.endTransmission() == 0);
  if (mpuOk) {
    Wire.beginTransmission(MPU);
    Wire.write(0x6B);
    Wire.write(0);               // wake up
    Wire.endTransmission(true);
  }

  Serial.println(F("=== Fly-by-wire hardware test ==="));
  Serial.println(mpuOk ? F("MPU6050: FOUND at 0x68") : F("MPU6050: NOT FOUND (check SDA/SCL/VCC/GND)"));
  printHelp();
}

void loop() {
  // Commands
  while (Serial.available()) {
    char c = Serial.read();
    if (c >= '1' && c <= '5') {
      if (digitalRead(KILL_PIN) == LOW) Serial.println(F("Kill switch held, ignoring"));
      else sweep(c - '1');
    } else if (c == 'c') {
      centerAll();
      Serial.println(F("All centred"));
    } else if (c == 'h') {
      printHelp();
    }
  }

  // Kill switch forces neutral
  bool killed = (digitalRead(KILL_PIN) == LOW);
  if (killed) centerAll();

  // Print status twice a second
  if (millis() - lastPrint >= 500) {
    lastPrint = millis();

    Serial.print(F("KILL: "));
    Serial.print(killed ? F("PRESSED") : F("released"));

    if (mpuOk) {
      Wire.beginTransmission(MPU);
      Wire.write(0x3B);
      Wire.endTransmission(false);
      Wire.requestFrom(MPU, 14, true);
      float ax = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.0;
      float ay = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.0;
      float az = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.0;
      Wire.read(); Wire.read();  // skip temperature
      float gx = (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0;
      float gy = (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0;
      float gz = (int16_t)(Wire.read() << 8 | Wire.read()) / 131.0;

      Serial.print(F(" | Accel g: "));
      Serial.print(ax, 2); Serial.print(' ');
      Serial.print(ay, 2); Serial.print(' ');
      Serial.print(az, 2);
      Serial.print(F(" | Gyro dps: "));
      Serial.print(gx, 1); Serial.print(' ');
      Serial.print(gy, 1); Serial.print(' ');
      Serial.print(gz, 1);
    }
    Serial.println();
  }
}

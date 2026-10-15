#include <Servo.h>
#include <Wire.h>

// --- Servo Configuration ---
const int SERVO_COUNT = 6; 
Servo servos[SERVO_COUNT];
const int servoPins[SERVO_COUNT] = {2, 3, 4, 5, 6, 7}; 

// --- MPU6050 I2C Register Address ---
const int MPU_ADDR = 0x68; 

// Timing control for telemetry output (e.g., 30Hz or ~33ms)
unsigned long lastTelemetryTime = 0;
const unsigned long telemetryInterval = 33; 

void setup() {
  Serial.begin(115200);
  
  // Initialize Servos
  for (int i = 0; i < SERVO_COUNT; i++) {
    servos[i].attach(servoPins[i]);
    servos[i].write(90); 
  }

  // Initialize MPU6050 I2C communication
  Wire.begin();
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); // PWR_MGMT_1 register
  Wire.write(0);    // Wake up the MPU6050
  Wire.endTransmission(true);
}

void loop() {
  // 1. Handle INCOMING Servo commands from Python
  handleIncomingServos();

  // 2. Handle OUTGOING MPU6050 data transmission to Python
  unsigned long currentTime = millis();
  if (currentTime - lastTelemetryTime >= telemetryInterval) {
    lastTelemetryTime = currentTime;
    transmitTelemetry();
  }
}

void handleIncomingServos() {
  if (Serial.available() > 0) {
    if (Serial.peek() == 255) {
      if (Serial.available() >= (SERVO_COUNT + 1)) {
        Serial.read(); // Discard the 255 dummy byte
        
        byte angles[SERVO_COUNT];
        Serial.readBytes((char*)angles, SERVO_COUNT);
        
        for (int i = 0; i < SERVO_COUNT; i++) {
          int cleanAngle = constraint(angles[i], 0, 180);
          servos[i].write(cleanAngle);
        }
      }
    } else {
      Serial.read(); // Clear misaligned bytes
    }
  }
}

void transmitTelemetry() {
  int16_t raw_ax, raw_ay, raw_az;
  int16_t raw_gx, raw_gy, raw_gz;
  int16_t raw_temp; // Read temperature to cleanly step past registers

  // Request 14 registers starting from ACCEL_XOUT_H (0x3B)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14, true);

  if (Wire.available() >= 14) {
    raw_ax = (Wire.read() << 8) | Wire.read();
    raw_ay = (Wire.read() << 8) | Wire.read();
    raw_az = (Wire.read() << 8) | Wire.read();
    raw_temp = (Wire.read() << 8) | Wire.read();
    raw_gx = (Wire.read() << 8) | Wire.read();
    raw_gy = (Wire.read() << 8) | Wire.read();
    raw_gz = (Wire.read() << 8) | Wire.read();

    // Convert raw values to standard metric units (Assuming default MPU6050 sensitivities)
    // Accelerometer default range: +/- 2g -> Scale factor = 16384.0 LSB/g
    float ax = (float)raw_ax / 16384.0;
    float ay = (float)raw_ay / 16384.0;
    float az = (float)raw_az / 16384.0;

    // Gyroscope default range: +/- 250 deg/s -> Scale factor = 131.0 LSB/(deg/s)
    float gx = (float)raw_gx / 131.0;
    float gy = (float)raw_gy / 131.0;
    float gz = (float)raw_gz / 131.0;

    // Format output data package securely for simple Python split operations
    Serial.print("TELEMETRY:");
    Serial.print(ax, 4);  Serial.print(",");
    Serial.print(ay, 4);  Serial.print(",");
    Serial.print(az, 4);  Serial.print(",");
    Serial.print(gx, 4);  Serial.print(",");
    Serial.print(gy, 4);  Serial.print(",");
    Serial.println(gz, 4); // Ends package frame with '\n'
  }
}

int constraint(int val, int minVal, int maxVal) {
  if (val < minVal) return minVal;
  if (val > maxVal) return maxVal;
  return val;
}

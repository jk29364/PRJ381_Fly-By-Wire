#include <Servo.h>

// Created by Johni with help from Gemini

Servo servo8;
const int servoPin = 8;

void setup() {
  Serial.begin(115200);      // Must match the Python script baud rate
  servo8.attach(servoPin);  // Attach servo to pin 9
  servo8.write(90);         // Start at the center position
}

void loop() {
  // Check if serial data is waiting
  if (Serial.available() > 0) {
    // Read the incoming string until it hits a newline character
    String inputString = Serial.readStringUntil('\n');
    
    // Convert the string to an integer
    int angle = inputString.toInt();
    
    // Constrain the angle strictly for servo safety
    angle = constraint(angle, 0, 180);
    
    // Move the servo
    servo8.write(angle);
  }
}

// Quick helper to enforce bounds
int constraint(int val, int minVal, int maxVal) {
  if (val < minVal) return minVal;
  if (val > maxVal) return maxVal;
  return val;
}


#include <Pololu3piPlus2040.h>
#include <Scheduler.h>
#include "Odometry.h"
#include <ArduinoJson.h>

//-------------------------
// Hardware Objects
//-------------------------
Motors motors;
Encoders encoders;
ButtonA buttonA;             // Button to toggle motion on/off.
UART myUART(28, 29);         // myUART on GP28 (TX) and GP29 (RX)


// example commands:
// {"vl":150,"vr":150}
// {"vl":300,"vr":300}
//-------------------------
// Odometry Instance
//-------------------------
// Wheel diameter: 37.5 mm, Gear ratio: 75, Encoder pulses per rev: 12, Wheel distance: 98 mm.
Odometry odom(37.5, 75, 12, 98);
int lastRightCount = 0;
int lastLeftCount  = 0;

//-------------------------
// Teleoperation & Velocity Control Variables
//-------------------------
int desiredSpeedLeft = 0;    // Desired left wheel velocity (units as per your system, e.g., mm/s)
int desiredSpeedRight = 0;   // Desired right wheel velocity
unsigned long lastCommandTime = 0;  // Last valid command time (ms)
const unsigned long commandTimeout = 1000;  // Timeout in ms
bool motionEnabled = false;  // When false, motion is disabled regardless of incoming commands

// PI controller gains (tune these to suit your robot)
const float Kp = 1.0;       // Proportional gain
const float Ki = 2.5;        // Integral gain

// Integral error accumulators (for each wheel)
static float intErrorLeft = 0;
static float intErrorRight = 0;

//-------------------------
// Task: Poll myUART for Incoming JSON Commands
//-------------------------
void pollUART() {
  static String uartBuffer = "";
  
  while (myUART.available()) {
    char c = myUART.read();
    if (c == '\n') {
      String jsonMessage = uartBuffer;
      uartBuffer = "";      // Clear the buffer.
      jsonMessage.trim();   // Remove stray whitespace.
      
      if (jsonMessage.length() > 0) {
        StaticJsonDocument<128> doc;
        DeserializationError error = deserializeJson(doc, jsonMessage);
        if (error) {
          myUART.print("JSON Parse Error: ");
          myUART.println(error.c_str());
        } else if (doc.containsKey("vl") && doc.containsKey("vr")) {
          desiredSpeedLeft = doc["vl"];
          desiredSpeedRight = doc["vr"];
          lastCommandTime = millis();
          Serial.print("Updated speeds - Left: ");
          Serial.print(desiredSpeedLeft);
          Serial.print(" Right: ");
          Serial.println(desiredSpeedRight);
        } else {
          myUART.println("Missing keys in JSON command");
        }
      }
    } else {
      uartBuffer += c;
    }
  }
  yield();
}

//-------------------------
// Task: Merged Control Task with Velocity PI Control
//-------------------------
//
// This task updates the odometry and implements a velocity PI controller for each wheel.
// It runs at a fixed frequency (approximately every 10 ms for odometry updates).

void controlTask() {
  static unsigned long lastTimeMicros = micros();
  unsigned long nowMicros = micros();
  
  if (nowMicros - lastTimeMicros >= 10000UL) {  // ~10 ms interval.
    unsigned long dtMicros = nowMicros - lastTimeMicros;
    lastTimeMicros = nowMicros;
    
    // Calculate dtControl in seconds using dtMicros.
    float dtControl = dtMicros / 1000000.0;
    
    // --- Odometry Update ---
    int currentRight = encoders.getCountsRight();
    int currentLeft  = encoders.getCountsLeft();
    
    int deltaRight = currentRight - lastRightCount;
    int deltaLeft  = currentLeft - lastLeftCount;
    
    lastRightCount = currentRight;
    lastLeftCount = currentLeft;
    
    odom.update(deltaRight, deltaLeft, dtMicros);
    
    // --- Velocity Control ---
    if (!motionEnabled) {
      // When motion is disabled, reset speeds and integrators.
      desiredSpeedLeft = 0;
      desiredSpeedRight = 0;
      intErrorLeft = 0;
      intErrorRight = 0;
      motors.setSpeeds(0, 0);
    } else {
      // Check for communication timeout.
      if (millis() - lastCommandTime > commandTimeout) {
        desiredSpeedLeft = 0;
        desiredSpeedRight = 0;
        intErrorLeft = 0;
        intErrorRight = 0;
        Serial.println("Command timeout. Stopping motors.");
      }
      
      // Compute PI controller for the left wheel:
      float errorLeft = (float)desiredSpeedLeft - odom.v_left;
      intErrorLeft += errorLeft * dtControl;
      float outputLeft = Kp * errorLeft + Ki * intErrorLeft;
      
      // Compute PI controller for the right wheel:
      float errorRight = (float)desiredSpeedRight - odom.v_right;
      intErrorRight += errorRight * dtControl;
      float outputRight = Kp * errorRight + Ki * intErrorRight;
      
      // Saturate outputs to the range [-400, 400]
      if (outputLeft > 400) outputLeft = 400;
      if (outputLeft < -400) outputLeft = -400;
      if (outputRight > 400) outputRight = 400;
      if (outputRight < -400) outputRight = -400;
      
      motors.setSpeeds((int)outputLeft, (int)outputRight);
    }
  }
  
  yield();
}

//-------------------------
// Task: Send Odometry Data via myUART
//-------------------------
//
// This task sends a JSON-formatted string containing the current odometry every 100 ms.
void sendOdometryTask() {
  static unsigned long lastSentTime = 0;
  unsigned long now = millis();
  
  if (now - lastSentTime >= 100) {
    lastSentTime = now;
    
    StaticJsonDocument<128> doc;
    doc["x"] = odom.posX;
    doc["y"] = odom.posY;
    doc["theta"] = odom.theta * 57.2958;  // Convert radians to degrees.
    doc["vL"] = odom.v_left;
    doc["vR"] = odom.v_right;
    
    char outBuffer[128];
    size_t n = serializeJson(doc, outBuffer, sizeof(outBuffer));
    myUART.write((const uint8_t*)outBuffer, n);
    myUART.write((const uint8_t*)"\n", 1);
    
    Serial.print("Sent odometry: ");
    Serial.println(outBuffer);
  }
  yield();
}

//-------------------------
// Setup and Main Loop
//-------------------------
void setup() {
  Serial.begin(115200);
  delay(100);
  
  myUART.begin(115200, SERIAL_8N1);
  Serial.println("Teleoperation control with PI velocity loop starting over myUART");
  
  // Initialize encoder counts.
  lastRightCount = encoders.getCountsRight();
  lastLeftCount = encoders.getCountsLeft();
  
  // Initialize the last command time.
  lastCommandTime = millis();
  
  // Start scheduled tasks.
  Scheduler.startLoop(pollUART);
  Scheduler.startLoop(controlTask);     // Merged control (odometry update + PI control)
  Scheduler.startLoop(sendOdometryTask);
}

void loop() {
  // --- ButtonA Check in Main Loop ---
  // Toggle motionEnabled on a rising edge of ButtonA press.
  static bool lastButtonState = false;
  bool currentState = buttonA.isPressed();
  if (currentState && !lastButtonState) {
    motionEnabled = !motionEnabled;
    Serial.print("Motion ");
    Serial.println(motionEnabled ? "Enabled" : "Disabled");
  }
  lastButtonState = currentState;
  
  yield();
}

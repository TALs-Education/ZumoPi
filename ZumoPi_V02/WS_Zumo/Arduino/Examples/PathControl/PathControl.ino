#include <Pololu3piPlus2040.h>
#include <Scheduler.h>
#include "Odometry.h"
#include "PathController.h"

// Global hardware objects.
Motors motors;
Encoders encoders;
ButtonA buttonA;  // Button to trigger the path start.

// Create an Odometry instance with your parameters:
// Wheel diameter: 37.5 mm, Gear ratio: 75, Encoder pulses per rev: 12, Wheel distance: 98 mm.
Odometry odom(37.5, 75, 12, 98);

// Create a PathController instance.
PathController pathCtrl;

// Define desired path (coordinates in mm).
float desiredPath[][2] = {
  {100, 0},
  {200, 100},
  {500, 100}
};
const int numPoints = sizeof(desiredPath) / sizeof(desiredPath[0]);

// Global variables to hold previous encoder counts.
int lastRightCount = 0;
int lastLeftCount  = 0;

// Flag to indicate that the path is active.
bool pathActive = false;

// For button edge detection.
bool lastButtonState = false;

//--------------------------------------------------
// Odometry and Path Update Task (100 Hz)
//--------------------------------------------------
void updateTask() {
  static unsigned long lastTimeMicros = micros();
  unsigned long nowMicros = micros();
  
  if (nowMicros - lastTimeMicros >= 10000UL) {  // Only run if 10,000 µs (10 ms) have passed.
    unsigned long dtMicros = nowMicros - lastTimeMicros;
    lastTimeMicros = nowMicros;
    
    int currentRight = encoders.getCountsRight();
    int currentLeft  = encoders.getCountsLeft();
    
    int deltaRight = currentRight - lastRightCount;
    int deltaLeft  = currentLeft  - lastLeftCount;
    
    lastRightCount = currentRight;
    lastLeftCount  = currentLeft;
    
    // Update odometry with the measured dt.
    odom.update(deltaRight, deltaLeft, dtMicros);
    
    // If the path is active, update the path controller and send motor commands.
    if (pathActive) {
      pathCtrl.update(odom, desiredPath, numPoints);
      motors.setSpeeds(pathCtrl.currentCommands.leftSpeed, pathCtrl.currentCommands.rightSpeed);
    }
  }
  yield();
}

//--------------------------------------------------
// Serial Output Task (every 10 ms)
//--------------------------------------------------
void serialTask() {
  static unsigned long lastPrint = 0;
  unsigned long now = millis();
  if (now - lastPrint >= 10) {  // every 10 ms
    lastPrint = now;
    char buf[100];
    // Odometry
    //snprintf(buf, sizeof(buf), "X: %.2f mm, Y: %.2f mm, Theta: %.2f deg, vL: %.2f mm/s, vR: %.2f mm/s", 
    //         odom.posX, odom.posY, odom.theta * 57.2958, odom.v_left, odom.v_right);
    
    // car states control         
    snprintf(buf, sizeof(buf), "X: %.2f mm, Y: %.2f mm, Theta: %.2f deg, de: %.2f mm/s, theta_t: %.2f mm/s", 
             pathCtrl.car_state.posx, pathCtrl.car_state.posy, pathCtrl.car_state.theta * 57.2958, pathCtrl.path_state.de, pathCtrl.path_state.theta_t);    
    // wheels controller performance:
//    snprintf(buf, sizeof(buf),"vL actual: %.2f mm/s, vR actual: %.2f mm/s vL target: %.2f mm/s, vR target: %.2f mm/s ",
//             odom.v_left, odom.v_right,pathCtrl.v_l_target, pathCtrl.v_r_target);
    Serial.println(buf);
  }
  yield();
}

//--------------------------------------------------
// Setup and Main Loop
//--------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(100);
  
  // Initialize the PathController.
  pathCtrl.begin();
  
  // Initialize encoder counts.
  lastRightCount = encoders.getCountsRight();
  lastLeftCount  = encoders.getCountsLeft();
  
  // Start the merged update and serial tasks.
  Scheduler.startLoop(updateTask);
  Scheduler.startLoop(serialTask);
}

void loop() {
  // Button edge detection: if Button A is pressed now but wasn't last loop...
  bool currentButtonState = buttonA.isPressed();
  if (currentButtonState && !lastButtonState) {
    // Reset odometry and the path controller on each new button press.
    odom.reset();
    pathCtrl.reset();
    pathActive = true;
    //Serial.println("Path started (odometry and car state reset)");
  }
  lastButtonState = currentButtonState;
  
  yield();  // Main loop yields since tasks run under Scheduler.
}

#include <Pololu3piPlus2040.h>
#include <Scheduler.h>
#include "Odometry.h"

//-------------------------
// Hardware Objects
//-------------------------
Motors motors;
Encoders encoders;
ButtonA buttonA;  // Button to trigger the motion sequence

//-------------------------
// Odometry Instance
//-------------------------
// Wheel diameter: 37.5 mm, Gear ratio: 75, Encoder pulses per rev: 12, Wheel distance: 98 mm.
Odometry odom(37.5, 75, 12, 98);

//-------------------------
// Global Encoder Variables
//-------------------------
int lastRightCount = 0;
int lastLeftCount  = 0;

//-------------------------
// Non-Blocking Motion Variables
//-------------------------
enum Movement { 
  MOVE_FORWARD, 
  TURN_RIGHT, 
  STOP 
};

struct MovementCommand {
  Movement command;         // Command being executed
  unsigned long duration;   // Duration in ms
  unsigned long startTime;  // When the command started
  bool active;              // True if a movement is in progress
};

MovementCommand currentMovement = { STOP, 0, 0, false };

// Motion sequence variables:
// State 0: move forward for 1 sec
// State 1: turn right for 575 ms
// State 2: sequence complete.
bool motionSequenceActive = false;
int motionSequenceState = 0;

//
// move() sets the motor speeds based on the command for a specified duration,
// without blocking the rest of the code.
void move(Movement command, unsigned long duration) {
  if (!currentMovement.active) {
    currentMovement.command = command;
    currentMovement.duration = duration;
    currentMovement.startTime = millis();
    currentMovement.active = true;
    
    switch (command) {
      case MOVE_FORWARD:
        motors.setSpeeds(200, 200);
        Serial.println("Moving forward");
        break;
      case TURN_RIGHT:
        // For a right turn, left motor moves forward while right motor moves reverse.
        motors.setSpeeds(200, -200);
        Serial.println("Turning right");
        break;
      case STOP:
      default:
        motors.setSpeeds(0, 0);
        break;
    }
  }
}

//
// updateMovement() checks if the current movement duration has elapsed.
// If so, it stops the motors and marks the movement as complete.
void updateMovement() {
  if (currentMovement.active && (millis() - currentMovement.startTime >= currentMovement.duration)) {
    motors.setSpeeds(0, 0);
    currentMovement.active = false;
  }
}

//-------------------------
// Motion Sequence Task
//-------------------------
//
// motionTask() is scheduled to run continuously. When Button A is pressed,
// it resets the odometry and starts a motion sequence that moves forward for 1 sec
// then turns right for 575 ms.
void motionTask() {
  updateMovement();
  
  // Start a new sequence when Button A is pressed.
  if (!motionSequenceActive && buttonA.isPressed()) {
    odom.reset();  // Reset odometry when the sequence starts.
    Serial.println("Odometry reset; starting motion sequence");
    motionSequenceActive = true;
    motionSequenceState = 0;
  }
  
  // If a sequence is active and no movement is running, issue the next command.
  if (motionSequenceActive && !currentMovement.active) {
    if (motionSequenceState == 0) {
      // Move forward for 1 second.
      move(MOVE_FORWARD, 1000);
      motionSequenceState = 1;
    } else if (motionSequenceState == 1) {
      // Turn right for 575 ms.
      move(TURN_RIGHT, 575);
      motionSequenceState = 2;
    } else if (motionSequenceState == 2) {
      // Sequence complete.
      motionSequenceActive = false;
      Serial.println("Motion sequence complete");
    }
  }
  
  yield();
}

//-------------------------
// Odometry Update Task
//-------------------------
// encoderOdometryTask() runs at approximately 100 Hz (every ~10 ms). It reads the encoder counts,
// computes the deltas, calculates dt in microseconds, updates the odometry, and prints the updated pose.
void encoderOdometryTask() {
  static unsigned long lastTimeMicros = micros();
  unsigned long nowMicros = micros();
  if (nowMicros - lastTimeMicros >= 10000UL) {  // 10,000 µs = 10 ms interval.
    unsigned long dtMicros = nowMicros - lastTimeMicros;
    lastTimeMicros = nowMicros;
    
    int currentRight = encoders.getCountsRight();
    int currentLeft  = encoders.getCountsLeft();
    
    int deltaRight = currentRight - lastRightCount;
    int deltaLeft  = currentLeft - lastLeftCount;
    
    lastRightCount = currentRight;
    lastLeftCount = currentLeft;
    
    // Update odometry with the incremental counts and measured dt (in µs).
    odom.update(deltaRight, deltaLeft, dtMicros);
    
    // Print the updated pose and wheel velocities.
    char buf[80];
    snprintf(buf, sizeof(buf), "X: %.2f mm, Y: %.2f mm, Theta: %.2f deg, vL: %.2f, vR: %.2f",
             odom.posX, odom.posY, odom.theta * 57.2958, odom.v_left, odom.v_right);
    Serial.println(buf);
  }
  
  yield();
}

//-------------------------
// Setup and Main Loop
//-------------------------
void setup() {
  Serial.begin(115200);
  delay(100);
  
  // Initialize encoder counts.
  lastRightCount = encoders.getCountsRight();
  lastLeftCount = encoders.getCountsLeft();
  
  // Start the scheduled tasks:
  // - encoderOdometryTask: Updates odometry at ~100 Hz.
  // - motionTask: Monitors Button A and executes the motion sequence.
  Scheduler.startLoop(encoderOdometryTask);
  Scheduler.startLoop(motionTask);
}

void loop() {
  yield(); // All work is done in the scheduled tasks.
}

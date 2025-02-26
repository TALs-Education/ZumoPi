#include <Pololu3piPlus2040.h>
#include <Scheduler.h>

Encoders encoders;
Motors motors;
ButtonA buttonA;

// Define a state machine for driving
enum DrivingState {
  IDLE,           // Waiting for button press
  FORWARD,        // Driving forward
  REVERSE,        // Driving in reverse
  WAIT_FOR_RELEASE // Wait until button is released to avoid retriggering
};

DrivingState driveState = IDLE;
unsigned long stateStartTime = 0; // To track state durations

// Encoder task: reads encoder counts and sends them over Serial every 100ms.
void encoderTask() {
  static unsigned long lastSerialTime = 0;
  unsigned long currentMillis = millis();
  
  if (currentMillis - lastSerialTime >= 100) {
    lastSerialTime = currentMillis;
    int16_t countsLeft = encoders.getCountsLeft();
    int16_t countsRight = encoders.getCountsRight();
    
    char report[80];
    snprintf_P(report, sizeof(report), PSTR("%6d %6d"), countsLeft, countsRight);
    Serial.println(report);
  }
  
  yield(); // Ensure other tasks get processor time.
}

// Driving task: non-blocking state machine to run the drive sequence.
void drivingTask() {
  unsigned long currentMillis = millis();
  
  switch (driveState) {
    case IDLE:
      // When the button is pressed, start the drive sequence.
      if (buttonA.isPressed()) {
        driveState = FORWARD;
        stateStartTime = currentMillis;
        motors.setSpeeds(200, 200); // Drive forward
      }
      break;
      
    case FORWARD:
      // After 1 second in forward mode, switch to reverse.
      if (currentMillis - stateStartTime >= 1000) {
        driveState = REVERSE;
        stateStartTime = currentMillis;
        motors.setSpeeds(-200, -200); // Reverse
      }
      break;
      
    case REVERSE:
      // After 1 second in reverse mode, stop the motors.
      if (currentMillis - stateStartTime >= 1000) {
        driveState = WAIT_FOR_RELEASE;
        motors.setSpeeds(0, 0); // Stop
      }
      break;
      
    case WAIT_FOR_RELEASE:
      // Wait for the button to be released so that the sequence isn't retriggered.
      if (!buttonA.isPressed()) {
        driveState = IDLE;
      }
      break;
  }
  
  yield(); // Pass control to other tasks.
}

void setup() {
  Serial.begin(115200);
  
  // Start the encoder and driving tasks using the Scheduler.
  Scheduler.startLoop(encoderTask);
  Scheduler.startLoop(drivingTask);
}

void loop() {
  // The main loop can remain empty (or can call yield) because all
  // work is done in the scheduled tasks.
  yield();
}

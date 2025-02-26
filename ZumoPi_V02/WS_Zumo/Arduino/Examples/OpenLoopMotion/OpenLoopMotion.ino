#include <Pololu3piPlus2040.h>
#include <Scheduler.h>

Motors motors;
Encoders encoders;
ButtonA buttonA;  // Button to trigger the movement sequence

// Define possible movement commands.
enum Movement { 
  MOVE_FORWARD, 
  MOVE_REVERSE, 
  TURN_RIGHT, 
  TURN_LEFT, 
  STOP 
};

// Structure to hold the current movement command.
struct MovementCommand {
  Movement command;         // Which command is being executed.
  unsigned long duration;   // How long the movement should last (ms).
  unsigned long startTime;  // When the command started.
  bool active;              // Is a movement currently active?
};

MovementCommand currentMovement = { STOP, 0, 0, false };
// Sequence counter: 0: forward, 1: reverse, 2: turn right, 3: turn left.
// When sequence reaches 4, the sequence is complete.
int sequence = 0;
// Flag to indicate if a sequence is currently active.
bool sequenceActive = false;

//
// move() accepts a movement command and duration (in ms) and immediately
// sets the motor speeds accordingly in a non blocking way.
void move(Movement command, unsigned long duration) {
  if (!currentMovement.active) {
    currentMovement.command = command;
    currentMovement.duration = duration;
    currentMovement.startTime = millis();
    currentMovement.active = true;
    
    switch (command) {
      case MOVE_FORWARD:
        motors.setSpeeds(200, 200);
        break;
      case MOVE_REVERSE:
        motors.setSpeeds(-200, -200);
        break;
      case TURN_RIGHT:
        // Left motor forward, right motor reverse for a right turn.
        motors.setSpeeds(200, -200);
        break;
      case TURN_LEFT:
        // Left motor reverse, right motor forward for a left turn.
        motors.setSpeeds(-200, 200);
        break;
      case STOP:
      default:
        motors.setSpeeds(0, 0);
        break;
    }
  }
}

//
// updateMovement() checks if the active movement's duration has elapsed.
// If it has, the motors are stopped and the movement command is marked complete.
void updateMovement() {
  if (currentMovement.active && (millis() - currentMovement.startTime >= currentMovement.duration)) {
    motors.setSpeeds(0, 0);
    currentMovement.active = false;
  }
}

//
// movementSequenceTask() is scheduled to run continuously.
// When Button A is pressed (and no sequence is running), it starts a sequence.
// Then, as each non blocking movement completes, it steps through the 4 commands.
void movementSequenceTask() {
  updateMovement();
  
  // If no sequence is active, check if the button is pressed to start one.
  if (!sequenceActive) {
    if (buttonA.isPressed()) {
      sequenceActive = true;
      sequence = 0;
      Serial.println("Starting movement sequence");
    }
  }
  
  // If a sequence is active and no movement is running, issue the next command.
  if (sequenceActive && !currentMovement.active) {
    if (sequence < 4) {
      switch (sequence) {
        case 0:
          Serial.println("Moving forward");
          move(MOVE_FORWARD, 1000);
          break;
        case 1:
          Serial.println("Moving reverse");
          move(MOVE_REVERSE, 1000);
          break;
        case 2:
          Serial.println("Turning right");
          move(TURN_RIGHT, 1000);
          break;
        case 3:
          Serial.println("Turning left");
          move(TURN_LEFT, 1000);
          break;
      }
      sequence++; // Advance to the next command.
    } else {
      // Sequence complete.
      sequenceActive = false;
      Serial.println("Sequence complete");
    }
  }
  
  yield();
}

//
// encoderTask() reads the encoder counts every 100ms and sends them to Serial.
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
  
  yield();
}

//
// In setup() we initialize Serial and start the Scheduler tasks.
void setup() {
  Serial.begin(115200);
  delay(100);
  
  Scheduler.startLoop(encoderTask);
  Scheduler.startLoop(movementSequenceTask);
}

//
// The main loop remains empty since all work is done in the scheduled tasks.
void loop() {
  yield();
}

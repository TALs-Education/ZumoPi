#include <Wire.h>
#include <SparkFun_VL53L5CX_Library.h>  // VL53L5CX sensor library
#include <Pololu3piPlus2040.h>          // Pololu 3pi+ 2040 API

// Create sensor and control objects.
Motors motors;
ButtonA buttonA;

SparkFun_VL53L5CX myImager;
VL53L5CX_ResultsData measurementData;

// Global variables for sensor resolution.
int imageResolution = 0;  // Total number of pads (64 for 8x8 mode)
int imageWidth = 0;       // Grid width (8 for 8x8 mode)

// Sensor assumed horizontal field-of-view in degrees.
#define H_FOV 45.0  

// Control parameters.
const float DESIRED_DISTANCE = 100.0; // Target distance (mm)
const float ANGLE_THRESHOLD  = H_FOV/4;   // Angle threshold (degrees)
const float KP_DISTANCE      = 2.0;    // Proportional gain for distance error
const float KP_ANGLE         = 10;   // Proportional gain for angular error
const int   MAX_SPEED        = 200;    // Maximum motor speed (-400 to 400)



// Update the minDistance array with the minimum distance per column
// from the two center rows of the sensor image.
void updateMinDistances(int minDistance[]) {
  int centerRowOffset = imageWidth / 2 - 1; // For 8x8, center rows are 3 & 4.
  for (int col = 0; col < imageWidth; col++) {
    int idx1 = centerRowOffset * imageWidth + col;
    int idx2 = (centerRowOffset + 1) * imageWidth + col;
    int d1 = measurementData.distance_mm[idx1];
    int d2 = measurementData.distance_mm[idx2];
    minDistance[col] = (d2 < d1) ? d2 : d1;
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Zumo Control with VL53L5CX");

  // Initialize I2C.
  Wire.begin();
  Wire.setClock(1000000);

  // Initialize the sensor.
  Serial.println("Initializing VL53L5CX sensor...");
  if (!myImager.begin()) {
    Serial.println("Sensor not found - check wiring!");
    while (1);
  }
  
  // Use 8x8 mode.
  myImager.setResolution(4*4);
  imageResolution = myImager.getResolution();
  imageWidth = sqrt(imageResolution); // For 8x8, imageWidth = 8
  myImager.setRangingFrequency(60); // max 60Hz for 4x4 and 15Hz for 8x8

  myImager.startRanging();

  // Wait for Button A press to start the motion sequence.
  Serial.println("Press Button A to START motion.");
  while (!buttonA.isPressed()) {
    delay(10);
  }
  // Wait for button release to debounce.
  while (buttonA.isPressed()) {
    delay(10);
  }
  Serial.println("Motion sequence started.");
}

void loop() {
  
  // If Button A is pressed during operation, stop the motors and exit.
  if (buttonA.isPressed()) {
    motors.setSpeeds(0, 0);
    Serial.println("Motion sequence stopped. Motors off.");
    // Wait for button release.
    while (buttonA.isPressed()) {
      delay(10);
    }
    // Stop running by entering an infinite loop.
    while (true) {
      delay(10);
    }
  }
  // If new sensor data is ready, process it.
  if (myImager.isDataReady()) {
    if (myImager.getRangingData(&measurementData)) {
      // Compute minimum distances per column (center rows only).
      int minDistance[8];  // Maximum grid width is 8.
      updateMinDistances(minDistance);

      // Print the per-column distances.
      Serial.print("Min per column (center rows): ");
      for (int i = 0; i < imageWidth; i++) {
        Serial.print(minDistance[i]);
        Serial.print("\t");
      }
      Serial.println();

      // Find the column with the overall minimum distance.
      int minCol = 0;
      int overallMin = minDistance[0];
      for (int col = 1; col < imageWidth; col++) {
        if (minDistance[col] < overallMin) {
          overallMin = minDistance[col];
          minCol = col;
        }
      }

      // Map the column index to an angle.
      // Leftmost column maps to -H_FOV/2, rightmost to +H_FOV/2.
      float angleStep = H_FOV / (imageWidth - 1);
      float objectAngle = -H_FOV / 2 + (minCol * angleStep);

      // Compute the distance error relative to the desired distance.
      float distanceError = overallMin - DESIRED_DISTANCE;

      // Decide motor commands based on object angle and distance error.
      int leftSpeed = 0;
      int rightSpeed = 0;
      if (abs(objectAngle) > ANGLE_THRESHOLD) {
        // If the object is off-center, rotate.
        int turnSpeed = (int)(KP_ANGLE * objectAngle);
        // Constrain turnSpeed.
        if (turnSpeed > MAX_SPEED)
          turnSpeed = MAX_SPEED;
        if (turnSpeed < -MAX_SPEED)
          turnSpeed = -MAX_SPEED;
        // Rotate in place: one wheel forward, the other in reverse.
        leftSpeed = turnSpeed;
        rightSpeed = -turnSpeed;
      } else {
        // If aligned, drive forward or backward to correct the distance.
        int driveSpeed = (int)(KP_DISTANCE * distanceError);
        if (driveSpeed > MAX_SPEED)
          driveSpeed = MAX_SPEED;
        if (driveSpeed < -MAX_SPEED)
          driveSpeed = -MAX_SPEED;
        leftSpeed = driveSpeed;
        rightSpeed = driveSpeed;
      }

      // Send motor commands.
      motors.setSpeeds(leftSpeed, rightSpeed);

      // Print calculated values.
      Serial.print("Overall min distance: ");
      Serial.print(overallMin);
      Serial.print(" mm, Object angle: ");
      Serial.print(objectAngle);
      Serial.print(" deg, Motor speeds => Left: ");
      Serial.print(leftSpeed);
      Serial.print(", Right: ");
      Serial.println(rightSpeed);
    }
  }
}

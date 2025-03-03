#include <Pololu3piPlus2040.h>

// Core objects
LineSensors lineSensors;
Motors motors;
ButtonA buttonA;
RGBLEDs leds;
Buzzer buzzer;

// Basic speed settings
uint16_t maxSpeed = 200;          // max speed for each motor
uint16_t calibrationSpeed = 200;  // used for sensor calibration

void setup()
{
  // Start serial communication for printing sensor values
  Serial.begin(115200);

  // Wait for button A press to begin
  while(!buttonA.getSingleDebouncedPress())
  {
    // Do nothing, just wait
  }

  // Play a little welcome song
  buzzer.play(">g32>>c32");
  
  // Perform sensor calibration by rotating in place
  for(uint16_t i = 0; i < 100; i++)
  {
    if (i > 30 && i <= 70)
    {
      motors.setSpeeds(-(int16_t)calibrationSpeed, calibrationSpeed);
    }
    else
    {
      motors.setSpeeds(calibrationSpeed, -(int16_t)calibrationSpeed);
    }
    delay(10);

    lineSensors.calibrate();
  }

  // Stop motors at the end of calibration
  motors.setSpeeds(0, 0);
}

void loop()
{
  // Read the position of the black line (returns 0 to 4000)
  int16_t position = lineSensors.readLineBlack();

  // Print line position and calibrated sensor values over Serial
  Serial.print("Position: ");
  Serial.print(position);
  Serial.print("  Values: ");
  for (uint8_t i = 0; i < LINE_SENSOR_COUNT; i++)
  {
    Serial.print(lineSensors.calibratedSensorValues[i]);
    Serial.print(" ");
  }
  Serial.println();

  // --- Proportional control calculations ---
  // The center of the line is assumed around 2000 (half of 4000).
  int16_t error = position - 2000;

  // Tune these constants as needed:
  // baseSpeed is our "straight line" speed,
  // Kp is our proportional gain (the higher it is, the more aggressively we turn).
  int16_t baseSpeed = 100;
  float   Kp        = 0.10; 

  // The turn “correction” is proportional to how far we are from the center
  int16_t turn = (int16_t)(Kp * error);

  // Calculate the desired motor speeds by adding/subtracting the correction
  int16_t leftSpeed = baseSpeed + turn;
  int16_t rightSpeed = baseSpeed - turn;

  // Clamp the speeds so they don't exceed 0–maxSpeed
  if (leftSpeed < 0) leftSpeed = 0;
  if (rightSpeed < 0) rightSpeed = 0;
  if (leftSpeed > maxSpeed) leftSpeed = maxSpeed;
  if (rightSpeed > maxSpeed) rightSpeed = maxSpeed;

  // Set the motor speeds
  motors.setSpeeds(leftSpeed, rightSpeed);

  // Optionally update the LEDs based on steering
  // You can adapt this logic to highlight bigger differences in speed/error
  if(turn > 0)
  {
    // turning left
    leds.setBrightness(FRONT_LEFT_LED, 0);
    leds.setBrightness(FRONT_RIGHT_LED, 4);
  }
  else if(turn < 0)
  {
    // turning right
    leds.setBrightness(FRONT_LEFT_LED, 4);
    leds.setBrightness(FRONT_RIGHT_LED, 0);
  }
  else
  {
    // going straight
    leds.setBrightness(FRONT_LEFT_LED, 4);
    leds.setBrightness(FRONT_RIGHT_LED, 4);
  }
}

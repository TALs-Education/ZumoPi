#include <Pololu3piPlus2040.h>

Encoders encoders;
Motors motors;
ButtonA buttonA;  // Using Button A for the drive sequence

char report[80];

void setup()
{
  Serial.begin(9600);
  // Uncomment and adjust any configuration if needed:
  // encoders.flipEncoders(true);
  // motors.flipLeftMotor(true);
  // motors.flipRightMotor(true);
}

void loop()
{
  // Send encoder counts to the serial monitor every 100ms.
  static uint8_t lastSerialTime = 0;
  if ((uint8_t)(millis() - lastSerialTime) >= 100)
  {
    lastSerialTime = millis();
    int16_t countsLeft = encoders.getCountsLeft();
    int16_t countsRight = encoders.getCountsRight();
    snprintf_P(report, sizeof(report), PSTR("%6d %6d"), countsLeft, countsRight);
    Serial.println(report);
  }
  
  // When Button A is pressed, drive forward for 1 second and then reverse for 1 second.
  if(buttonA.isPressed())
  {
    motors.setSpeeds(200, 200);  // Drive forward [-400 400]
    delay(1000);                 // for 1 second
    motors.setSpeeds(-200, -200); // Reverse      [-400 400]
    delay(1000);                 // for 1 second
    motors.setSpeeds(0, 0);       // Stop the motors
    
    // Wait until the button is released to avoid repeating the sequence immediately.
    while(buttonA.isPressed())
    {
      // Optionally, you could add a small delay here.
      delay(10);
    }
  }
}

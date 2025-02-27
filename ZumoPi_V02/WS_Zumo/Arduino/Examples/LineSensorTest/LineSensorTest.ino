// This example shows how to read the raw values from the five line sensors on
// the 3pi+ 2040.  This example is useful if you are having trouble with the
// sensors or just want to characterize their behavior.
// The raw (uncalibrated) values are reported to the serial monitor. 

#include <Pololu3piPlus2040.h>

LineSensors lineSensors;


void setup()
{

}

// Prints a line with all the sensor readings to the serial
// monitor.
void printReadingsToSerial()
{
  char buffer[80];
  sprintf(buffer, "%4d %4d %4d %4d %4d\n",
    lineSensors.rawSensorValues[0],
    lineSensors.rawSensorValues[1],
    lineSensors.rawSensorValues[2],
    lineSensors.rawSensorValues[3],
    lineSensors.rawSensorValues[4]
  );
  Serial.print(buffer);
}

void loop()
{
  static uint16_t lastSampleTime = 0;

  if ((uint16_t)(millis() - lastSampleTime) >= 100)
  {
    lastSampleTime = millis();

    // Read the line sensors.
    lineSensors.read();

    // Send the results to the LCD and to the serial monitor.
    printReadingsToSerial();
  }

}

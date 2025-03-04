// This example shows how to blink the LEDs 
//
// It alternates between the Yellow user LEDs next to the USB connector and the
// 6 addressable RGB LEDs distributed around the robot. The RGB LEDs are set to
// a rainbow of colors (red, orange, yellow, green, blue, and violet).

#include <Pololu3piPlus2040.h>

RGBLEDs leds;

// We'll use this variable to keep track of loop iterations.
unsigned long loopCounter = 0;

void setup()
{
  // Initialize serial communication at 9600 baud.
  Serial.begin(9600);

  // Set initial colors for the 6 addressable RGB LEDs.
  leds.set(FRONT_LEFT_LED, RED, 0);
  leds.set(FRONT_CENTER_LED, ORANGE, 0);
  leds.set(FRONT_RIGHT_LED, YELLOW, 0);
  leds.set(BACK_RIGHT_LED, GREEN, 0);
  leds.set(BACK_CENTER_LED, BLUE, 0);
  leds.set(BACK_LEFT_LED, VIOLET, 0);
}

void loop()
{
  // Print a message with the loop counter over Serial.
  Serial.print("Hello World, iteration: ");
  Serial.println(loopCounter);

  // Turn the Yellow LED on.
  ledYellow(1);

  // Turn RGB LEDs off.
  leds.setBrightness(0);

  // Wait for a second.
  delay(1000);

  // Turn the Yellow LED off.
  ledYellow(0);

  // Turn the RGB LEDs on (brightness = 15).
  leds.setBrightness(15);

  // Wait for a second.
  delay(1000);

  // Increment the loop counter.
  loopCounter++;
}

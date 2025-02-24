#include <APA102.h>

// Define which pins to use.
const uint8_t dataPin = 3;
const uint8_t clockPin = 6;

// Create an object for writing to the LED strip.
APA102<dataPin, clockPin> ledStrip;

// Set the number of LEDs to control.
const uint16_t ledCount = 10;

// Create a buffer for holding the colors (3 bytes per color).
rgb_color colors[ledCount];

// Set the brightness to use (the maximum is 31).
const uint8_t brightness = 1;

void setup()
{
  // Set all LEDs to off (black)
  for (int i = 0; i < ledCount; i++) {
    colors[i] = rgb_color(0, 0, 0);
  }
  
  // Define colors for specific LEDs.
  colors[6] = rgb_color(255, 0, 0);     // Red
  colors[7] = rgb_color(0, 255, 0);       // Green
  colors[8] = rgb_color(0, 0, 255);       // Blue
  colors[9] = rgb_color(255, 255, 255);   // White
  
  // Write the colors to the LED strip.
  ledStrip.write(colors, ledCount, brightness);
}

void loop(){
  // Nothing to do here.
}

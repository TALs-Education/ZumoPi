#include <APA102.h>
#include <ArduinoJson.h>
#include <Scheduler.h>

// Define which pins to use for the LED strip.
const uint8_t dataPin = 3;
const uint8_t clockPin = 6;

// Create an APA102 LED strip instance.
APA102<dataPin, clockPin> ledStrip;

// Configuration for the LED strip.
const uint16_t ledCount = 10;
rgb_color colors[ledCount];
const uint8_t brightness = 1;

// Create a UART instance on GP28 (TX) and GP29 (RX)
UART myUART(28, 29);

// Forward declarations.
void pollMyUART();
void processJsonCommand(String jsonMessage);
void setLEDColor(int ledNum, const char* colorStr);

void setup() {
  Serial.begin(115200);
  
  // Initialize all LEDs to off (black).
  for (int i = 0; i < ledCount; i++) {
    colors[i] = rgb_color(0, 0, 0);
  }
  ledStrip.write(colors, ledCount, brightness);

  // Initialize the custom UART.
  myUART.begin(115200, SERIAL_8N1);
  const char *initMsg = "Ready to receive JSON commands over myUART!\n";
  myUART.write((const uint8_t*)initMsg, strlen(initMsg));

  // Start the UART polling task.
  Scheduler.startLoop(pollMyUART);

  Serial.println("Setup complete. Awaiting JSON commands on myUART.");
}

void loop() {
  // Nothing to do here; the scheduler handles UART polling.
  yield();
}

// Task: Poll myUART for incoming JSON messages.
void pollMyUART() {
  // Use a static buffer to accumulate incoming characters.
  static String uartBuffer = "";
  
  // Read all available characters from myUART.
  while (myUART.available()) {
    char c = myUART.read();
    if (c == '\n') {
      // End-of-message detected.
      String jsonMessage = uartBuffer;
      uartBuffer = "";  // Clear the buffer for the next message.
      jsonMessage.trim(); // Remove any stray whitespace/newlines.
      
      if (jsonMessage.length() > 0) {
        processJsonCommand(jsonMessage);
      }
    } else {
      uartBuffer += c;
    }
  }
  
  yield(); // Yield to allow other tasks to run.
}

// Parse the JSON command and update the LED color.
void processJsonCommand(String jsonMessage) {
  // Allocate a static JSON document (adjust size as needed).
  StaticJsonDocument<128> doc;
  DeserializationError error = deserializeJson(doc, jsonMessage);
  
  if (error) {
    myUART.print("JSON Parse Error: ");
    myUART.println(error.c_str());
    return;
  }
  
  int ledNum = doc["LEDNumber"];
  const char* color = doc["Color"];
  
  // Validate LED number.
  if (ledNum < 0 || ledNum >= ledCount) {
    myUART.println("Invalid LED number");
    return;
  }
  
  // Set the specified LED to the given color.
  setLEDColor(ledNum, color);
}

// Set a given LED to the desired color.
void setLEDColor(int ledNum, const char* colorStr) {
  // Compare the color string (case-insensitive) and set accordingly.
  if (strcasecmp(colorStr, "Red") == 0) {
    colors[ledNum] = rgb_color(255, 0, 0);
  } else if (strcasecmp(colorStr, "Green") == 0) {
    colors[ledNum] = rgb_color(0, 255, 0);
  } else if (strcasecmp(colorStr, "Blue") == 0) {
    colors[ledNum] = rgb_color(0, 0, 255);
  } else if (strcasecmp(colorStr, "White") == 0) {
    colors[ledNum] = rgb_color(255, 255, 255);
  } else if (strcasecmp(colorStr, "Off") == 0 || strcasecmp(colorStr, "Black") == 0) {
    colors[ledNum] = rgb_color(0, 0, 0);
  } else {
    myUART.print("Unknown color: ");
    myUART.println(colorStr);
    return;
  }
  
  // Update the LED strip with the new color.
  ledStrip.write(colors, ledCount, brightness);
  myUART.print("Set LED ");
  myUART.print(ledNum);
  myUART.print(" to ");
  myUART.println(colorStr);
}

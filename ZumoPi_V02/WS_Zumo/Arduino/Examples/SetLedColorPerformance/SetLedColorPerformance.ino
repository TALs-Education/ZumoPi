#include <Pololu3piPlus2040.h>
#include <APA102.h>
#include <ArduinoJson.h>
#include <Scheduler.h>

// APA102 LED strip configuration
const uint8_t dataPin = 3;
const uint8_t clockPin = 6;
APA102<dataPin, clockPin> ledStrip;
const uint16_t ledCount = 10;
rgb_color colors[ledCount];
const uint8_t brightness = 1;

// Custom UART instance on GP28 (TX) and GP29 (RX)
UART myUART(28, 29);

// Forward declarations for tasks.
void pollMyUART();
void ledBlinkTask();

// Global idle counter for idle time measurement.
volatile unsigned long idleCycles = 0;
unsigned long lastPrintTime = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ;  // Wait for USB Serial connection
  }

  // Initialize all LEDs to off.
  for (int i = 0; i < ledCount; i++) {
    colors[i] = rgb_color(0, 0, 0);
  }
  ledStrip.write(colors, ledCount, brightness);

  // Initialize custom UART.
  myUART.begin(115200, SERIAL_8N1);
  const char *initMsg = "Ready to receive JSON commands over myUART!\n";
  myUART.write((const uint8_t*)initMsg, strlen(initMsg));

  // Start scheduler tasks.
  Scheduler.startLoop(pollMyUART);
  Scheduler.startLoop(ledBlinkTask);

  Serial.println("Setup complete. Awaiting JSON commands on myUART.");
}

void loop() {
  // Idle Time Measurement: count idle cycles.
  idleCycles++;

  unsigned long currentMillis = millis();
  if (currentMillis - lastPrintTime >= 1000) {
    Serial.print("Idle cycles in last second: ");
    Serial.println(idleCycles);
    idleCycles = 0;
    lastPrintTime = currentMillis;
  }

  yield();  // Yield to allow scheduled tasks to run.
}

// Task: Poll myUART for incoming JSON commands.
void pollMyUART() {
  static String uartBuffer = "";

  // Read all available characters from myUART.
  while (myUART.available()) {
    char c = myUART.read();
    if (c == '\n') {
      String jsonMessage = uartBuffer;
      uartBuffer = "";
      jsonMessage.trim();
      if (jsonMessage.length() > 0) {
        // Parse JSON command.
        StaticJsonDocument<128> doc;
        DeserializationError error = deserializeJson(doc, jsonMessage);
        if (error) {
          Serial.print("JSON Parse Error: ");
          Serial.println(error.c_str());
        } else {
          int ledNum = doc["LEDNumber"];
          const char* color = doc["Color"];
          if (ledNum < 0 || ledNum >= ledCount) {
            Serial.println("Invalid LED number");
          } else {
            // Set LED color based on JSON command.
            if (strcasecmp(color, "Red") == 0)
              colors[ledNum] = rgb_color(255, 0, 0);
            else if (strcasecmp(color, "Green") == 0)
              colors[ledNum] = rgb_color(0, 255, 0);
            else if (strcasecmp(color, "Blue") == 0)
              colors[ledNum] = rgb_color(0, 0, 255);
            else if (strcasecmp(color, "White") == 0)
              colors[ledNum] = rgb_color(255, 255, 255);
            else if (strcasecmp(color, "Off") == 0 || strcasecmp(color, "Black") == 0)
              colors[ledNum] = rgb_color(0, 0, 0);
            else {
              Serial.print("Unknown color: ");
              Serial.println(color);
              return;
            }
            // Update the LED strip.
            ledStrip.write(colors, ledCount, brightness);
            Serial.print("Set LED ");
            Serial.print(ledNum);
            Serial.print(" to ");
            Serial.println(color);
          }
        }
      }
    } else {
      uartBuffer += c;
    }
  }
  yield();
}

// Non-blocking LED blink task using millis()
void ledBlinkTask() {
  static bool ledState = false;
  static unsigned long lastBlinkTime = 0;
  unsigned long currentTime = millis();

  // Toggle LED every 1000 ms.
  if (currentTime - lastBlinkTime >= 1000) {
    ledState = !ledState;
    ledYellow(ledState ? 1 : 0);
    lastBlinkTime = currentTime;
    Serial.print("LED Blink: ");
    Serial.println(ledState ? "ON" : "OFF");
  }
  yield();
}

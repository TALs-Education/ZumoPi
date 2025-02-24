#include <Scheduler.h>
#include <Pololu3piPlus2040.h>

// Create a UART instance on GP28 (TX) and GP29 (RX)
UART myUART(28, 29);

// Create an instance for the RGB LEDs.
RGBLEDs leds;

// Forward declarations for the task functions.
void pollUART();
void pollUSB();

void setup() {
  // Initialize USB Serial.
  Serial.begin(115200);
  while (!Serial) { ; } // Wait for Serial connection, if needed.

  // Initialize the custom UART.
  myUART.begin(115200, SERIAL_8N1);
  const char *initMsg = "Hello from RP2040 myUART!\n";
  myUART.write((const uint8_t*)initMsg, strlen(initMsg));
  
  // Initialize the RGB LEDs with a rainbow of colors.
  leds.set(FRONT_LEFT_LED, RED, 0);
  leds.set(FRONT_CENTER_LED, ORANGE, 0);
  leds.set(FRONT_RIGHT_LED, YELLOW, 0);
  leds.set(BACK_RIGHT_LED, GREEN, 0);
  leds.set(BACK_CENTER_LED, BLUE, 0);
  leds.set(BACK_LEFT_LED, VIOLET, 0);
  
  // Start the additional tasks.
  Scheduler.startLoop(pollUART);
  Scheduler.startLoop(pollUSB);
}

void loop() {
  // LED blinking routine based on the 3π+ 2040 example.
  
  // Turn the Yellow user LED on.
  ledYellow(1);
  // Turn the RGB LEDs off.
  leds.setBrightness(0);
  delay(1000);  // Delay yields to other tasks.
  
  // Turn the Yellow user LED off.
  ledYellow(0);
  // Turn the RGB LEDs on.
  leds.setBrightness(15);
  delay(1000);  // Delay yields to other tasks.
}

// Task: Poll the custom UART for incoming data.
void pollUART() {
  if (myUART.available()) {
    String data = "";
    // Read data until a newline is encountered.
    while (myUART.available()) {
      char c = myUART.read();
      if (c == '\n') break;
      data += c;
    }
    
    if (data.length() > 0) {
      Serial.print("myUART Received: ");
      Serial.println(data);
      
      // Prepare and send the echo message.
      char outBuffer[128];
      sprintf(outBuffer, "myUART: %s\n", data.c_str());
      myUART.write((const uint8_t*)outBuffer, strlen(outBuffer));
    }
  }
  yield(); // Yield to allow other tasks to run.
}

// Task: Poll the USB Serial for incoming data.
void pollUSB() {
  if (Serial.available()) {
    String data = Serial.readStringUntil('\n');
    data.trim();  // Remove newline and extra whitespace.
    if (data.length() > 0) {
      Serial.print("USB Serial Received: ");
      Serial.println(data);
      
      // Prepare and send the message over myUART.
      char outBuffer[128];
      sprintf(outBuffer, "USB Serial: %s\n", data.c_str());
      myUART.write((const uint8_t*)outBuffer, strlen(outBuffer));
    }
  }
  yield(); // Yield to allow other tasks to run.
}

// Communication example between Raspberry Pi <--> Pico2040 over:
// - USB UART --> USB Pi ttyACM0
// - myUART (on GP28/GP29) --> Pi UART (ttyAMA10)

// Create a UART instance on GP28 (TX) and GP29 (RX)
UART myUART(28, 29);

void setup() {
  // Initialize the USB Serial console.
  Serial.begin(115200);
  while (!Serial) {
    ; // Wait for Serial to connect (only needed on some boards)
  }
  
  // Initialize our UART at 115200 baud, 8 data bits, no parity, 1 stop bit.
  myUART.begin(115200, SERIAL_8N1);
  
  // Send an initial message over our custom UART.
  const char *initMsg = "Hello from RP2040 myUART!\n";
  myUART.write((const uint8_t*)initMsg, strlen(initMsg));
}

void pollUART() {
  // Check if data is available on our custom UART.
  if (myUART.available()) {
    String data = "";
    // Read incoming data character by character until a newline is encountered.
    while (myUART.available()) {
      char c = myUART.read();
      if (c == '\n') break;
      data += c;
    }
    
    if (data.length() > 0) {
      Serial.print("myUART Received: ");
      Serial.println(data);
      
      // Assemble the echo message using sprintf
      char outBuffer[128];
      sprintf(outBuffer, "myUART: %s\n", data.c_str());
      
      // Send the message over myUART
      myUART.write((const uint8_t*)outBuffer, strlen(outBuffer));
    }
  }
}

void pollUSB() {
  // Check if data is available on the USB Serial console.
  if (Serial.available()) {
    String data = Serial.readStringUntil('\n');
    data.trim();  // Remove newline and whitespace
    if (data.length() > 0) {
      Serial.print("USB Serial Received: ");
      Serial.println(data);
      
      // Assemble the message using sprintf
      char outBuffer[128];
      sprintf(outBuffer, "USB Serial: %s\n", data.c_str());
      
      // Send the assembled message over myUART.
      myUART.write((const uint8_t*)outBuffer, strlen(outBuffer));
    }
  }
}

void loop() {
  pollUART();    // Poll for myUART data.
  pollUSB(); // Poll for USB Serial input.
  delay(100);    // Short delay to prevent hogging the CPU.
}

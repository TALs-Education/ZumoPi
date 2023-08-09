/*

*/
#include <Wire.h>
#include <Zumo32U4.h>

Zumo32U4Motors motors;

int i = 0;
String inputString = "";         // a String to hold incoming data
bool stringComplete = false;  // whether the string is complete

// the setup function runs once when you press reset or power the board
void setup() {
  // initialize digital pin LED_BUILTIN as an output.
  pinMode(LED_BUILTIN, OUTPUT);
  
  // initialize serial:
  Serial.begin(9600);
  // reserve 200 bytes for the inputString:
  inputString.reserve(200);
  //
  Serial.println("Serial Pssthrough example");
  motors.setLeftSpeed(0);
  motors.setRightSpeed(0);
}

// the loop function runs over and over again forever
void loop() {
  while (Serial.available()) {
    // get the new byte:
    char inChar = (char)Serial.read();
    // add it to the inputString:
    inputString += inChar;
    // if the incoming character is a newline, set a flag so the main loop can
    // do something about it:
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
  // print the string when a newline arrives:
  if (stringComplete) {
    //Serial.print(inputString);

    int ind1 = inputString.indexOf(',');  //finds location of first ,
    String str = inputString.substring(0, ind1);   //captures first data String
    int joyX = str.toInt();
    str ="";
    str = inputString.substring(ind1+1);   //captures first data String
    int joyY = str.toInt();
    
    int leftMotor = joyY + joyX;  //int(float(joyX)/1.5);
    int rightMotor = joyY - joyX; //int(float(joyX)/1.5);
    uint16_t batteryLevel = readBatteryMillivolts();
    float battery = float(batteryLevel)/1000.0;
    Serial.print(leftMotor);
    Serial.print(" , ");
    Serial.print(rightMotor);
    Serial.print(" , ");
    Serial.println(battery);
    motors.setLeftSpeed(leftMotor);
    motors.setRightSpeed(rightMotor);
    // clear the string:
    inputString = "";
    stringComplete = false;
  }
}
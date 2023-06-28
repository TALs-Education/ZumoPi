/*
  Path Control ZumoPi Platform
*/

#include "ZumoController.h"

// Constants
#define SAMPLERATE 10 // 5 millis =  200 Hz

// Desired path in the format: {x, y} coordinates
float desired_path[][2] = {
//    {0.44   , 0   },
//    {0.44   , 0.5 },
//    {-0.06  , 0.5 },
//    {-0.06  , 0   } // compensate stopping distance

 {0.042426, 0.042426},    {0.077046, 0.0079789},    {0.11062, -0.024426},    {0.14266, -0.053409},    {0.17249, -0.077685},    {0.19926, -0.096164},    {0.22175, -0.10817},    {0.23849, -0.11388},    {0.24856, -0.11498},    {0.25357, -0.11407},    {0.2579, -0.11159},    {0.2644, -0.10486},    {0.27236, -0.091744},    {0.27997, -0.072333},    {0.28586, -0.047971},    {0.28928, -0.02042},    {0.28988, 0.0084613},    {0.28761, 0.036794},    {0.28268, 0.062705},    {0.27567, 0.084374},    {0.26764, 0.10022},    {0.26032, 0.10948},    {0.2552, 0.11335},    {0.25104, 0.11473},    {0.24348, 0.11475},    {0.22949, 0.11125},    {0.20921, 0.10196},    {0.18406, 0.086127},    {0.15538, 0.064147},    {0.12417, 0.036973},    {0.091165, 0.0058275},    {0.056924, -0.027941},    {0.021886, -0.062931},    {-0.013608, -0.097754},    {-0.04932, -0.13108},    {-0.085148, -0.16171},    {-0.1212, -0.18854},    {-0.15788, -0.21057},    {-0.19599, -0.22657},    {-0.23627, -0.23458},    {-0.27792, -0.2317},    {-0.31689, -0.2163},    {-0.34868, -0.19074},    {-0.37232, -0.15903},    {-0.38917, -0.12362},    {-0.40059, -0.085645},    {-0.4074, -0.045863},    {-0.40997, -0.0050792},    {-0.40842, 0.035818},    {-0.40269, 0.075927},    {-0.39246, 0.11442},    {-0.37707, 0.15054},    {-0.35526, 0.18333},    {-0.32554, 0.21075},    {-0.28803, 0.22903},    {-0.24656, 0.235},    {-0.20575, 0.2294},    {-0.16716, 0.21515},    {-0.1302, 0.19449},    {-0.09405, 0.16875},    {-0.058187, 0.13897},    {-0.022443, 0.1062},    
 {0.013123, 0.071628},
 {0.11062, -0.024426}


    // ...add more points as needed...
};

// Number of points in the path
int num_points = sizeof(desired_path) / sizeof(desired_path[0]);

// Zumo controller
ZumoController zumoController;
bool pathControlFlag = 0;
// time variables
unsigned long lastMillis = 0;
unsigned long lastMicros = 0;

// message variables
String inputString = "";      // a String to hold incoming data
bool stringComplete = false;  // whether the string is complete

// battery level;
float batteryVoltage = 0;

// add button to init path control
Zumo32U4ButtonC buttonC;

void setup() {
  // initialize serial:
  Serial.begin(115200);
  // reserve 200 bytes for the inputString:
  inputString.reserve(200);
  // take time stamp
  lastMillis = millis();
  lastMicros = micros();
  // calculate gyro offset
  //zumoController.gyroOffset();
  // initial conditions
  zumoController.car_state.posx = 0.042426;
  zumoController.car_state.posy = 0.042426;
  zumoController.car_state.theta = -0.78539;
}

void loop() {
  // check button press to init path controll
  if (buttonC.getSingleDebouncedPress()){ 
    // reset variables
    zumoController.motorsSetSpeed(0, 0);
    zumoController.reset();
    delay(2500);
    pathControlFlag = 1;
  }
  if (pathControlFlag){
    if (millis() - lastMillis >= SAMPLERATE){
      lastMillis = millis();
      // calculate dt sample
      unsigned long dtMicros = micros()-lastMicros;
      lastMicros = micros();
      
      zumoController.dt_time = dtMicros / 1000000.0f;
      // update current car states:
      zumoController.odometry();
      // run path control
      zumoController.P2P_CTRL(desired_path, num_points);
      
      // read voltage
      uint16_t batteryLevel = readBatteryMillivolts();
      batteryVoltage = float(batteryLevel)/1000.0;
      
      // send a response
      Serial.print(zumoController.car_state.posx);
      Serial.print(" , ");
      Serial.print(zumoController.car_state.posy);
      Serial.print(" , ");
      Serial.println(batteryVoltage);
    }
  }
  // check for incoming messages
  msg_handler();
}

void msg_handler(void){
  // check for incoming message
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
  // check if message is complete
  if (stringComplete) {
    parse_msg();
  }
}
// parse incoming message and send a response
void parse_msg(void){
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
    batteryVoltage = float(batteryLevel)/1000.0;


    // send a response
    Serial.print(leftMotor);
    Serial.print(" , ");
    Serial.print(rightMotor);
    Serial.print(" , ");
    Serial.println(batteryVoltage);

    pathControlFlag = 0;
    zumoController.motorsSetSpeed(leftMotor,rightMotor);
    // clear the string:
    inputString = "";
    stringComplete = false;  
}

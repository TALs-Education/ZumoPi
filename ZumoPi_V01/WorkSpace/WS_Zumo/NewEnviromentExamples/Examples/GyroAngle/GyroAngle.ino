/*
  Odometry && Gyro Integration with teleoperate
*/
#include <Wire.h>
#include <Zumo32U4.h>

// zumo classes
Zumo32U4Encoders encoders;
Zumo32U4Motors motors;
Zumo32U4IMU imu;

// time variables
#define SAMPLERATE 10          // 5 millis =  200 Hz
unsigned long lastMillis = 0;
unsigned long lastMicros = 0;
float dt_time = SAMPLERATE/1000.0;

// message variables
String inputString = "";      // a String to hold incoming data
bool stringComplete = false;  // whether the string is complete

// Odometry settings
#define GEAR_RATIO 51.45      // Motor gear ratio 100.37
#define WHEELS_DISTANCE 98    // Distance between tracks
#define WHEEL_DIAMETER 37.5   // Wheels diameter measured 38.5
#define ENCODER_PPR 12        // Encoder pulses per revolution
#define GYRO_SCALE 0.07        // 70 mdps/LSB 
float encoder2dist = WHEEL_DIAMETER*3.14/(ENCODER_PPR*GEAR_RATIO);  // conversition of encoder pulses to distance in mm

float theta = 0; 
float posx = 0;
float posy = 0;

// imu Fusion
float gyroAngle=0;
int32_t gyroOffset_z = -16;
float gyroz=0;
boolean motorsState = 0;
// the setup function runs once when you press reset or power the board
void setup() {
  // init imu
  Wire.begin();
  imu.init();
  imu.enableDefault();
  imu.configureForTurnSensing();
  // initialize digital pin LED_BUILTIN as an output.
  pinMode(LED_BUILTIN, OUTPUT);
  
  // initialize serial:
  Serial.begin(9600);
  // reserve 200 bytes for the inputString:
  inputString.reserve(200);
  // update motors command to stop
  motors.setLeftSpeed(0);
  motors.setRightSpeed(0);
  // take time stamp
  lastMillis = millis();
  lastMicros = micros();
  
  // calculate gyro offset
  //gyroOffset();
  
}

// the loop function runs over and over again forever
void loop() {
  if (millis() - lastMillis >= SAMPLERATE){
    lastMillis = millis();
    // calculate dt sample
    unsigned long dtMicros = micros()-lastMicros;
    lastMicros = micros();
    dt_time = float(dtMicros)/1000000.0;
    // read imu, calculate rotation angle
    gyroIntegration();
    // run functions
    odometry();
  }
  // check for iuncoming messages
  msg_handler();
}

// gyroIntegration
void gyroIntegration(void){
  imu.readGyro();
  gyroz = ((float) (imu.g.z - (int16_t)gyroOffset_z))*GYRO_SCALE;
  if (motorsState) gyroAngle+=(gyroz*dt_time); // integrate when in motion
}

// gyro calibration
void gyroOffset(){
  delay(1); // delay before starting gyro readings for offset
  int32_t total = 0;
  for (uint16_t i = 0; i < 1024; i++)
  {
    // Wait for new data to be available, then read it.
    while(!imu.gyroDataReady()) {}
    imu.readGyro();

    // Add the Z axis reading to the total.
    total += imu.g.z;
  }
  gyroOffset_z = total / 1024;
  Serial.println(gyroOffset_z);
}

// check if there is a message if so parse it and send an update
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
    float battery = float(batteryLevel)/1000.0;


    // send a response
    Serial.print(leftMotor);
    Serial.print(" , ");
    Serial.print(rightMotor);
    Serial.print(" , ");
    Serial.print(battery);
    Serial.print(" , ");
    Serial.print(dt_time);
    Serial.print(" , ");
    Serial.print(posx);
    Serial.print(" , ");
    Serial.print(posy);
    Serial.print(" , ");
    Serial.print(theta*57.295);
    Serial.print(" , ");
    Serial.println(gyroAngle);

    motorsState = (leftMotor || rightMotor) ==  0 ? 0 : 1; //  check if motors are still
    // update motors 
    
    motors.setLeftSpeed(leftMotor);
    motors.setRightSpeed(rightMotor);
    // clear the string:
    inputString = "";
    stringComplete = false;  
}

void odometry(void){
      //encoder read
    int16_t countsLeft = encoders.getCountsAndResetLeft();
    int16_t countsRight = encoders.getCountsAndResetRight();
    float dx_1 = countsRight*encoder2dist;
    float dx_2 = countsLeft*encoder2dist;
    float d_theta = float(dx_1-dx_2)/WHEELS_DISTANCE;
    posx += cos(theta+d_theta/2)*(dx_1+dx_2)/2;
    posy += sin(theta+d_theta/2)*(dx_1+dx_2)/2;
    theta += d_theta;
}
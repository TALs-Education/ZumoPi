/*
  Odometry && Gyro Integration && Magnetic Angle with teleoperate
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
bool stringComplete = true;  // whether the string is complete

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

float magAngle = 0;
// define if to perform magnetometer calibration
#define MAG_CALIBRATE false
// magnetometer calibration variables
struct {
 int xMax = -22628; //-21445
 int xMin = -26413; //-27942
 int yMax = 19277;  // 20547
 int yMin = 14575;  // 14575
 int xOffset = 8247; //8074
 int yOffset = -15842; // -15207
 float scaleX = 1892.5; // 3248.5
 float scaleY = 2351.0; // 2986.0
} magCal;

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
  gyroOffset();
  
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
    // Magnetometer angle
    magnetometer();
  }
  // check for iuncoming messages
  msg_handler();
}

// Magnetometer angle
void magnetometer(void){
    imu.read();
    float magx = ((double)(imu.m.x - magCal.xOffset))/magCal.scaleX;
    float magy = ((double)(imu.m.y - magCal.yOffset))/magCal.scaleY;
    magAngle = atan2(magy,magx);

    if (MAG_CALIBRATE){
        if (imu.m.x > magCal.xMax) magCal.xMax = imu.m.x;
        if (imu.m.x < magCal.xMin) magCal.xMin = imu.m.x;
        magCal.xOffset = (magCal.xMax + magCal.xMin)/2;
        magCal.scaleX = ((float)(magCal.xMax - magCal.xMin))/2;
        if (imu.m.y > magCal.yMax) magCal.yMax = imu.m.y;
        if (imu.m.y < magCal.yMin) magCal.yMin = imu.m.y;
        magCal.yOffset = (magCal.yMax + magCal.yMin)/2;
        magCal.scaleY = ((float)(magCal.yMax - magCal.yMin))/2;
    

        Serial.print(imu.m.x);
        Serial.print(" , ");
        Serial.print(imu.m.y);
        Serial.print(" , ");
        Serial.print(magCal.xMax);
        Serial.print(" , ");
        Serial.print(magCal.xMin);
        Serial.print(" , ");
        Serial.print(magCal.yMax);
        Serial.print(" , ");
        Serial.print(magCal.yMin);
        Serial.print(" , ");
        Serial.print(magCal.xOffset);
        Serial.print(" , ");
        Serial.print(magCal.yOffset);
        Serial.print(" , ");
        Serial.print(magCal.scaleX);
        Serial.print(" , ");
        Serial.print(magCal.scaleY);
        Serial.print(" , ");
        Serial.println(magAngle*57.295);
    }
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
    Serial.print(dt_time*1000);
    Serial.print(" , ");
    Serial.print(posx);
    Serial.print(" , ");
    Serial.print(posy);
    Serial.print(" , ");
    Serial.print(theta*57.295);
    Serial.print(" , ");
    Serial.print(gyroAngle);
    Serial.print(" , ");
    Serial.println(magAngle*57.295);


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
    posx += sin(theta)*(dx_1+dx_2)/2;
    posy += cos(theta)*(dx_1+dx_2)/2;
    theta += float(dx_1-dx_2)/WHEELS_DISTANCE;
}
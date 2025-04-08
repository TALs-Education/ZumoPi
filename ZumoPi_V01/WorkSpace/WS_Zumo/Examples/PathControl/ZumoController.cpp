#include "ZumoController.h"

ZumoController::ZumoController(){
    // Constructor body
}

void ZumoController::begin() {
  // Begin communication with IMU
  Wire.begin();
  imu.init();
  imu.enableDefault();
  imu.configureForTurnSensing();
  // initialize digital pin LED_BUILTIN as an output.
  pinMode(LED_BUILTIN, OUTPUT);
  
  // Reset all the member variables
  reset();
}


void ZumoController::reset() {
    // Reset all the member variables
    car_state = {0.0f, 0.0f, 0.0f, 0.0f, 0, 0.0f, 0.0f};
    path_state = {0.0f, 0.0f, 0.0f, 0.0f, 0};

    err_sum_left = 0.0f;
    err_sum_right = 0.0f;
    v_l_target = 0.0f;
    v_r_target = 0.0f;
    prev_v_forward = 0.0f;
}

void ZumoController::control() {
    // calculate control
    float error_left = v_l_target - car_state.v_left;
    float error_right = v_r_target - car_state.v_right;

    err_sum_left += error_left;
    err_sum_right += error_right;

    int u_left = Kp * error_left + Ki * err_sum_left;
    int u_right = Kp * error_right + Ki * err_sum_right;

//      Serial.print(v_l_target);
//      Serial.print(" , ");
//      Serial.print(v_r_target);
//      Serial.print(" , ");
//      Serial.print(error_left);
//      Serial.print(" , ");
//      Serial.print(error_right);
//      Serial.print(" , ");
//      Serial.print(u_left);
//      Serial.print(" , ");
//      Serial.println(u_right);
      
    motorsSetSpeed(u_left, u_right);
}

void ZumoController::odometry() {
  //encoder read
  int16_t countsLeft = encoders.getCountsAndResetLeft();
  int16_t countsRight = encoders.getCountsAndResetRight();
  float dx_1 = float(countsRight)*encoder2dist;
  float dx_2 = float(countsLeft)*encoder2dist;
  car_state.v_left  =  dx_2/dt_time;
  car_state.v_right =  dx_1/dt_time;
  float d_theta = float(dx_1-dx_2)/WHEELS_DISTANCE;
  car_state.posx += cos(car_state.theta+d_theta/2)*(dx_1+dx_2)/2;
  car_state.posy += sin(car_state.theta+d_theta/2)*(dx_1+dx_2)/2;
  car_state.theta += d_theta;
  // integrate gyro
  gyroIntegration();
}

void ZumoController::gyroOffset() {
  delay(500); // delay before starting gyro readings for offset
  int32_t total = 0;
  for (uint16_t i = 0; i < 1024; i++) {
    while(!imu.gyroDataReady()) {}
    imu.readGyro();
    total += imu.g.z;
  }
  gyroOffset_z = total / 1024;
}

void ZumoController::gyroIntegration() {
  imu.readGyro();
  float gyroz = ((float) (imu.g.z - gyroOffset_z))*0.07;
  if (car_state.motorState) car_state.gyroAngle += (gyroz*dt_time); // integrate when in motion
}

void ZumoController::motorsSetSpeed(int leftSpeed, int rightSpeed) {
    // saturate command
    if (leftSpeed > 400) leftSpeed = 400;
    if (leftSpeed < -400) leftSpeed = -400;
    if (rightSpeed > 400) rightSpeed = 400;
    if (rightSpeed < -400) rightSpeed = -400;

    // update motor State flag based on the motor commands
    (leftSpeed == 0 && rightSpeed == 0) ? car_state.motorState = 0: car_state.motorState = 1;

    // set motors speed
    motors.setSpeeds(leftSpeed, rightSpeed);

}

void ZumoController::P2P_CTRL(float desired_pos[][2], int numPoints) {
    // define the stopping distance and the pass to next point distance in [m]
    float stopDistance = 0.025f; // [m]
    float passDistance = 0.05f; // [m]

    // calculate car vectors and Path vectors
    float Vr[2] = {cos(car_state.theta) , sin(car_state.theta)}; // car direction vector
    float Vt[2] = {desired_pos[path_state.currPoint][0] - car_state.posx, desired_pos[path_state.currPoint][1] - car_state.posy}; // target direction vector

    float Vd[2];
    if ( path_state.currPoint > 0) {
        Vd[0] = desired_pos[path_state.currPoint][0] - desired_pos[path_state.currPoint-1][0];
        Vd[1] = desired_pos[path_state.currPoint][1] - desired_pos[path_state.currPoint-1][1];
    } else {
        Vd[0] = desired_pos[path_state.currPoint][0]; // initial condition
        Vd[1] = desired_pos[path_state.currPoint][1]; // initial condition
    }

    float crossVdVr = Vd[1]*Vr[0] - Vd[0]*Vr[1];
    float crossVtVd =  Vt[1]*Vd[0] - Vt[0]*Vd[1];
    float dotVdVr = (Vd[0]*Vr[0] + Vd[1]*Vr[1])/(sqrt(Vd[0]*Vd[0] + Vd[1]*Vd[1]) * sqrt(Vr[0]*Vr[0] + Vr[1]*Vr[1]));

    path_state.de = crossVtVd / sqrt(Vd[0]*Vd[0] + Vd[1]*Vd[1]); // distance to desired path

    // calculate remaining distance
    path_state.dist = sqrt(Vt[0]*Vt[0] + Vt[1]*Vt[1]); // distance to current point
    float pathDist = 0;
    // sum of remaining points
    if (path_state.currPoint < (numPoints-1)) {
        for (int i = path_state.currPoint; i < (numPoints-1); i++) {
            float dx = desired_pos[i+1][0] - desired_pos[i][0];
            float dy = desired_pos[i+1][1] - desired_pos[i][1];
            pathDist += sqrt(dx*dx + dy*dy);
        }
        // pass to next point condition
        if (abs(path_state.dist) < passDistance) {
            path_state.currPoint++;
        } else {
            float dx = desired_pos[path_state.currPoint+1][0] - car_state.posx;
            float dy = desired_pos[path_state.currPoint+1][1] - car_state.posy;
            float dist_nextPoint = sqrt(dx*dx + dy*dy);
            if (dist_nextPoint < path_state.dist) path_state.currPoint++;
        }
        // update remaining distance
        path_state.dist += pathDist;
    }

    // calculate the desired angle change for the target point
    if (abs(crossVdVr) < 0.001f) {
              // Math singularity
        if (dotVdVr == -1) {
            // vectors align in reverse... singularity
            path_state.theta_t = 3.14159265f / 2;
        } else {
            // Vectors align in the same direction
            path_state.theta_t = 0;
        }
    } else {
        float dir = (crossVdVr > 0) ? 1.0f : -1.0f;
        path_state.theta_t = acos(dotVdVr) * dir; // angle from desired path
    }

    // stop condition, happens only if reached last point and if reached stop distance or passed the last point - dotVtVr
    if ((path_state.currPoint == numPoints - 1) && ((abs(path_state.dist) < stopDistance) || ((Vt[0]*Vr[0] + Vt[1]*Vr[1]) < -0.1f))){
        path_state.v_forward = 0;
        path_state.theta_t = 0;
        motorsSetSpeed(0, 0);
    }else{ // set desired velocity
        path_state.v_forward  = sqrt(2*a_max*path_state.dist)/2; // /2 for slower deceleration
        float max_change = a_max*dt_time;
        // set max acceleration
        float c_v_farward = (car_state.v_left + car_state.v_right)/2; 
        
        // based on current forward velocity which changes or based on command profile
        //if ((path_state.v_forward - prev_v_forward) >= max_change) path_state.v_forward = c_v_farward + max_change;
        //if ((path_state.v_forward - prev_v_forward) <= -max_change) path_state.v_forward = c_v_farward - max_change;

        // based on command profile for thhe positive change only
        if ((path_state.v_forward - prev_v_forward) >= max_change) path_state.v_forward = prev_v_forward + max_change;
        if ((path_state.v_forward - prev_v_forward) <= -max_change) path_state.v_forward = prev_v_forward - max_change;
        
        prev_v_forward = path_state.v_forward; 

        // set max velocity
        if (path_state.v_forward >= v_max) path_state.v_forward = v_max;
     
        // update motors desired velocity:
        v_l_target = path_state.v_forward - (path_state.theta_t*Kp_theta + path_state.de*Kp_de);
        v_r_target = path_state.v_forward + (path_state.theta_t*Kp_theta + path_state.de*Kp_de);
        
//        Serial.print(car_state.posx);
//        Serial.print(" , ");
//        Serial.print(car_state.posy);
//        Serial.print(" , ");
//        Serial.print(path_state.v_forward);
//        Serial.print(" , ");
//        Serial.print(c_v_farward);
//        Serial.print(" , ");
//        Serial.print(path_state.de*100);
//        Serial.print(" , ");
//        Serial.println(path_state.dist*100);

        // update control
        control();


    }
}

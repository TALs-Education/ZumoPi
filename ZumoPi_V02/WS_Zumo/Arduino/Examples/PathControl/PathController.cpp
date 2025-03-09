#include "PathController.h"

PathController::PathController() {
  // Initialize control parameters.
  dt_time  = 0.01f;           // 10 ms update interval
  WHEELS_DISTANCE = 98.0f;    // mm between wheels
  a_max = 200.0f;             // maximum acceleration (mm/s^2)
  v_max = 100.0f;             // maximum forward velocity (mm/s)
  Kp = 1.0f;
  Ki = 0.1f;
  Kp_theta = 100.0f;
  Kp_de = 1.0f;    

  // Initialize target velocities and integrators.
  v_l_target = 0.0f;
  v_r_target = 0.0f;
  err_sum_left = 0.0f;
  err_sum_right = 0.0f;
  prev_v_forward = 0.0f;

  // Initialize states.
  car_state = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0};
  path_state = {0.0f, 0.0f, 0.0f, 0.0f, 0};

  // Initialize motor commands.
  currentCommands.leftSpeed = 0;
  currentCommands.rightSpeed = 0;
}

void PathController::begin() {
  reset();
}

void PathController::reset() {
  car_state = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0};
  path_state = {0.0f, 0.0f, 0.0f, 0.0f, 0};
  err_sum_left = 0.0f;
  err_sum_right = 0.0f;
  v_l_target = 0.0f;
  v_r_target = 0.0f;
  prev_v_forward = 0.0f;
  currentCommands.leftSpeed = 0;
  currentCommands.rightSpeed = 0;
}

void PathController::setMotorSpeeds(int leftSpeed, int rightSpeed) {
  // Saturate commands.
  if (leftSpeed > 400) leftSpeed = 400;
  if (leftSpeed < -400) leftSpeed = -400;
  if (rightSpeed > 400) rightSpeed = 400;
  if (rightSpeed < -400) rightSpeed = -400;
  
  // Update motor state flag.
  car_state.motorState = ((leftSpeed == 0 && rightSpeed == 0) ? 0 : 1);
  
  // Store the commands.
  currentCommands.leftSpeed = leftSpeed;
  currentCommands.rightSpeed = rightSpeed;
}

void PathController::control() {
  // PID control for each wheel.
  float error_left = v_l_target - car_state.v_left;
  float error_right = v_r_target - car_state.v_right;
  
  err_sum_left += error_left;
  err_sum_right += error_right;
  
  int u_left = (int)(Kp * error_left + Ki * err_sum_left);
  int u_right = (int)(Kp * error_right + Ki * err_sum_right);
  
  setMotorSpeeds(u_left, u_right);
}

void PathController::update(const Odometry &odom, float desired_pos[][2], int numPoints) {
  // Copy current odometry data into the controller's car state.
  car_state.posx = odom.posX;
  car_state.posy = odom.posY;
  car_state.theta = odom.theta;
  car_state.v_left = odom.v_left;
  car_state.v_right = odom.v_right;
  dt_time = odom.dt;
  
  // Define distance thresholds (in mm).
  float stopDistance = 25.0f;  // 25 mm = 0.025 m
  float passDistance = 50.0f;  // 50 mm = 0.05 m
  
  // Ensure the current target index is valid.
  if (path_state.currPoint >= numPoints) {
    path_state.currPoint = numPoints - 1;
  }
  
  // Get the current target point.
  float targetX = desired_pos[path_state.currPoint][0];
  float targetY = desired_pos[path_state.currPoint][1];
  
  // Compute vector from current position to target.
  float Vt[2] = { targetX - car_state.posx, targetY - car_state.posy };
  
  // Car heading vector.
  float Vr[2] = { cos(car_state.theta), sin(car_state.theta) };
  
  // Compute path direction vector Vd.
  float Vd[2];
  if (path_state.currPoint > 0) {
    Vd[0] = desired_pos[path_state.currPoint][0] - desired_pos[path_state.currPoint - 1][0];
    Vd[1] = desired_pos[path_state.currPoint][1] - desired_pos[path_state.currPoint - 1][1];
  } else {
    Vd[0] = desired_pos[path_state.currPoint][0];
    Vd[1] = desired_pos[path_state.currPoint][1];
  }
  
  float normVd = sqrt(Vd[0]*Vd[0] + Vd[1]*Vd[1]);
  // Vr is a unit vector.
  
  // Compute cross products and dot product.
  float crossVdVr = Vd[1]*Vr[0] - Vd[0]*Vr[1];
  float crossVtVd = Vt[1]*Vd[0] - Vt[0]*Vd[1];
  float dotVdVr = (Vd[0]*Vr[0] + Vd[1]*Vr[1]) / normVd;
  
  // Compute cross-track error.
  path_state.de = crossVtVd / normVd;
  
  // Distance to current target point.
  path_state.dist = sqrt(Vt[0]*Vt[0] + Vt[1]*Vt[1]);
  float pathDist = 0.0f;
  
  if (path_state.currPoint < (numPoints - 1)) {
    // Sum remaining path distances.
    for (int i = path_state.currPoint; i < (numPoints - 1); i++) {
      float dx = desired_pos[i+1][0] - desired_pos[i][0];
      float dy = desired_pos[i+1][1] - desired_pos[i][1];
      pathDist += sqrt(dx*dx + dy*dy);
    }
    // Transition condition: if close enough to current target.
    if (path_state.dist < passDistance) {
      path_state.currPoint++;
    } else {
      float dx = desired_pos[path_state.currPoint+1][0] - car_state.posx;
      float dy = desired_pos[path_state.currPoint+1][1] - car_state.posy;
      float dist_nextPoint = sqrt(dx*dx + dy*dy);
      if (dist_nextPoint < path_state.dist)
        path_state.currPoint++;
    }
    path_state.dist += pathDist;
  }
  
  // Calculate desired heading change.
  if (fabs(crossVdVr) < 0.001f) {
    path_state.theta_t = (dotVdVr == -1) ? (PI / 2) : 0;
  } else {
    float dir = (crossVdVr > 0) ? 1.0f : -1.0f;
    path_state.theta_t = acos(dotVdVr) * dir;
  }
  
  // Stop condition: if at last point and within stopDistance, or if target is behind.
  float dotVtVr = (Vt[0]*Vr[0] + Vt[1]*Vr[1]) / (sqrt(Vt[0]*Vt[0] + Vt[1]*Vt[1]));
  if ((path_state.currPoint == numPoints - 1 && fabs(path_state.dist) < stopDistance) ||
      (dotVtVr < -0.1f)) {
    path_state.v_forward = 0;
    path_state.theta_t = 0;
    setMotorSpeeds(0, 0);
  } else {
    // Compute desired forward velocity (with deceleration).
    path_state.v_forward = sqrt(2 * a_max * path_state.dist) / 2; // slower deceleration
    float max_change = a_max * dt_time;
    float c_v_forward = (car_state.v_left + car_state.v_right) / 2; // average speed
    
    if ((path_state.v_forward - prev_v_forward) >= max_change)
      path_state.v_forward = prev_v_forward + max_change;
    if ((path_state.v_forward - prev_v_forward) <= -max_change)
      path_state.v_forward = prev_v_forward - max_change;
    
    prev_v_forward = path_state.v_forward;
    
    if (path_state.v_forward > v_max)
      path_state.v_forward = v_max;
    
    // Set target wheel velocities.
    v_l_target = path_state.v_forward - (path_state.theta_t * Kp_theta + path_state.de * Kp_de);
    v_r_target = path_state.v_forward + (path_state.theta_t * Kp_theta + path_state.de * Kp_de);
    
    // Run PID control.
    control();
  }
}

#ifndef PATHCONTROLLER_H
#define PATHCONTROLLER_H

#include <Arduino.h>
#include <math.h>
#include "Odometry.h"  // Ensure the Odometry class is available

class PathController {
public:
  // Structure to hold a snapshot of the car's state.
  struct CarState {
    float posx;      // position in mm
    float posy;
    float theta;     // orientation in rad
    float v_left;    // left wheel velocity (mm/s)
    float v_right;   // right wheel velocity (mm/s)
    int motorState;  // 0 = off, 1 = on
  };

  // Structure to hold the path state.
  struct PathState {
    float de;      // cross-track error (mm)
    float dist;    // distance to current target point (mm)
    float theta_t; // desired heading change (rad)
    float v_forward; // desired forward velocity (mm/s)
    int currPoint; // index of current target point
  };

  // Structure to hold motor command outputs.
  struct MotorCommands {
    int leftSpeed;
    int rightSpeed;
  };

  // Constructor.
  PathController();

  // Initialize controller state.
  void begin();

  // Reset the controller.
  void reset();

  // Update the controller using the current odometry (from the Odometry class)
  // and a desired path (an array of [x,y] points in mm).
  // numPoints is the number of target points.
  // This function updates the public member 'currentCommands'.
  void update(const Odometry &odom, float desired_pos[][2], int numPoints);

  // Control parameters (tune these as needed)
  float dt_time;         // time interval (s)
  float WHEELS_DISTANCE; // distance between wheels (mm)
  float a_max;           // maximum acceleration (mm/s^2)
  float v_max;           // maximum forward velocity (mm/s)
  float Kp;              // proportional gain for velocity control
  float Ki;              // integral gain for velocity control
  float Kp_theta;        // gain for heading error
  float Kp_de;           // gain for cross-track error

  // Target velocities for each wheel (mm/s)
  float v_l_target;
  float v_r_target;

  // PID integrators.
  float err_sum_left;
  float err_sum_right;
  
  // For acceleration limiting.
  float prev_v_forward;

  // Public state snapshots.
  CarState car_state;
  PathState path_state;

  // The most recent motor command outputs.
  MotorCommands currentCommands;

private:
  // Internal helper to run the PID control loop and update currentCommands.
  void control();

  // Internal helper to saturate and store motor commands.
  void setMotorSpeeds(int leftSpeed, int rightSpeed);
};

#endif // PATHCONTROLLER_H

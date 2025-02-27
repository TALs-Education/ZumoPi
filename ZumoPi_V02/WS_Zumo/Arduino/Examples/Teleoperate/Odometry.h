#ifndef ODOMETRY_H
#define ODOMETRY_H

#include <Arduino.h>
#include <math.h>

class Odometry {
public:
  float posX, posY, theta;   // Robot's estimated pose (in mm and radians)
  float encoder2dist;        // Conversion factor: mm per encoder pulse
  float wheelBase;           // Distance between wheels in mm
  float dt;                  // Last measured dt in seconds
  // wheel velocities (mm/s)
  float v_left;
  float v_right;

  // Constructor:
  // wheelDiameter (mm), gearRatio (e.g., 75), pulsesPerRev (e.g., 12),
  // wheelDistance (mm)
  Odometry(float wheelDiameter, float gearRatio, float pulsesPerRev, float wheelDistance);

  // Reset the odometry to zero.
  void reset();

  // Update the odometry using incremental encoder counts.
  // dtMicros is the elapsed time in microseconds.
  void update(int deltaRight, int deltaLeft, unsigned long dtMicros);
};

#endif // ODOMETRY_H

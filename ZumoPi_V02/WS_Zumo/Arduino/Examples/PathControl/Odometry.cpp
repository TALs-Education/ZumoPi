#include "Odometry.h"

Odometry::Odometry(float wheelDiameter, float gearRatio, float pulsesPerRev, float wheelDistance) {
  posX = 0.0;
  posY = 0.0;
  theta = 0.0;
  wheelBase = wheelDistance;
  float pulsesPerWheelRev = pulsesPerRev * gearRatio;
  encoder2dist = (PI * wheelDiameter) / pulsesPerWheelRev;
  
  v_left = 0.0;
  v_right = 0.0;
}

void Odometry::reset() {
  posX = 0.0;
  posY = 0.0;
  theta = 0.0;
  v_left = 0.0;
  v_right = 0.0;
}

void Odometry::update(int deltaRight, int deltaLeft, unsigned long dtMicros) {
  // Convert dt from microseconds to seconds.
  dt = dtMicros / 1000000.0f;
  
  // Compute distances traveled by each wheel (in mm).
  float dx_r = deltaRight * encoder2dist;
  float dx_l = deltaLeft  * encoder2dist;
  
  // Calculate wheel velocities (mm/s).
  v_right = dx_r / dt;
  v_left  = dx_l / dt;
  
  // Compute change in orientation.
  float dTheta = (dx_r - dx_l) / wheelBase;
  float dCenter = (dx_r + dx_l) / 2.0;
  
  // Update pose using midpoint integration.
  posX += dCenter * cos(theta + dTheta / 2.0);
  posY += dCenter * sin(theta + dTheta / 2.0);
  theta += dTheta;
}

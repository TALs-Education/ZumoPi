#include "Odometry.h"

Odometry::Odometry(float wheelDiameter, float gearRatio, float pulsesPerRev, float wheelDistance) {
  posX = 0.0;
  posY = 0.0;
  theta = 0.0;
  wheelBase = wheelDistance;
  float pulsesPerWheelRev = pulsesPerRev * gearRatio;
  encoder2dist = (PI * wheelDiameter) / pulsesPerWheelRev;
}

void Odometry::reset() {
  posX = 0.0;
  posY = 0.0;
  theta = 0.0;
}

void Odometry::update(int deltaRight, int deltaLeft) {
  float dx_r = deltaRight * encoder2dist;  // Right wheel distance in mm
  float dx_l = deltaLeft  * encoder2dist;    // Left wheel distance in mm
  float dTheta = (dx_r - dx_l) / wheelBase;   // Change in orientation (radians)
  float dCenter = (dx_r + dx_l) / 2.0;          // Average forward distance (mm)
  
  // Update pose using midpoint integration:
  posX += dCenter * cos(theta + dTheta / 2.0);
  posY += dCenter * sin(theta + dTheta / 2.0);
  theta += dTheta;
}

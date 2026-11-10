"""
Wheel odometry ("Encoder Position Estimation" subsystem), manual section 2.2.

    dL, dR = 2*pi*r * w * dt            (w in rev/s - as in the Simulink model)
    dPhi   = (dL - dR) / L
    X_k    = X_k-1 + (dL+dR)/2 * cos(Phi_k-1 + dPhi/2)
    Y_k    = Y_k-1 + (dL+dR)/2 * sin(Phi_k-1 + dPhi/2)
    Phi_k  = Phi_k-1 + dPhi

Sign convention (kept from the MATLAB model): a faster LEFT wheel increases Phi.
"""
import math


class Odometry:
    def __init__(self, wheel_radius, robot_L, dt, x0=0.0, y0=0.0, phi0=0.0):
        self.k = 2 * math.pi * wheel_radius * dt
        self.L = robot_L
        self.x, self.y, self.phi = x0, y0, phi0

    def update(self, w_left, w_right):
        dL = self.k * w_left
        dR = self.k * w_right
        dphi = (dL - dR) / self.L
        d = (dL + dR) / 2
        self.x += d * math.cos(self.phi + dphi / 2)
        self.y += d * math.sin(self.phi + dphi / 2)
        self.phi += dphi
        return self.x, self.y, self.phi

"""
Simulation parameters - the Python equivalent of InitZumo.m plus the
gains/constants that are set inside the Simulink block diagrams.

All units are SI (meters, seconds, radians) unless stated otherwise.
"""
from dataclasses import dataclass, field, asdict, replace
import math


@dataclass
class ZumoParams:
    # ------------------------------------------------------------------
    # Simulation (InitZumo.m)
    # ------------------------------------------------------------------
    sample_time: float = 0.01          # [s] controller / encoder sample time
    sim_time: float = 40.0             # [s] maximum simulated time

    # ------------------------------------------------------------------
    # Platform characteristics (InitZumo.m)
    # ------------------------------------------------------------------
    gear_ratio: float = 75.0
    wheel_radius: float = 37.5 / 2 / 1000   # [m]
    robot_L: float = 98 / 1000              # [m] distance between wheels

    # ------------------------------------------------------------------
    # Trapezoidal velocity profile (InitZumo.m)
    # ------------------------------------------------------------------
    a_max: float = 1 / 8               # [m/s^2] max linear acceleration
    v_max: float = 1 / 4               # [m/s]   max linear velocity
    # Deceleration limit = decel_factor * a_max  (Rate Limiter falling slew).
    # Path_Control model uses 1, the P2P models use 2.
    decel_factor: float = 1.0

    # ------------------------------------------------------------------
    # Wheel speed PI controllers ("Discrete PID Controller" blocks)
    # Parallel form, forward Euler, output limited to [-1, 1] (PWM duty),
    # clamping anti-windup.
    # ------------------------------------------------------------------
    kp: float = 0.1
    ki: float = 0.01
    pwm_limit: float = 1.0

    # ------------------------------------------------------------------
    # Path / P2P controller gains ("Theta_t Gain", "de Gain" blocks)
    # ------------------------------------------------------------------
    k_theta: float = 0.1               # heading error gain
    k_de: float = 0.25                 # cross-track error gain (path control only)
    stop_distance: float = 0.01        # [m] stop when closer than this to the last point
    pass_distance: float = 0.025       # [m] advance to next way-point when closer than this

    # Simplified open-loop model (Simplified_OpenLoop.slx): fixed internal gains
    ol_gain_theta: float = 0.1
    ol_gain_forward: float = 0.1
    ol_v_max: float = 1.0              # [m/s] (as written inside the MATLAB function)

    # ------------------------------------------------------------------
    # DC motor + H-bridge + gearbox (Simscape "Motor System" subsystem)
    # The Simscape motor is parameterised by stall torque / no-load speed.
    # ------------------------------------------------------------------
    motor_V_rated: float = 6.0             # [V]
    motor_w_noload_rpm: float = 33000.0    # [rpm] at V_rated
    motor_T_stall: float = 0.00215         # [N*m] at V_rated
    motor_J: float = 1e-7                  # [kg*m^2] rotor inertia (1 g*cm^2)
    load_J: float = 2.5e-5                 # [kg*m^2] wheel-side inertia (250 g*cm^2)
    bridge_voltage: float = 4.0            # [V] H-bridge output at 100% duty
    encoder_pulses_per_rev: int = 3        # Hall pulses per motor revolution
    # Small correction for the H-bridge on-resistance drop observed in the
    # Simscape model (steady state speed is 0.1% below V/Ke).
    bridge_efficiency: float = 0.99893

    # ------------------------------------------------------------------
    # Motor noise / non-idealities (not in the MATLAB model, default off)
    # ------------------------------------------------------------------
    motor_mismatch: float = 0.0        # e.g. 0.05 -> right motor 5% weaker than left

    # Initial state (InitZumo.m)
    x0: float = 0.0
    y0: float = 0.0
    phi0: float = 0.0

    # ---------------- derived quantities ----------------
    @property
    def motor_ke(self) -> float:
        """Back-EMF / torque constant [V/(rad/s)] = [N*m/A]."""
        return self.motor_V_rated / (self.motor_w_noload_rpm * 2 * math.pi / 60)

    @property
    def motor_R(self) -> float:
        """Armature resistance [Ohm] derived from the stall torque."""
        return self.motor_V_rated * self.motor_ke / self.motor_T_stall

    @property
    def motor_tau(self) -> float:
        """Mechanical time constant [s] (inductance is negligible: L/R = 50 us)."""
        J_eff = self.motor_J + self.load_J / self.gear_ratio ** 2
        return J_eff * self.motor_R / self.motor_ke ** 2

    @property
    def wheel_speed_gain(self) -> float:
        """Steady state wheel speed [rad/s] per unit PWM duty."""
        return self.bridge_efficiency * self.bridge_voltage / self.motor_ke / self.gear_ratio

    @property
    def w_max(self) -> float:
        """Max wheel speed command [rev/s] (InitZumo.m: v_Max/(2*pi*r))."""
        return self.v_max / (self.wheel_radius * 2 * math.pi)

    def copy(self, **changes) -> "ZumoParams":
        return replace(self, **changes)

    def as_dict(self) -> dict:
        return asdict(self)

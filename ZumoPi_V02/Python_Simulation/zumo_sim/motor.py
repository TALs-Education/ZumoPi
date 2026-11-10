"""
Wheel drive model: DC motor + gearbox + Hall encoder, and the wheel speed
PI controller.

This replaces the Simscape "DC Motor Simulation Left/Right" subsystems:

    PWM duty u  ->  H-bridge (averaged)  ->  DC motor  ->  75:1 gear  ->  wheel
                                              |
                                  Hall encoder (3 pulses / motor rev)
                                              |
                     pulse-period speed decoder + 1-sample delay  ->  measured speed

The electrical time constant (L/R ~ 50 us) is far below the 10 ms sample
time, so the motor reduces to a first order system:

    tau * d(w)/dt = K * u - w          w = wheel speed [rad/s]
"""
import math
import numpy as np


class WheelDrive:
    """One motor + gearbox + Hall encoder, integrated with sub-steps."""

    def __init__(self, p, gain_scale: float = 1.0, substeps: int = 10):
        self.p = p
        self.K = p.wheel_speed_gain * gain_scale      # [rad/s per unit duty]
        self.tau = p.motor_tau                        # [s]
        self.dt = p.sample_time
        self.n = substeps
        self.h = self.dt / substeps
        self.edge_angle = 2 * math.pi / p.encoder_pulses_per_rev   # motor rad / pulse
        self.reset()

    def reset(self):
        self.t = 0.0
        self.w = 0.0                  # true wheel speed [rad/s]
        self.motor_angle = 0.0        # motor shaft angle [rad]
        self.edge_idx = 0             # index of last encoder edge passed
        self.t_edges = []             # times of the last two edges
        self.edge_dir = 0.0
        self.decoded = 0.0            # decoder output (before unit delay) [wheel rad/s]
        self.measured = 0.0           # after the unit delay [wheel rad/s]

    def step(self, u: float):
        """Apply duty `u` for one sample period. Returns measured wheel speed
        for the *next* sample (includes the decoder's unit delay)."""
        u = max(-1.0, min(1.0, u))
        w_ss = self.K * u
        a = math.exp(-self.h / self.tau)
        G = self.p.gear_ratio
        for _ in range(self.n):
            w0 = self.w
            # exact solution of the first order system over one sub step
            self.w = w_ss + (w0 - w_ss) * a
            d_wheel = w_ss * self.h + (w0 - w_ss) * self.tau * (1 - a)
            th0 = self.motor_angle
            self.motor_angle += G * d_wheel
            self._detect_edges(th0, self.motor_angle, self.t, self.t + self.h)
            self.t += self.h

        # unit delay: what the controller sees at the next sample
        self.measured = self.decoded
        self.decoded = self._decode(self.t)
        return self.measured

    # ---------------- Hall encoder ----------------
    def _detect_edges(self, th0, th1, t0, t1):
        k1 = math.floor(th1 / self.edge_angle)
        if k1 == self.edge_idx:
            return
        step = 1 if k1 > self.edge_idx else -1
        while self.edge_idx != k1:
            nxt = self.edge_idx + (1 if step > 0 else 0)
            th_e = nxt * self.edge_angle
            frac = (th_e - th0) / (th1 - th0) if th1 != th0 else 0.0
            te = t0 + frac * (t1 - t0)
            if self.edge_dir != step:      # direction change: restart period timing
                self.t_edges = []
                self.edge_dir = step
            self.t_edges = (self.t_edges + [te])[-2:]
            self.edge_idx += step

    def _decode(self, t_now):
        """Pulse frequency -> rpm -> wheel rad/s ("Pulse decode" + f2rpm)."""
        if len(self.t_edges) < 2:
            return 0.0
        period = self.t_edges[-1] - self.t_edges[-2]
        period = max(period, t_now - self.t_edges[-1])  # decays when the motor stops
        freq = 1.0 / period
        rpm_motor = freq * 60.0 / self.p.encoder_pulses_per_rev
        return self.edge_dir * rpm_motor * 2 * math.pi / 60 / self.p.gear_ratio


class PIController:
    """Discrete PI controller, parallel form, output saturation and clamping
    anti-windup - same as the Simulink 'Discrete PID Controller' blocks.

    IMPORTANT: the Simulink blocks use an integrator in *Accumulation* mode
    (gainval = 1), i.e. the integral is a plain running sum WITHOUT the
    sample time:

        integ[k+1] = integ[k] + Ki * e[k]          (Ki per sample)
        u[k]       = Kp * e[k] + integ[k]

    So Ki = 0.01 here corresponds to a continuous-time Ki of 0.01/Ts = 1.0 1/s.
    This is also how the integral is written in the robot's C++ code.
    """

    def __init__(self, kp, ki, ts, limit=1.0):
        self.kp, self.ki, self.ts, self.limit = kp, ki, ts, limit
        self.integ = 0.0

    def reset(self):
        self.integ = 0.0

    def update(self, error: float) -> float:
        pre = self.kp * error + self.integ
        out = min(self.limit, max(-self.limit, pre))
        # clamping: stop integrating when saturated and the error pushes further
        saturated = pre != out
        same_sign = np.sign(pre) == np.sign(self.ki * error)
        if not (saturated and same_sign):
            self.integ += self.ki * error
        return out

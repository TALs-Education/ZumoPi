"""
Wheel speed loop on its own: open-loop step (constant PWM) and closed-loop
PI step response. Use it to understand the motor PI gains (manual section 6)
before tuning the path controller.

    python examples/wheel_step_response.py
"""
import os
import sys
import math
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from zumo_sim import ZumoParams  # noqa: E402
from zumo_sim.motor import WheelDrive, PIController  # noqa: E402

p = ZumoParams()
dt, T = p.sample_time, 3.0
t = np.arange(0, T, dt)

fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(9, 9), sharex=True)

# 1) open loop: constant duty
for u in (0.1, 0.3, 0.5):
    m = WheelDrive(p)
    w = [0.0] + [m.step(u) for _ in t[1:]]
    a1.plot(t, w, label=f"duty = {u}")
a1.set_title(f"Open loop (tau = {p.motor_tau * 1000:.0f} ms, "
             f"gain = {p.wheel_speed_gain:.1f} per unit duty)")
a1.set_ylabel("measured wheel speed")
a1.grid(True); a1.legend()

# 2) closed loop: speed set point step, different PI gains
v_set = 0.15                                        # [m/s]
w_set = v_set / (2 * math.pi * p.wheel_radius)      # [rev/s] as in the model
for kp, ki in [(0.1, 0.01), (0.05, 0.005), (0.3, 0.01), (0.1, 0.05)]:
    m = WheelDrive(p)
    pi = PIController(kp, ki, dt, p.pwm_limit)
    w_meas, W, U = 0.0, [], []
    for _ in t:
        u = pi.update(w_set - w_meas)
        W.append(w_meas); U.append(u)
        w_meas = m.step(u)
    a2.plot(t, W, label=f"Kp={kp}, Ki={ki}")
    a3.plot(t, U, label=f"Kp={kp}, Ki={ki}")
a2.axhline(w_set, color="k", ls=":", label="set point")
a2.set_title(f"Closed loop PI, set point {v_set} m/s")
a2.set_ylabel("wheel speed"); a2.grid(True); a2.legend(fontsize=8)
a3.set_ylabel("PWM duty"); a3.set_xlabel("time [s]"); a3.grid(True); a3.legend(fontsize=8)
fig.tight_layout()
plt.show()

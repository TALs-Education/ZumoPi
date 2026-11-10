"""
Gain tuning experiment: sweep one path control gain and compare the
resulting trajectories (deliverable: "plots illustrating at least one
gain-tuning experiment").

    python examples/gain_sweep.py
"""
import os
import sys
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from zumo_sim import ZumoParams, simulate, paths  # noqa: E402

points = paths.infinity()
GAIN = "k_de"                       # try: "k_theta", "k_de", "kp", "ki", "a_max"
VALUES = [0.0, 0.25, 1.0, 2.0]
base = ZumoParams(k_theta=0.3, k_de=0.25)

fig, (ax_xy, ax_de) = plt.subplots(1, 2, figsize=(13, 5.5))
ax_xy.plot(points[:, 0], points[:, 1], "k*", ms=5, label="desired")
print(f"{GAIN:>8s} {'finish[s]':>10s} {'final[mm]':>10s} {'max dev[mm]':>12s} {'rms dev[mm]':>12s}")
for v in VALUES:
    r = simulate(points, "path", base.copy(**{GAIN: v}))
    m = r.metrics()
    ft = f"{m['finish_time']:.2f}" if m["finish_time"] is not None else "--"
    print(f"{v:8.3g} {ft:>10s} {m['final_error_mm']:10.1f} {m['max_path_dev_mm']:12.1f} {m['rms_path_dev_mm']:12.1f}")
    ax_xy.plot(r.x, r.y, label=f"{GAIN}={v:g}")
    ax_de.plot(r.t, r.de * 1000, label=f"{GAIN}={v:g}")

ax_xy.set_aspect("equal"); ax_xy.grid(True); ax_xy.legend()
ax_xy.set_xlabel("X [m]"); ax_xy.set_ylabel("Y [m]"); ax_xy.set_title(f"Path control - sweep of {GAIN}")
ax_de.grid(True); ax_de.legend(); ax_de.set_xlabel("time [s]"); ax_de.set_ylabel("de [mm]")
ax_de.set_title("Cross-track error")
fig.tight_layout()
plt.show()

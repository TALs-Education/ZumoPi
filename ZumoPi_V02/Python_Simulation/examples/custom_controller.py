"""
Template for writing your OWN path controller and comparing it with the
original one. Copy this file, change MyController.update(), run it.

The example below adds a "look-ahead" (pure-pursuit flavour): instead of the
heading error to the current segment, it steers toward a point that is
`lookahead` meters further along the path.

    python examples/custom_controller.py
"""
import os
import sys
import math
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from zumo_sim import ZumoParams, simulate, paths, PathController  # noqa: E402


class MyController(PathController):
    """Same way-point handling as PathController, different heading error."""

    def __init__(self, points, lookahead=0.08, **kw):
        super().__init__(points, **kw)
        self.lookahead = lookahead

    def update(self, pos, phi, a_max):
        v, theta_t, de, dist, en = super().update(pos, phi, a_max)
        if en == 0:
            return v, theta_t, de, dist, en
        # find the first way-point at least `lookahead` away (from the current target on)
        target = self.points[-1]
        for p in self.points[self.curr:]:
            if np.linalg.norm(p - pos) >= self.lookahead:
                target = p
                break
        Vr = np.array([math.cos(phi), math.sin(phi)])
        Vt = target - pos
        ang = math.atan2(Vr[0] * Vt[1] - Vr[1] * Vt[0], Vr @ Vt)   # signed angle Vr -> Vt
        return v, ang, 0.0, dist, en                                  # de not used


points = paths.infinity()
p = ZumoParams(k_theta=0.3, k_de=0.5)

r_orig = simulate(points, "path", p)
r_mine = simulate(points, "path", p, controller=MyController(points, lookahead=0.08,
                                                             stop_distance=p.stop_distance,
                                                             pass_distance=p.pass_distance))
for name, r in [("original", r_orig), ("look-ahead", r_mine)]:
    m = r.metrics()
    print(f"{name:10s} finish={m['finish_time']}  max dev={m['max_path_dev_mm']:.1f} mm  "
          f"rms dev={m['rms_path_dev_mm']:.1f} mm")

plt.plot(points[:, 0], points[:, 1], "k*", ms=5, label="desired")
plt.plot(r_orig.x, r_orig.y, label="original PathController")
plt.plot(r_mine.x, r_mine.y, label="MyController (look-ahead)")
plt.axis("equal"); plt.grid(True); plt.legend()
plt.xlabel("X [m]"); plt.ylabel("Y [m]")
plt.show()

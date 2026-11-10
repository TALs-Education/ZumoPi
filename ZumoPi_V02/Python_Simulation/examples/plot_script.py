"""
Python version of plotScript.m

Runs the P2P (multi-point) and the Path control simulations on the same
desired coordinates and plots both trajectories.

    python examples/plot_script.py
"""
import os
import sys
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from zumo_sim import ZumoParams, simulate, paths  # noqa: E402

# ---- desired coordinates (choose one) --------------------------------------
DesiredCoordinates = paths.line(2.0, 0.2)        # [0 0.2; 0 0.4; ... 0 2]
# DesiredCoordinates = paths.infinity()           # figure-eight (infSignMath.m)
# DesiredCoordinates = [[0, 0.5], [0, 1.0], [0, 1.5], [0, 2.0]]

# ---- parameters -------------------------------------------------------------
# P2P model: deceleration = 2*a_max ; Path model: deceleration = a_max
p2p_params = ZumoParams(sim_time=30, decel_factor=2.0, k_theta=0.1)
path_params = ZumoParams(sim_time=30, decel_factor=1.0, k_theta=0.1, k_de=0.25)

# ---- run simulations --------------------------------------------------------
Record_P2P = simulate(DesiredCoordinates, "p2p", p2p_params)
Record_Path = simulate(DesiredCoordinates, "path", path_params)

for name, r in [("P2P", Record_P2P), ("Path", Record_Path)]:
    m = r.metrics()
    print(f"{name:5s} finish={m['finish_time']}  final error={m['final_error_mm']:.1f} mm  "
          f"max deviation={m['max_path_dev_mm']:.1f} mm")

# ---- plot ---------------------------------------------------------------------
pts = Record_Path.points
plt.figure(1)
plt.plot(Record_P2P.x, Record_P2P.y, label="P2P")
plt.plot(Record_Path.x, Record_Path.y, label="Path")
plt.plot(pts[:, 0], pts[:, 1], "*", label="desired")
plt.legend()
plt.grid(True)
plt.title("Path Control")
plt.xlabel("XPos [m]")
plt.ylabel("YPos [m]")
plt.show()

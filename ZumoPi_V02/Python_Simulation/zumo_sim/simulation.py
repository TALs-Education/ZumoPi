"""
Closed loop simulation - the Python equivalent of the Simulink diagrams.

Signal flow per sample k (dt = 10 ms), same order as the Simulink models:

  pose[k-1] --> Path/P2P controller --> V_forward, theta_t, de, En
                                           |
      V_forward -> Rate Limiter (a_max) -> Saturation (v_max) -> V
      turn = k_theta*theta_t + k_de*de            [m/s]
      v_left  = V + turn ,  v_right = V - turn     [m/s]
      w_sp    = v / (2*pi*r)                       [rev/s] wheel speed set point
                                           |
      error = w_sp - w_meas  -> PI -> PWM duty (x En) -> motor -> encoder -> w_meas
                                           |
      odometry(w_meas) -> pose[k]
"""
from dataclasses import dataclass, field
import math
import numpy as np

from .params import ZumoParams
from .motor import WheelDrive, PIController
from .odometry import Odometry
from .controllers import PathController, P2PController, OpenLoopP2P

MODES = {
    "path": "Path control (trajectory following)",
    "p2p": "Point to point (multi way-point)",
    "open_loop": "Simplified open loop (no wheel PI)",
}


class RateLimiter:
    def __init__(self, rising, falling, ts, y0=0.0):
        self.r, self.f, self.ts, self.y = rising, falling, ts, y0

    def update(self, u):
        dy = u - self.y
        dy = min(self.r * self.ts, max(self.f * self.ts, dy))
        self.y += dy
        return self.y


@dataclass
class SimResult:
    mode: str
    points: np.ndarray
    params: ZumoParams
    t: np.ndarray = None
    x: np.ndarray = None
    y: np.ndarray = None
    phi: np.ndarray = None
    v_request: np.ndarray = None   # V_forward from the path controller [m/s]
    v_cmd: np.ndarray = None       # after rate limiter + saturation [m/s]
    theta_t: np.ndarray = None     # heading error [rad]
    de: np.ndarray = None          # cross track error [m]
    dist: np.ndarray = None        # remaining distance [m]
    en: np.ndarray = None
    wl_sp: np.ndarray = None       # wheel speed set points [rev/s]
    wr_sp: np.ndarray = None
    wl: np.ndarray = None          # measured wheel speeds (encoder)
    wr: np.ndarray = None
    ul: np.ndarray = None          # PWM duty commands [-1..1]
    ur: np.ndarray = None
    target_idx: np.ndarray = None
    finish_time: float = None

    # ------------- performance metrics -------------
    def metrics(self):
        """Simple tracking metrics used in the GUI and the manual."""
        pos = np.column_stack([self.x, self.y])
        path = np.vstack([[self.params.x0, self.params.y0], self.points])
        d = _dist_to_polyline(pos, path)
        final_err = float(np.linalg.norm(pos[-1] - self.points[-1]))
        return {
            "finish_time": None if self.finish_time is None else round(self.finish_time, 2),
            "final_error_mm": final_err * 1000,
            "max_path_dev_mm": float(d.max() * 1000),
            "rms_path_dev_mm": float(np.sqrt(np.mean(d ** 2)) * 1000),
            "path_length_m": float(np.sum(np.linalg.norm(np.diff(pos, axis=0), axis=1))),
        }


def _dist_to_polyline(pts, poly):
    """Distance of each point in pts to the polyline poly."""
    best = np.full(len(pts), np.inf)
    for a, b in zip(poly[:-1], poly[1:]):
        ab = b - a
        L2 = float(ab @ ab)
        if L2 == 0:
            d = np.linalg.norm(pts - a, axis=1)
        else:
            s = np.clip(((pts - a) @ ab) / L2, 0, 1)
            d = np.linalg.norm(pts - (a + s[:, None] * ab), axis=1)
        best = np.minimum(best, d)
    return best


def simulate(points, mode="path", params: ZumoParams = None, stop_when_done=True,
             controller=None):
    """Run one simulation.

    points          Nx2 array of way-points [m]
    mode            'path' | 'p2p' | 'open_loop'
    params          ZumoParams (defaults = InitZumo.m + model gains)
    stop_when_done  end the run 0.5 s after the controller disables the motors
    controller      optional custom controller object with the same interface
                    as PathController / P2PController (for student experiments)
    """
    p = params or ZumoParams()
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    dt = p.sample_time
    N = int(round(p.sim_time / dt)) + 1

    # --- blocks ---
    if controller is not None:
        ctrl = controller
    elif mode == "path":
        ctrl = PathController(pts, p.stop_distance, p.pass_distance, start=(p.x0, p.y0))
    elif mode == "p2p":
        ctrl = P2PController(pts, p.stop_distance, p.pass_distance)
    elif mode == "open_loop":
        ctrl = OpenLoopP2P(pts, p.ol_gain_theta, p.ol_gain_forward, p.ol_v_max, p.wheel_radius)
    else:
        raise ValueError(f"unknown mode {mode!r}")

    left = WheelDrive(p, gain_scale=1.0)
    right = WheelDrive(p, gain_scale=1.0 - p.motor_mismatch)
    pi_l = PIController(p.kp, p.ki, dt, p.pwm_limit)
    pi_r = PIController(p.kp, p.ki, dt, p.pwm_limit)
    limiter = RateLimiter(p.a_max, -p.a_max * p.decel_factor, dt)
    odo = Odometry(p.wheel_radius, p.robot_L, dt, p.x0, p.y0, p.phi0)
    m_to_rev = 1.0 / (p.wheel_radius * 2 * math.pi)

    r = SimResult(mode, pts, p)
    names = ["t", "x", "y", "phi", "v_request", "v_cmd", "theta_t", "de", "dist", "en",
             "wl_sp", "wr_sp", "wl", "wr", "ul", "ur", "target_idx"]
    buf = {n: np.zeros(N) for n in names}

    wl_meas = wr_meas = 0.0
    x_prev, y_prev, phi_prev = p.x0, p.y0, p.phi0   # "Delay" block on the pose feedback
    done_count = 0
    k_end = N
    for k in range(N):
        t = k * dt
        pos_prev = np.array([x_prev, y_prev])

        if mode == "open_loop" and controller is None:
            ul_cmd, ur_cmd, theta_t = ctrl.update(pos_prev, phi_prev)
            v_req = v_cmd = de = dist = 0.0
            en = 1
            wl_sp = wr_sp = float("nan")
            wl_o, wr_o = wl_meas, wr_meas
            ul = max(-1.0, min(1.0, ul_cmd))
            ur = max(-1.0, min(1.0, ur_cmd))
        else:
            out = ctrl.update(pos_prev, phi_prev, p.a_max)
            if len(out) == 5:
                v_req, theta_t, de, dist, en = out
            else:
                v_req, theta_t, dist, en = out
                de = 0.0
            v_cmd = max(-p.v_max, min(p.v_max, limiter.update(v_req)))
            turn = p.k_theta * theta_t + p.k_de * de
            wl_sp = (v_cmd + turn) * m_to_rev
            wr_sp = (v_cmd - turn) * m_to_rev
            # measured speeds are gated by En inside the motor subsystem
            wl_o, wr_o = wl_meas * en, wr_meas * en
            ul = pi_l.update(wl_sp - wl_o) * en
            ur = pi_r.update(wr_sp - wr_o) * en

        x, y, phi = odo.update(wl_o, wr_o)

        b = buf
        b["t"][k] = t; b["x"][k] = x; b["y"][k] = y; b["phi"][k] = phi
        b["v_request"][k] = v_req; b["v_cmd"][k] = v_cmd
        b["theta_t"][k] = theta_t; b["de"][k] = de; b["dist"][k] = dist; b["en"][k] = en
        b["wl_sp"][k] = wl_sp; b["wr_sp"][k] = wr_sp; b["wl"][k] = wl_o; b["wr"][k] = wr_o
        b["ul"][k] = ul; b["ur"][k] = ur
        b["target_idx"][k] = getattr(ctrl, "curr", 0)

        # plant runs during [t, t+dt) with the commanded duty
        wl_meas = left.step(ul)
        wr_meas = right.step(ur)
        x_prev, y_prev, phi_prev = x, y, phi

        if en == 0:
            if r.finish_time is None:
                r.finish_time = t
            done_count += 1
            if stop_when_done and done_count * dt >= 0.5:
                k_end = k + 1
                break
        if mode == "open_loop" and controller is None:
            if np.linalg.norm(np.array([x, y]) - pts[-1]) < p.stop_distance and r.finish_time is None:
                r.finish_time = t

    for n in names:
        setattr(r, n, buf[n][:k_end])
    return r

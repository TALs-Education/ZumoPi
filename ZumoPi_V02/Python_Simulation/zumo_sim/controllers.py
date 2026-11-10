"""
Path controllers - direct Python ports of the MATLAB Function blocks:

    PathController      <- "Path Control"            (ZumoSimulatiom_Path_Control.slx)
    P2PController       <- "Point to Point Control"  (ZumoSimulatiom_P2P_MultiPoint.slx,
                                                       ZumoSimulatiom_P2P.slx with one point)
    OpenLoopP2P         <- "Point to Point Control"  (Simplified_OpenLoop.slx)

STUDENTS: this is the file to read and modify. Each controller receives the
current position estimate and returns the forward velocity request and the
angle errors. The gains that turn those errors into wheel commands are
applied in simulation.py (the "Theta_t Gain" / "de Gain" blocks).

Vector notation (see manual section 4.3):
    Vr  robot direction vector      [cos(phi), sin(phi)]
    Vt  robot -> current target point
    Vd  previous point -> current target point (the desired path segment)

Note on 2D cross products: for a=[ax,ay], b=[bx,by]
    cross(a, b) = ax*by - ay*bx   (z component, positive if b is CCW from a)
"""
import math
import numpy as np


def _cross(a, b):
    """z component of the 2D cross product a x b."""
    return a[0] * b[1] - a[1] * b[0]


def _remaining_path_length(points, idx):
    """Sum of the segment lengths from point idx to the last point."""
    return float(np.sum(np.linalg.norm(np.diff(points[idx:], axis=0), axis=1)))


class PathController:
    """Trajectory (path following) control.

    Outputs:
        v_forward  requested forward velocity sqrt(2*a_max*dist)  [m/s]
        theta_t    heading error: angle between robot direction and path segment [rad]
        de         cross-track error: signed distance from the path segment [m]
        dist       remaining distance along the path [m]
        en         1 while driving, 0 once the last point was reached
    """

    def __init__(self, points, stop_distance=0.01, pass_distance=0.025, start=(0.0, 0.0)):
        self.points = np.asarray(points, dtype=float).reshape(-1, 2)
        self.stop_distance = stop_distance
        self.pass_distance = pass_distance
        self.start = np.asarray(start, dtype=float)   # start of the first path segment
        self.curr = 0          # index of the current target point (MATLAB currPoint-1)

    def reset(self):
        self.curr = 0

    def update(self, pos, phi, a_max):
        P = self.points
        n = len(P)
        i = self.curr

        Vr = np.array([math.cos(phi), math.sin(phi)])      # robot direction
        Vt = P[i] - pos                                       # robot -> target point
        if i > 0:
            Vd = P[i] - P[i - 1]                              # desired path segment
        else:
            Vd = P[i] - self.start                            # first segment: start -> first point

        cross_vr_vd = _cross(Vr, Vd)
        cross_vd_vt = _cross(Vd, Vt)                         # MATLAB: crossVtVd
        dot_vd_vr = float(Vd @ Vr) / (np.linalg.norm(Vd) * np.linalg.norm(Vr))

        de = cross_vd_vt / np.linalg.norm(Vd)                # distance to the desired path

        dist = float(np.linalg.norm(Vt))                     # distance to the current point
        if i < n - 1:
            path_dist = _remaining_path_length(P, i)
            # advance to the next point
            if abs(dist) < self.pass_distance:
                self.curr += 1
            else:
                # missed the point? jump if the next point is already closer
                dist_next = np.linalg.norm(P[i + 1] - pos)
                if dist_next < dist:
                    self.curr += 1
            dist = dist + path_dist

        # heading error relative to the path segment
        if abs(cross_vr_vd) < 1e-5:                          # singularity (~0.13 deg)
            theta_t = math.pi / 2 if dot_vd_vr == -1 else 0.0
        else:
            theta_t = math.acos(np.clip(dot_vd_vr, -1, 1)) * np.sign(cross_vr_vd)

        # forward velocity request (trapezoidal profile: v = sqrt(2*a*s))
        if self.curr == n - 1:
            # stop at the last point, or if we drove past it
            passed = float(Vt @ Vr) / np.linalg.norm(Vr) < -self.pass_distance
            if abs(dist) < self.stop_distance or passed:
                return 0.0, 0.0, de, dist, 0
        return math.sqrt(2 * a_max * dist), theta_t, de, dist, 1


class P2PController:
    """Point-to-point control through a list of way-points.

    The robot simply turns toward the current target point (no notion of the
    path between points). Outputs: v_forward, theta_t, dist, en.
    """

    def __init__(self, points, stop_distance=0.01, pass_distance=0.025):
        self.points = np.asarray(points, dtype=float).reshape(-1, 2)
        self.stop_distance = stop_distance
        self.pass_distance = pass_distance
        self.curr = 0

    def reset(self):
        self.curr = 0

    def update(self, pos, phi, a_max):
        P = self.points
        n = len(P)
        i = self.curr

        Vr = np.array([math.cos(phi), math.sin(phi)])        # robot direction
        Vt = P[i] - pos                                       # robot -> target point

        cross_vr_vt = _cross(Vr, Vt)
        nt = np.linalg.norm(Vt)
        dot_vt_vr = float(Vt @ Vr) / (nt * np.linalg.norm(Vr)) if nt > 0 else 1.0

        if abs(cross_vr_vt) < 1e-5:
            theta_t = math.pi / 2 if dot_vt_vr == -1 else 0.0
        else:
            theta_t = math.acos(np.clip(dot_vt_vr, -1, 1)) * np.sign(cross_vr_vt)

        dist = float(nt)
        if i < n - 1:
            path_dist = _remaining_path_length(P, i)
            if abs(dist) < self.pass_distance:
                self.curr += 1
            else:
                dist_next = np.linalg.norm(P[i + 1] - pos)
                if dist_next < dist:
                    self.curr += 1
            dist = dist + path_dist

        if abs(dist) < self.stop_distance:
            return 0.0, 0.0, dist, 0
        return math.sqrt(2 * a_max * dist), theta_t, dist, 1


class OpenLoopP2P:
    """Simplified_OpenLoop.slx: steer to a single point, motor PWM commands are
    computed directly from the position error (no wheel speed feedback)."""

    def __init__(self, target, gain_theta=0.1, gain_forward=0.1,
                 v_max=1.0, wheel_radius=37.5 / 2 / 1000):
        self.target = np.asarray(target, dtype=float).reshape(-1, 2)[-1]
        self.gain_theta = gain_theta
        self.gain_forward = gain_forward
        self.w_max = v_max / (wheel_radius * 2 * math.pi)

    def reset(self):
        pass

    def update(self, pos, phi):
        Vr = np.array([math.cos(phi), math.sin(phi)])
        Vt = self.target - pos
        d = np.sign(_cross(Vr, Vt))
        nt = np.linalg.norm(Vt)
        dot = float(Vt @ Vr) / (nt * np.linalg.norm(Vr)) if nt > 0 else 1.0
        if d == 0 and dot == -1:
            theta_t = math.pi / 2
        else:
            theta_t = math.acos(np.clip(dot, -1, 1)) * d * self.gain_theta
        w_forward = min(nt * self.gain_forward, self.w_max)
        left = w_forward + theta_t
        right = w_forward - theta_t
        return left, right, theta_t

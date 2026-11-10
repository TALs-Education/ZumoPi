"""
Ready-made desired paths (Nx2 arrays of way-points, meters).
Students: add your own path functions here (manual: "define a path of your
choosing, up to 1x1 m, 50-100 points").
"""
import math
import numpy as np


def line(length=2.0, step=0.2):
    """plotScript.m: DesiredCoordinates = ([0.2:0.2:2].*[0;1])'"""
    y = np.arange(step, length + 1e-9, step)
    return np.column_stack([np.zeros_like(y), y])


def single_point(x=-1.0, y=1.0):
    """ZumoSimulatiom_P2P.slx default target."""
    return np.array([[x, y]])


def square(size=0.5):
    return np.array([[0, size], [size, size], [size, 0], [0, 0]], dtype=float)


def infinity(scale=0.5, step=0.1):
    """infSignMath.m: figure-eight. The first sample coincides with the
    start position (0,0) and is dropped (a zero-length segment is undefined)."""
    t = np.arange(-math.pi / 2, 3 * math.pi / 2 + 1e-9, step)
    pts = np.column_stack([np.cos(t) * scale, np.cos(t) * np.sin(t) * scale])
    return pts[1:]


def circle(radius=0.4, n=60):
    """Circle that starts at the origin heading along +x."""
    a = np.linspace(-math.pi / 2, 3 * math.pi / 2, n + 1)[1:]
    return np.column_stack([radius * np.cos(a), radius * np.sin(a) + radius])


def zigzag(width=0.3, length=1.0, n_zig=4):
    y = np.linspace(0, length, 2 * n_zig + 1)[1:]
    x = np.array([width if i % 2 == 0 else 0.0 for i in range(len(y))])
    return np.column_stack([x, y])


def sine(amplitude=0.2, length=1.0, n=60):
    x = np.linspace(0, length, n + 1)[1:]
    return np.column_stack([x, amplitude * np.sin(2 * math.pi * x / length)])


PRESETS = {
    "Line 2 m (plotScript)": line,
    "Line 1 m (manual)": lambda: line(1.0, 0.2),
    "Single point (-1, 1)": single_point,
    "Square 0.5 m": square,
    "Infinity (infSignMath)": infinity,
    "Circle r=0.4 m": circle,
    "Sine wave": sine,
    "Zig-zag": zigzag,
}


def parse_points(text):
    """Parse '0 0.2; 0 0.4; 0.5 0.5' (MATLAB style) or one 'x, y' pair per line."""
    text = text.replace("[", "").replace("]", "")
    rows = [r for r in text.replace("\n", ";").split(";") if r.strip()]
    pts = []
    for r in rows:
        vals = [float(v) for v in r.replace(",", " ").split()]
        if len(vals) != 2:
            raise ValueError(f"each point needs 2 values, got: {r!r}")
        pts.append(vals)
    if not pts:
        raise ValueError("no points given")
    return np.array(pts)


def format_points(pts):
    return ";\n".join(f"{x:.4g} {y:.4g}" for x, y in pts)


def to_cpp(pts, scale=1000.0, name="desiredPath"):
    """Convert way-points [m] to a C++ array for PathControl.ino (robot uses mm).

    >>> print(to_cpp([[0.1, 0], [0.2, 0.1]]))
    float desiredPath[][2] = { {100, 0}, {200, 100} };
    """
    items = ", ".join(f"{{{x * scale:.4g}, {y * scale:.4g}}}" for x, y in np.asarray(pts, dtype=float))
    return f"float {name}[][2] = {{ {items} }};"

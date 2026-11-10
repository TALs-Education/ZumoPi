"""
Block diagram preview of the simulated control structure, arranged like the
Simulink models (left to right: path controller -> velocity profile / gains ->
wheel speed PI loops -> motors -> odometry, with the z^-1 pose feedback below).

    draw_block_diagram(ax, mode, params)

Colour code:
    blue    outer loop  - position feedback (odometry -> z^-1 -> controller)
    orange  inner loops - wheel speed feedback (encoder -> PI), one per wheel
    grey    block exists in the Simulink family but is not used in this mode
"""
import math
from matplotlib.patches import FancyBboxPatch, Polygon, Circle

C_OUTER = "#1f77b4"
C_INNER = "#ff7f0e"
C_SIG = "#333333"
C_OFF = "#b0b0b0"
FILL = {"ctrl": "#e8f0fb", "prof": "#eef7ee", "pi": "#fff1e0", "motor": "#e9f7e9",
        "odo": "#f3ecfa", "gain": "#ffffff", "off": "#f4f4f4"}

TITLES = {
    "path": "Path control  (ZumoSimulatiom_Path_Control.slx)",
    "p2p": "Point to point, multi way-point  (ZumoSimulatiom_P2P_MultiPoint.slx / ZumoSimulatiom_P2P.slx)",
    "open_loop": "Simplified open loop  (Simplified_OpenLoop.slx)",
}


class _D:
    def __init__(self, ax):
        self.ax = ax

    def box(self, x, y, w, h, text, kind="gain", active=True, fs=8, bold=False, sub=None):
        ax = self.ax
        fc = FILL[kind] if active else FILL["off"]
        ec = "#222222" if active else C_OFF
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.4",
                                    fc=fc, ec=ec, lw=1.3 if active else 1.0,
                                    ls="-" if active else "--", zorder=3))
        ax.text(x + w / 2, y + h / 2 + (0.6 if sub else 0), text, ha="center", va="center",
                fontsize=fs, color="#111" if active else C_OFF, zorder=4,
                fontweight="bold" if bold else "normal")
        if sub:
            ax.text(x + w / 2, y + h / 2 - 1.0, sub, ha="center", va="center", fontsize=fs - 1.5,
                    color="#444" if active else C_OFF, zorder=4, family="monospace")

    def gain(self, x, y, w, h, text, active=True, label=None):
        ec = "#222" if active else C_OFF
        self.ax.add_patch(Polygon([[x, y - h / 2], [x, y + h / 2], [x + w, y]], closed=True,
                                  fc="white" if active else FILL["off"], ec=ec,
                                  ls="-" if active else "--", lw=1.2, zorder=3))
        self.ax.text(x + w * 0.38, y, text, ha="center", va="center", fontsize=7,
                     color="#111" if active else C_OFF, zorder=4)
        if label:
            self.ax.text(x + w / 2, y - h / 2 - 0.9, label, ha="center", va="top", fontsize=7,
                         color="#333" if active else C_OFF, family="monospace")

    def sum(self, x, y, signs="++", r=1.1, active=True, second="top"):
        """signs[0]: left input, signs[1]: input entering from `second` (top/bottom)."""
        self.ax.add_patch(Circle((x, y), r, fc="white", ec="#222" if active else C_OFF,
                                 lw=1.2, zorder=3))
        self.ax.text(x, y, "Σ", ha="center", va="center", fontsize=8, zorder=4)
        self.ax.text(x - r - 0.3, y + 0.9, signs[0], fontsize=7, ha="right", va="bottom")
        if second == "top":
            self.ax.text(x + 0.9, y + r + 0.2, signs[1], fontsize=7, ha="left", va="bottom")
        else:
            self.ax.text(x + 0.9, y - r - 0.2, signs[1], fontsize=7, ha="left", va="top")

    def wire(self, pts, color=C_SIG, lw=1.2, arrow=True, ls="-", label=None, lpos=0, loff=(0, 0.5),
             lcolor=None, fs=7):
        xs, ys = zip(*pts)
        self.ax.plot(xs, ys, color=color, lw=lw, ls=ls, zorder=2, solid_capstyle="butt")
        if arrow:
            (x0, y0), (x1, y1) = pts[-2], pts[-1]
            self.ax.annotate("", xy=(x1, y1), xytext=(x0 + (x1 - x0) * 0.6, y0 + (y1 - y0) * 0.6),
                             arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                             mutation_scale=9, shrinkA=0, shrinkB=0), zorder=2)
        if label:
            (x0, y0), (x1, y1) = pts[lpos], pts[lpos + 1]
            self.ax.text((x0 + x1) / 2 + loff[0], (y0 + y1) / 2 + loff[1], label, ha="center",
                         va="bottom", fontsize=fs, color=lcolor or color)

    def dot(self, x, y, color=C_SIG):
        self.ax.plot([x], [y], "o", ms=3, color=color, zorder=4)


def draw_block_diagram(ax, mode, p, font_scale=None):
    """Draw the control structure for `mode` ('path' | 'p2p' | 'open_loop')
    with the current parameter values `p` (ZumoParams).

    font_scale: multiply all font sizes (None = fit the fonts to the axes size,
    so the text keeps its size relative to the blocks at any window size / DPI)."""
    ax.clear()
    ax.set_xlim(0, 104)
    ax.set_ylim(-1, 44)
    ax.set_aspect("equal")
    ax.axis("off")
    d = _D(ax)
    ol = mode == "open_loop"
    has_de = mode == "path"
    yL, yR = 32.0, 14.0                       # left / right wheel rows

    ax.text(52, 43.2, TITLES[mode], ha="center", va="center", fontsize=11, fontweight="bold")

    # ---------------------------------------------------------- desired points
    d.box(0.5, 26, 7, 6, "Desired\nPoints", "prof", fs=7.5)
    # ---------------------------------------------------------- controller
    name = {"path": "Path_CTRL", "p2p": "P2P_CTRL", "open_loop": "P2P_CTRL\n(open loop)"}[mode]
    d.box(10, 9, 11, 27, "", "ctrl")
    ax.text(15.5, 22.5, name, ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(15.5, 18.6, "controllers.py", ha="center", va="center", fontsize=6.5, color="#555",
            family="monospace")
    d.wire([(7.5, 29), (10, 29)])
    ax.text(10.4, 13.2, "X, Y, Φ", fontsize=6.5, ha="left", va="center")

    # odometry block and outer loop (common to all modes)
    d.box(84, 9, 9, 27, "", "odo")
    ax.text(88.5, 22.5, "Encoder\nPosition\nEstimation", ha="center", va="center", fontsize=7.5)
    ax.text(88.5, 15.5, "odometry.py", ha="center", fontsize=6.5, color="#555", family="monospace")
    for yy, lab in ((31, "X"), (26, "Y"), (21, "Φ")):
        d.wire([(93, yy), (96.5, yy)], arrow=False, label=lab, loff=(0, 0.2), fs=6.5, color=C_OUTER)
    d.wire([(96.5, 31), (96.5, 21)], arrow=False, color=C_OUTER, lw=1.6)
    d.dot(96.5, 26, C_OUTER)
    d.wire([(96.5, 26), (99, 26), (99, 2.5), (55, 2.5)], arrow=False, color=C_OUTER, lw=2.2)
    d.box(50, 0.7, 5, 3.6, "z⁻¹", "gain", fs=9)
    d.wire([(50, 2.5), (6, 2.5), (6, 13), (10, 13)], color=C_OUTER, lw=2.2)
    ax.text(27, 3.0, "outer loop: position feedback (1 sample delay)", fontsize=7.5,
            color=C_OUTER, va="bottom", ha="center", fontweight="bold")
    ax.text(101.2, 26, "pose", fontsize=6.5, rotation=90, va="center", color=C_OUTER)

    # motor blocks (common)
    xm = 67
    for yy, side in ((yL, "Left"), (yR, "Right")):
        d.box(xm, yy - 3.2, 10.5, 6.4, f"DC Motor {side}", "motor", fs=7.5,
              sub="motor+gear+encoder")
        ax.text(xm + 5.25, yy - 4.4, "[En] gate" if not ol else "", fontsize=6, ha="center",
                va="top", color="#555")

    if ol:
        _draw_open_loop(d, ax, p, yL, yR, xm)
    else:
        _draw_closed(d, ax, p, yL, yR, xm, has_de)

    # legend
    ax.plot([2, 6], [40.5, 40.5], color=C_OUTER, lw=2.2)
    ax.text(6.8, 40.5, "outer loop (position)", fontsize=7.5, va="center")
    if not ol:
        ax.plot([27, 31], [40.5, 40.5], color=C_INNER, lw=2.2)
        ax.text(31.8, 40.5, "inner loops (wheel speed PI)", fontsize=7.5, va="center")
    ax.plot([57, 61], [40.5, 40.5], color=C_OFF, lw=1.2, ls="--")
    ax.text(61.8, 40.5, "not used in this mode", fontsize=7.5, va="center")
    ax.text(103, 40.5, f"Ts = {p.sample_time * 1000:.0f} ms", fontsize=7.5, va="center", ha="right")

    if font_scale is None:
        font_scale = fit_font_scale(ax)
    if font_scale != 1.0:
        for t in ax.texts:
            t.set_fontsize(t.get_fontsize() * font_scale)


def fit_font_scale(ax, ref_width_pt=930.0):
    """Font scale so the text matches the drawing scale (layout was designed for
    a drawing ~930 pt wide). Uses the drawn width (equal aspect -> limited by
    the axes width or height)."""
    fig = ax.figure
    bb = ax.get_position()
    w_in = bb.width * fig.get_figwidth()
    h_in = bb.height * fig.get_figheight()
    xr = ax.get_xlim()[1] - ax.get_xlim()[0]
    yr = ax.get_ylim()[1] - ax.get_ylim()[0]
    drawn_w_pt = min(w_in, h_in * xr / yr) * 72
    return max(0.4, min(2.0, drawn_w_pt / ref_width_pt))


def _draw_closed(d, ax, p, yL, yR, xm, has_de):
    # controller outputs
    yV, yT, yD = 31.0, 24.5, 18.0
    d.wire([(21, yV), (24, yV)], label="V_Forward", loff=(0, 0.3), fs=6)
    # velocity profile: rate limiter + saturation
    d.box(24, yV - 2, 5.5, 4, "rate\nlimit", "prof", fs=6.5)
    ax.text(26.75, yV - 2.6, f"+{p.a_max:g}\n-{p.a_max * p.decel_factor:g}", fontsize=5.8, ha="center",
            va="top", family="monospace")
    d.wire([(29.5, yV), (31, yV)])
    d.box(31, yV - 2, 5, 4, "sat", "prof", fs=6.5)
    ax.text(33.5, yV - 2.6, f"±{p.v_max:g}", fontsize=5.8, ha="center", va="top",
            family="monospace")
    ax.text(30.2, yV + 3.0, "trapezoidal profile", fontsize=6.5, ha="center", color="#2c7a2c")

    # heading / cross-track gains
    d.wire([(21, yT), (25, yT)], label="θt", loff=(-1.3, 0.2), fs=7)
    d.gain(25, yT, 5, 3.4, "Kθ", label=f"{p.k_theta:g}")
    d.wire([(21, yD), (25, yD)], label="de", loff=(-1.3, 0.2), fs=7,
           color=C_SIG if has_de else C_OFF, ls="-" if has_de else "--")
    d.gain(25, yD, 5, 3.4, "Kde", active=has_de, label=f"{p.k_de:g}" if has_de else "n/a")
    xs = 34
    d.sum(xs, 21.5, "+" + ("+" if has_de else " "), second="bottom")
    d.wire([(30, yT), (xs - 0.8, yT), (xs - 0.8, 22.3)], arrow=True)
    d.wire([(30, yD), (xs - 0.8, yD), (xs - 0.8, 20.7)], arrow=True,
           color=C_SIG if has_de else C_OFF, ls="-" if has_de else "--")
    ax.text(xs + 1.6, 19.3, "turn", fontsize=6.5)

    # left / right wheel set points: V +/- turn
    xa = 40
    d.wire([(36, yV), (xa - 1.1, yV)])
    d.sum(xa, yL, "++", second="bottom")
    d.dot(37.5, yV)
    d.wire([(37.5, yV), (37.5, yR), (xa - 1.1, yR)])
    d.sum(xa, yR, "+-")
    d.wire([(xs + 1.1, 21.5), (xa, 21.5), (xa, yL - 1.1)])
    d.dot(xa, 21.5)
    d.wire([(xa, 21.5), (xa, yR + 1.1)])
    for yy in (yL, yR):
        d.wire([(xa + 1.1, yy), (43, yy)])
        d.gain(43, yy, 4.5, 3.4, "1/2πr")
    ax.text(45, yL + 2.5, "m/s → rev/s", fontsize=6, ha="center")

    # inner loops
    xe = 52
    for yy, lab in ((yL, "wL_sp"), (yR, "wR_sp")):
        d.wire([(47.5, yy), (xe - 1.1, yy)], label=lab, loff=(0, 0.2), fs=6)
        d.sum(xe, yy, "+-", second="bottom")
        d.wire([(xe + 1.1, yy), (55, yy)])
        d.box(55, yy - 2.6, 8, 5.2, "PI", "pi", fs=8, bold=True,
              sub=f"Kp={p.kp:g} Ki={p.ki:g}")
        d.wire([(63, yy), (xm, yy)], label="PWM", loff=(0, 0.2), fs=6)
        # motor output -> odometry, with feedback branch
        d.wire([(xm + 10.5, yy), (84, yy if yy == yL else yy)], color=C_SIG,
               label="wheel speed", loff=(0, 0.2), fs=6)
        d.dot(80, yy, C_INNER)
        d.wire([(80, yy), (80, yy - 5.6), (xe, yy - 5.6), (xe, yy - 1.1)], color=C_INNER, lw=2.0)
    ax.text(65.5, yR - 7.2, "inner loops: wheel speed feedback (Hall encoder)", fontsize=7.5,
            color=C_INNER, ha="center", fontweight="bold")
    ax.text(66, 38.2, "v_L = V + (Kθ·θt" + (" + Kde·de)" if has_de else ")") +
            "     v_R = V − (Kθ·θt" + (" + Kde·de)" if has_de else ")"),
            fontsize=7.5, ha="center", family="monospace", color="#333")


def _draw_open_loop(d, ax, p, yL, yR, xm):
    for yy, lab in ((yL, "Left_Motor"), (yR, "Right_Motor")):
        d.wire([(21, yy - 1 if yy == yL else yy + 1), (54, yy - 1 if yy == yL else yy + 1),
                (54, yy), (57, yy)], label=lab, loff=(0, 0.3), fs=7)
        d.box(57, yy - 2, 5, 4, "ZOH", "gain", fs=7)
        d.wire([(62, yy), (xm, yy)], label="PWM", loff=(0, 0.2), fs=6)
        d.wire([(xm + 10.5, yy), (84, yy)], label="wheel speed", loff=(0, 0.2), fs=6)
    # unused blocks of the closed loop models, greyed
    d.box(24, 21, 9, 4.5, "rate limit / sat", "off", active=False, fs=6.5)
    d.box(36, 21, 8, 4.5, "Kθ, Kde", "off", active=False, fs=6.5)
    d.box(47, 21, 8, 4.5, "wheel PI", "off", active=False, fs=6.5)
    ax.text(39.5, 18.5, "no wheel speed feedback - PWM computed directly from the position error",
            fontsize=7, ha="center", color="#a33")
    ax.text(66, 38.2, f"Left = w_fwd + {p.ol_gain_theta:g}·θt     "
            f"Right = w_fwd − {p.ol_gain_theta:g}·θt     "
            f"w_fwd = min({p.ol_gain_forward:g}·dist, w_max)",
            fontsize=7.5, ha="center", family="monospace", color="#333")

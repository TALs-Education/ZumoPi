"""
ZumoPi Path Control Simulator - interactive GUI.

    python gui.py

Left panel : controller type, desired path, gains / parameters (sliders).
Right panel: 2D path (desired vs. simulated) and time responses.

Every change re-runs the simulation (takes ~0.1 s). Use "Pin run" to keep a
result on the plot and compare it against new gains.
"""
import csv
import math
import sys
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Polygon

from zumo_sim import ZumoParams, simulate, MODES, paths
from zumo_sim.diagram import draw_block_diagram

# (attribute, label, min, max, resolution, tooltip)
PARAM_GROUPS = [
    ("Path controller", [
        ("k_theta", "Theta gain  Kθ", 0.0, 2.0, 0.005, "Heading error gain [m/s per rad]"),
        ("k_de", "Cross-track gain  Kde", 0.0, 10.0, 0.01, "Cross-track error gain [1/s] (path mode only)"),
        ("pass_distance", "Pass distance [m]", 0.005, 0.2, 0.001, "Advance to next point when closer than this"),
        ("stop_distance", "Stop distance [m]", 0.002, 0.1, 0.001, "Stop when closer than this to the last point"),
    ]),
    ("Velocity profile (trapezoidal)", [
        ("a_max", "a_max [m/s²]", 0.01, 1.0, 0.005, "Max acceleration (rate limiter + sqrt(2*a*d))"),
        ("v_max", "v_max [m/s]", 0.02, 0.6, 0.005, "Max forward velocity"),
        ("decel_factor", "Decel factor", 0.5, 4.0, 0.1, "Deceleration limit = factor * a_max"),
    ]),
    ("Wheel speed PI", [
        ("kp", "Kp", 0.0, 1.0, 0.005, "Proportional gain [duty per rev/s]"),
        ("ki", "Ki (per sample)", 0.0, 0.2, 0.001, "Integral gain, accumulated each 10 ms sample"),
    ]),
    ("Robot / simulation", [
        ("motor_mismatch", "Right motor weaker [-]", -0.3, 0.3, 0.01, "Model a mismatch between the motors (0 = ideal)"),
        ("sim_time", "Max sim time [s]", 5, 120, 1, "Maximum simulated time"),
    ]),
]

MODE_DEFAULTS = {          # values that differ between the original models
    "path": dict(decel_factor=1.0),
    "p2p": dict(decel_factor=2.0),
    "open_loop": dict(decel_factor=2.0),
}

# parameters that have no effect in a mode -> disabled in the GUI
MODE_UNUSED = {
    "path": set(),
    "p2p": {"k_de"},                       # P2P has no cross-track error
    "open_loop": {"k_theta", "k_de", "pass_distance", "a_max", "v_max", "decel_factor",
                  "kp", "ki"},             # fixed internal gains, no velocity profile, no PI
}

PIN_COLORS = ["#7f7f7f", "#bcbd22", "#17becf", "#9467bd", "#8c564b", "#e377c2"]


class ParamRow:
    def __init__(self, parent, row, attr, label, lo, hi, res, tip, on_change):
        self.attr, self.lo, self.hi, self.res = attr, lo, hi, res
        self.on_change = on_change
        self.var = tk.DoubleVar()
        self.txt = tk.StringVar()
        lab = ttk.Label(parent, text=label)
        lab.grid(row=row, column=0, sticky="w", padx=(4, 2))
        self.lab = lab
        self.scale = ttk.Scale(parent, from_=lo, to=hi, variable=self.var,
                               command=self._scale_moved, length=150)
        self.scale.grid(row=row, column=1, sticky="ew", padx=2)
        ent = ttk.Entry(parent, textvariable=self.txt, width=7)
        self.ent = ent
        ent.grid(row=row, column=2, sticky="e", padx=(2, 4))
        ent.bind("<Return>", self._entry_set)
        ent.bind("<FocusOut>", self._entry_set)
        self.scale.bind("<ButtonRelease-1>", lambda e: self.on_change(final=True))
        Tooltip(lab, tip)

    def set_enabled(self, enabled: bool):
        state = ["!disabled"] if enabled else ["disabled"]
        for w in (self.lab, self.scale, self.ent):
            w.state(state)

    def _fmt(self, v):
        digits = max(0, -int(math.floor(math.log10(self.res)))) if self.res < 1 else 0
        return f"{v:.{digits}f}"

    def _scale_moved(self, _=None):
        v = round(self.var.get() / self.res) * self.res
        self.txt.set(self._fmt(v))
        self.on_change(final=False)

    def _entry_set(self, _=None):
        try:
            v = float(self.txt.get())
        except ValueError:
            v = self.get()
        self.set(v)               # entries may go beyond the slider range
        self.on_change(final=True)

    def get(self):
        try:
            return float(self.txt.get())
        except ValueError:
            return round(self.var.get() / self.res) * self.res

    def set(self, v):
        self.var.set(min(self.hi, max(self.lo, v)))
        self.txt.set(self._fmt(v))


class Tooltip:
    def __init__(self, widget, text):
        self.w, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _):
        x = self.w.winfo_rootx() + 20
        y = self.w.winfo_rooty() + 20
        self.tip = tk.Toplevel(self.w)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, background="#ffffe0", relief="solid",
                 borderwidth=1, font=("Segoe UI", 9)).pack()

    def hide(self, _):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class App:
    def __init__(self, root):
        self.root = root
        root.title("ZumoPi Path Control Simulator")
        self.result = None
        self.pinned = []          # list of (label, SimResult)
        self.draw_mode = tk.BooleanVar(value=False)
        self.live = tk.BooleanVar(value=True)
        self.show_points = tk.BooleanVar(value=True)
        self.anim_speed = tk.DoubleVar(value=5)     # animation speed factor (x real time)
        self._pending = None
        self._anim = None
        self.points = paths.line()

        self._build_controls()
        self._build_plots()
        self.reset_defaults(run=False)
        self.preset_var.set("Line 2 m (plotScript)")
        self._set_points(paths.line())
        self.run()

    # ------------------------------------------------------------------ UI
    def _build_controls(self):
        # scrollable left panel (works with Windows display scaling)
        holder = ttk.Frame(self.root)
        holder.pack(side="left", fill="y")
        # fixed title (does not scroll)
        tk.Label(holder, text="ZumoPi Simulator", font=("Segoe UI", 15, "bold"),
                 fg="#1f4e8c", anchor="w", padx=8, pady=4).pack(side="top", fill="x")
        ttk.Separator(holder, orient="horizontal").pack(side="top", fill="x", padx=4)
        body = ttk.Frame(holder)
        body.pack(side="top", fill="both", expand=True)
        cv = tk.Canvas(body, highlightthickness=0, width=10)
        sb = ttk.Scrollbar(body, orient="vertical", command=cv.yview)
        outer = ttk.Frame(cv, padding=4)
        cv.create_window((0, 0), window=outer, anchor="nw")
        cv.configure(yscrollcommand=sb.set, yscrollincrement=20)
        cv.pack(side="left", fill="y", expand=True)
        sb.pack(side="right", fill="y")

        def _update_region(_=None):
            # scroll region never smaller than the visible area -> no scrolling
            # into empty space when everything fits
            h = max(outer.winfo_reqheight(), cv.winfo_height())
            cv.configure(scrollregion=(0, 0, outer.winfo_reqwidth(), h),
                         width=outer.winfo_reqwidth())
            if outer.winfo_reqheight() <= cv.winfo_height():
                cv.yview_moveto(0)
        outer.bind("<Configure>", _update_region)
        cv.bind("<Configure>", _update_region)

        def _wheel(ev):
            if not str(ev.widget).startswith(str(holder)) or isinstance(ev.widget, tk.Text):
                return
            if outer.winfo_reqheight() > cv.winfo_height():   # only when content overflows
                cv.yview_scroll(int(-ev.delta / 120), "units")
        self.root.bind_all("<MouseWheel>", _wheel, add="+")

        # --- controller
        f = ttk.LabelFrame(outer, text="Controller", padding=4)
        f.pack(fill="x", pady=2)
        self.mode_var = tk.StringVar(value=MODES["path"])
        cb = ttk.Combobox(f, textvariable=self.mode_var, values=list(MODES.values()),
                          state="readonly", width=38)
        cb.pack(fill="x")
        cb.bind("<<ComboboxSelected>>", self._mode_changed)

        # --- path
        f = ttk.LabelFrame(outer, text="Desired path  (x y; x y; ...  in meters)", padding=4)
        f.pack(fill="x", pady=2)
        self.preset_var = tk.StringVar()
        cb = ttk.Combobox(f, textvariable=self.preset_var, values=list(paths.PRESETS),
                          state="readonly", width=38)
        cb.pack(fill="x")
        cb.bind("<<ComboboxSelected>>", self._preset_changed)
        self.pts_text = tk.Text(f, height=5, width=40, font=("Consolas", 9))
        self.pts_text.pack(fill="x", pady=2)
        bf = ttk.Frame(f)
        bf.pack(fill="x")
        ttk.Button(bf, text="Apply points", command=self._apply_points).pack(side="left")
        ttk.Checkbutton(bf, text="Draw on plot", variable=self.draw_mode,
                        command=self._draw_toggled).pack(side="left", padx=4)
        ttk.Button(bf, text="Clear", command=self._clear_points).pack(side="left")
        ttk.Button(bf, text="Load...", command=self._load_points).pack(side="left", padx=2)

        # --- parameters
        self.rows = {}
        for title, items in PARAM_GROUPS:
            f = ttk.LabelFrame(outer, text=title, padding=2)
            f.pack(fill="x", pady=2)
            f.columnconfigure(1, weight=1)
            for i, (attr, label, lo, hi, res, tip) in enumerate(items):
                self.rows[attr] = ParamRow(f, i, attr, label, lo, hi, res, tip, self._param_changed)

        # --- actions
        f = ttk.Frame(outer, padding=(0, 4))
        f.pack(fill="x")
        ttk.Button(f, text="Run", command=self.run).grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        ttk.Button(f, text="Animate", command=self.animate).grid(row=0, column=1, sticky="ew", padx=1, pady=1)
        ttk.Button(f, text="Pin run", command=self.pin).grid(row=0, column=2, sticky="ew", padx=1, pady=1)
        ttk.Button(f, text="Clear pins", command=self.clear_pins).grid(row=1, column=0, sticky="ew", padx=1, pady=1)
        ttk.Button(f, text="Defaults", command=self.reset_defaults).grid(row=1, column=1, sticky="ew", padx=1, pady=1)
        ttk.Button(f, text="Export CSV", command=self.export_csv).grid(row=1, column=2, sticky="ew", padx=1, pady=1)
        for c in range(3):
            f.columnconfigure(c, weight=1)
        f2 = ttk.Frame(outer)
        f2.pack(fill="x")
        ttk.Checkbutton(f2, text="Live update", variable=self.live).pack(side="left")
        ttk.Checkbutton(f2, text="Show way-points", variable=self.show_points,
                        command=self.redraw).pack(side="left", padx=6)

        # --- animation speed (x1 .. x20 real time)
        f3 = ttk.Frame(outer)
        f3.pack(fill="x", pady=(4, 0))
        lab = ttk.Label(f3, text="Animation speed")
        lab.pack(side="left", padx=(4, 4))
        Tooltip(lab, "Replay speed relative to real time (can be changed while animating)")
        self.speed_txt = tk.StringVar()
        ttk.Label(f3, textvariable=self.speed_txt, width=4).pack(side="right", padx=(2, 4))
        ttk.Scale(f3, from_=1, to=20, variable=self.anim_speed,
                  command=self._speed_moved).pack(side="left", fill="x", expand=True)
        self._speed_moved()

        # --- metrics
        f = ttk.LabelFrame(outer, text="Result", padding=4)
        f.pack(fill="both", expand=True, pady=2)
        self.metrics_var = tk.StringVar()
        ttk.Label(f, textvariable=self.metrics_var, font=("Consolas", 9),
                  justify="left").pack(anchor="nw")

    def _build_plots(self):
        nb = ttk.Notebook(self.root)
        nb.pack(side="right", fill="both", expand=True)
        right = ttk.Frame(nb)
        diag = ttk.Frame(nb)
        nb.add(right, text="  Responses  ")
        nb.add(diag, text="  Block diagram  ")
        self.notebook = nb
        self.fig = Figure(figsize=(11, 7.5), dpi=100)
        gs = self.fig.add_gridspec(4, 2, width_ratios=[1.15, 1], hspace=0.7, wspace=0.28,
                                   left=0.08, right=0.95, top=0.95, bottom=0.08)
        self.ax_xy = self.fig.add_subplot(gs[:, 0])
        self.ax_h = self.fig.add_subplot(gs[0, 1])
        self.ax_e = self.fig.add_subplot(gs[1, 1], sharex=self.ax_h)
        self.ax_v = self.fig.add_subplot(gs[2, 1], sharex=self.ax_h)
        self.ax_u = self.fig.add_subplot(gs[3, 1], sharex=self.ax_h)
        self.ax_d = self.ax_e.twinx()
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        NavigationToolbar2Tk(self.canvas, right).update()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.canvas.mpl_connect("button_press_event", self._on_click)

        # block diagram tab
        self.fig_d = Figure(figsize=(11, 5), dpi=100)
        self.fig_d.subplots_adjust(left=0.005, right=0.995, top=0.99, bottom=0.01)
        self.ax_diag = self.fig_d.add_subplot(111)
        self.canvas_d = FigureCanvasTkAgg(self.fig_d, master=diag)
        NavigationToolbar2Tk(self.canvas_d, diag).update()
        help_lab = ttk.Label(diag, justify="left", font=("Segoe UI", 9), padding=6, text=(
            "Blue: outer loop - the pose estimated by odometry is fed back (one sample later) to the "
            "path / P2P controller.   Orange: inner loops - each wheel speed is measured by the Hall "
            "encoder and regulated by its PI controller.\n"
            "Grey dashed blocks exist in the Simulink "
            "models but are not used by the selected controller. Values shown are the current GUI "
            "settings."))
        help_lab.pack(side="bottom", fill="x")
        help_lab.bind("<Configure>", lambda e: help_lab.configure(wraplength=max(200, e.width - 12)))
        self.canvas_d.get_tk_widget().pack(fill="both", expand=True)
        self.canvas_d.mpl_connect("resize_event", lambda e: self.update_diagram())

    def update_diagram(self):
        draw_block_diagram(self.ax_diag, self.mode(), self.params())
        self.canvas_d.draw_idle()

    def _apply_mode_state(self):
        unused = MODE_UNUSED[self.mode()]
        for attr, row in self.rows.items():
            row.set_enabled(attr not in unused)

    # ------------------------------------------------------------ helpers
    def mode(self):
        inv = {v: k for k, v in MODES.items()}
        return inv[self.mode_var.get()]

    def params(self):
        p = ZumoParams()
        for attr, row in self.rows.items():
            setattr(p, attr, row.get())
        return p

    def _set_points(self, pts):
        self.points = np.asarray(pts, dtype=float).reshape(-1, 2)
        self.pts_text.delete("1.0", "end")
        self.pts_text.insert("1.0", paths.format_points(self.points))

    def _apply_points(self):
        try:
            self._set_points(paths.parse_points(self.pts_text.get("1.0", "end")))
        except ValueError as e:
            messagebox.showerror("Path", str(e))
            return
        self.run()

    def _clear_points(self):
        self.points = np.zeros((0, 2))
        self.pts_text.delete("1.0", "end")
        self.draw_mode.set(True)
        self.result = None
        self.redraw()

    def _load_points(self):
        fn = filedialog.askopenfilename(filetypes=[("Text / CSV", "*.txt *.csv"), ("All", "*.*")])
        if not fn:
            return
        try:
            data = np.loadtxt(fn, delimiter="," if fn.endswith(".csv") else None)
            self._set_points(data)
        except Exception as e:        # noqa: BLE001
            messagebox.showerror("Load", str(e))
            return
        self.run()

    def _draw_toggled(self):
        if self.draw_mode.get():
            self.metrics_var.set("Draw mode:\n left click  = add point\n right click = remove last\n"
                                 "Uncheck 'Draw on plot'\nwhen done.")
        else:
            self.run()

    def _on_click(self, ev):
        if not self.draw_mode.get() or ev.inaxes is not self.ax_xy or ev.xdata is None:
            return
        if ev.button == 1:
            pt = np.round([ev.xdata, ev.ydata], 3)
            self.points = np.vstack([self.points, pt]) if len(self.points) else pt[None, :]
        elif ev.button == 3 and len(self.points):
            self.points = self.points[:-1]
        self._set_points(self.points)
        self.redraw(keep_limits=True)

    def _mode_changed(self, _=None):
        for k, v in MODE_DEFAULTS[self.mode()].items():
            self.rows[k].set(v)
        self._apply_mode_state()
        self.run()

    def _preset_changed(self, _=None):
        self._set_points(paths.PRESETS[self.preset_var.get()]())
        if self.preset_var.get().startswith("Single") and self.mode() == "path":
            self.mode_var.set(MODES["p2p"])
            self._mode_changed()
            return
        self.run()

    def _param_changed(self, final):
        if not self.live.get():
            return
        if self._pending:
            self.root.after_cancel(self._pending)
        self._pending = self.root.after(30 if final else 120, self.run)

    def reset_defaults(self, run=True):
        p = ZumoParams()
        for attr, row in self.rows.items():
            row.set(getattr(p, attr))
        for k, v in MODE_DEFAULTS[self.mode()].items():
            self.rows[k].set(v)
        if run:
            self.run()

    # ------------------------------------------------------------- actions
    def run(self):
        self._pending = None
        self._stop_anim()
        self._apply_mode_state()
        self.update_diagram()
        if self.draw_mode.get():
            return
        if len(self.points) == 0:
            self.result = None
            self.redraw()
            return
        try:
            self.result = simulate(self.points, self.mode(), self.params())
        except Exception as e:        # noqa: BLE001
            self.result = None
            self.metrics_var.set(f"Simulation error:\n{e}")
            self.redraw()
            return
        self._update_metrics()
        self.redraw()

    def _update_metrics(self):
        r = self.result
        m = r.metrics()
        ft = f"{m['finish_time']:.2f} s" if m["finish_time"] is not None else "NOT REACHED"
        p = r.params
        txt = (f"Finish time      : {ft}\n"
               f"Final pos. error : {m['final_error_mm']:.1f} mm\n"
               f"Max path dev.    : {m['max_path_dev_mm']:.1f} mm\n"
               f"RMS path dev.    : {m['rms_path_dev_mm']:.1f} mm\n"
               f"Distance driven  : {m['path_length_m']:.2f} m\n"
               f"Way-points       : {len(r.points)}")
        if m["finish_time"] is None:
            txt += ("\n\n! The robot did not stop - it\n  probably missed a way-point.\n"
                    "  Try other gains / pass distance.")
        self.metrics_var.set(txt)

    def pin(self):
        if self.result is None:
            return
        p = self.result.params
        lab = f"{self.mode()}  Kθ={p.k_theta:g} Kde={p.k_de:g} Kp={p.kp:g} Ki={p.ki:g}"
        self.pinned.append((lab, self.result))
        self.redraw()

    def clear_pins(self):
        self.pinned = []
        self.redraw()

    def export_csv(self):
        r = self.result
        if r is None:
            return
        fn = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not fn:
            return
        cols = ["t", "x", "y", "phi", "v_request", "v_cmd", "theta_t", "de", "dist", "en",
                "wl_sp", "wr_sp", "wl", "wr", "ul", "ur", "target_idx"]
        with open(fn, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(cols)
            for i in range(len(r.t)):
                w.writerow([f"{getattr(r, c)[i]:.6g}" for c in cols])

    # ------------------------------------------------------------- plotting
    def redraw(self, keep_limits=False):
        ax = self.ax_xy
        lims = (ax.get_xlim(), ax.get_ylim()) if keep_limits else None
        for a in (self.ax_xy, self.ax_h, self.ax_e, self.ax_v, self.ax_u, self.ax_d):
            a.clear()

        # pinned runs
        for i, (lab, r) in enumerate(self.pinned):
            c = PIN_COLORS[i % len(PIN_COLORS)]
            ax.plot(r.x, r.y, color=c, lw=1.2, alpha=0.8, label=lab)
            self.ax_h.plot(r.t, np.degrees(r.phi), color=c, lw=0.9, alpha=0.7)
            self.ax_e.plot(r.t, r.de * 1000, color=c, lw=0.9, alpha=0.7)
            self.ax_v.plot(r.t, r.v_cmd, color=c, lw=0.9, alpha=0.7)

        # desired path
        P = self.points
        start = np.array([[0.0, 0.0]])
        if len(P):
            full = np.vstack([start, P])
            ax.plot(full[:, 0], full[:, 1], ":", color="k", lw=1, alpha=0.6, label="desired path")
            if self.show_points.get():
                ax.plot(P[:, 0], P[:, 1], "*", color="#e6a100", ms=8, label="way-points")
        ax.plot(0, 0, "ko", ms=4)

        r = self.result
        if r is not None:
            ax.plot(r.x, r.y, color="#d62728", lw=2, label=f"simulated ({self.mode()})")
            self._draw_robot(r.x[-1], r.y[-1], r.phi[-1])
            t = r.t
            h = self.ax_h
            h.plot(t, np.degrees(r.phi), label="Φ heading", color="#1f77b4")
            h.plot(t, np.degrees(r.theta_t), label="θt error", color="#ff7f0e")
            h.set_ylabel("[deg]"); h.set_title("Heading and heading error", fontsize=9)
            e = self.ax_e
            if self.mode() == "path":
                e.plot(t, r.de * 1000, label="de cross-track", color="#2ca02c")
                e.set_ylabel("de [mm]")
            e2 = self.ax_d
            e2.yaxis.tick_right()
            e2.yaxis.set_label_position("right")
            e2.plot(t, r.dist, color="#9467bd", lw=1, label="remaining dist")
            e2.set_ylabel("dist [m]", color="#9467bd", fontsize=8)
            e2.tick_params(axis="y", labelsize=7, colors="#9467bd")
            e.set_title("Cross-track error / remaining distance", fontsize=9)
            v = self.ax_v
            if self.mode() != "open_loop":
                v.plot(t, r.v_request.clip(max=r.params.v_max * 1.6), ":", color="gray", lw=1, label="V request")
                v.plot(t, r.v_cmd, label="V cmd", color="k")
            k = 2 * math.pi * r.params.wheel_radius
            v.plot(t, r.wl * k, label="left", color="#1f77b4", lw=0.9)
            v.plot(t, r.wr * k, label="right", color="#d62728", lw=0.9)
            v.set_ylabel("[m/s]"); v.set_title("Forward velocity and wheel speeds", fontsize=9)
            u = self.ax_u
            u.plot(t, r.ul, label="left", color="#1f77b4", lw=0.9)
            u.plot(t, r.ur, label="right", color="#d62728", lw=0.9)
            u.set_ylabel("duty"); u.set_xlabel("time [s]")
            u.set_title("Motor PWM command (PI output)", fontsize=9)
            for a in (h, v, u):
                a.legend(fontsize=7, loc="upper right", ncol=2)
            if self.mode() == "path":
                e.legend(fontsize=7, loc="upper left")

        for a in (self.ax_h, self.ax_e, self.ax_v, self.ax_u):
            a.grid(True, alpha=0.4)
            a.tick_params(labelsize=8)
        ax.set_title("Path Control - X/Y position", fontsize=11)
        ax.set_xlabel("X [m]"); ax.set_ylabel("Y [m]")
        ax.grid(True, alpha=0.4)
        ax.set_aspect("equal", adjustable="datalim")
        ax.legend(fontsize=7, loc="upper left", framealpha=0.85)
        if lims:
            ax.set_xlim(lims[0]); ax.set_ylim(lims[1])
        elif r is not None:
            self._autoscale_xy(r)
        self.canvas.draw_idle()

    def _autoscale_xy(self, r):
        """Keep the view on the desired path even if the robot runs away."""
        P = np.vstack([[0, 0], self.points])
        lo, hi = P.min(axis=0), P.max(axis=0)
        span = max(hi - lo)
        pad = max(0.1, 0.25 * span)
        traj = np.column_stack([r.x, r.y])
        tlo, thi = traj.min(axis=0), traj.max(axis=0)
        lo = np.maximum(np.minimum(lo, tlo), lo - 1.5 * span - pad)
        hi = np.minimum(np.maximum(hi, thi), hi + 1.5 * span + pad)
        self.ax_xy.set_xlim(lo[0] - pad / 2, hi[0] + pad / 2)
        self.ax_xy.set_ylim(lo[1] - pad / 2, hi[1] + pad / 2)

    def _robot_shape(self, x, y, phi):
        L = 0.098
        body = np.array([[0.06, 0], [0.02, L / 2], [-0.05, L / 2], [-0.05, -L / 2], [0.02, -L / 2]])
        c, s = math.cos(phi), math.sin(phi)
        R = np.array([[c, -s], [s, c]])
        return body @ R.T + [x, y]

    def _draw_robot(self, x, y, phi):
        self._robot = Polygon(self._robot_shape(x, y, phi), closed=True, fc="#d62728",
                              ec="k", alpha=0.35, zorder=5)
        self.ax_xy.add_patch(self._robot)

    # ------------------------------------------------------------- animation
    def animate(self):
        r = self.result
        if r is None:
            return
        self._stop_anim()
        self.redraw()
        trail, = self.ax_xy.plot([], [], color="#1f77b4", lw=2.5, alpha=0.6, zorder=4)
        tgt, = self.ax_xy.plot([], [], "o", ms=12, mfc="none", mec="#1f77b4", mew=2, zorder=6)
        cursors = [a.axvline(0, color="k", lw=0.8, alpha=0.6) for a in
                   (self.ax_h, self.ax_e, self.ax_v, self.ax_u)]
        clock = self.ax_xy.text(0.98, 0.02, "", transform=self.ax_xy.transAxes, ha="right",
                                va="bottom", fontsize=9, family="monospace",
                                bbox=dict(fc="white", ec="0.7", alpha=0.85))
        n = len(r.t)
        dt = r.params.sample_time
        # simulated time advances with the wall clock times the speed factor
        state = {"t_sim": 0.0, "wall": time.perf_counter()}

        def tick():
            now = time.perf_counter()
            speed = self.anim_speed_value()
            state["t_sim"] += (now - state["wall"]) * speed
            state["wall"] = now
            i = min(int(state["t_sim"] / dt), n - 1)
            clock.set_text(f"t = {r.t[i]:5.2f} s   x{speed}")
            self._robot.set_xy(self._robot_shape(r.x[i], r.y[i], r.phi[i]))
            trail.set_data(r.x[:i + 1], r.y[:i + 1])
            ti = int(r.target_idx[i])
            if r.mode != "open_loop" and ti < len(r.points):
                tgt.set_data([r.points[ti, 0]], [r.points[ti, 1]])
            for c in cursors:
                c.set_xdata([r.t[i], r.t[i]])
            self.canvas.draw_idle()
            if i < n - 1:
                self._anim = self.root.after(30, tick)
            else:
                self._anim = None

        tick()

    def anim_speed_value(self) -> int:
        return int(round(self.anim_speed.get()))

    def _speed_moved(self, _=None):
        self.speed_txt.set(f"x{self.anim_speed_value()}")

    def _stop_anim(self):
        if self._anim:
            self.root.after_cancel(self._anim)
            self._anim = None


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:             # noqa: BLE001
            pass
    root = tk.Tk()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{int(sw * 0.92)}x{int(sh * 0.85)}+20+20")
    try:
        root.state("zoomed")          # maximised on Windows
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

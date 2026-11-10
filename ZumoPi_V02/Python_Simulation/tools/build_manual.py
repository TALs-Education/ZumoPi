"""
Build the Python edition of the student manual from the original Word file.

Copies "ZumoPiV02 - Autonomous Systems Lab - Path Control.docx" and replaces the
MATLAB pre-lab instructions with Python ones, reusing the document's own
paragraph / list / table formatting.

Requires python-docx (not needed for the simulation itself):
    pip install python-docx
    python tools/build_manual.py                  # default paths: ../EducationalMaterials
    python tools/build_manual.py <original.docx> <output.docx>
"""
import copy
import os
import sys

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches
from docx.text.paragraph import Paragraph

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "docs")

MAT = os.path.join(ROOT, "..", "EducationalMaterials")      # ZumoPi_V02/EducationalMaterials
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    MAT, "ZumoPiV02 - Autonomous Systems Lab - Path Control.docx")
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    MAT, "ZumoPiV02 - Autonomous Systems Lab - Path Control (Python).docx")

doc = docx.Document(SRC)
B = list(doc.element.body.iterchildren())


def find(text, start=0, style=None):
    for i in range(start, len(B)):
        el = B[i]
        if el.tag == qn("w:p"):
            p = Paragraph(el, doc._body)
            if p.text.strip().startswith(text) and (style is None or p.style.name == style):
                return i
    raise KeyError(text)


# ---------------------------------------------------------------- templates
i_pre = find("7. Pre-Lab Activity", style="Heading 1")
i_in = find("8. In-Lab Activity", style="Heading 1")
T = {
    "h3": B[find("Overview & Objectives", i_pre)],
    "p": B[find("Before proceeding", i_pre)],
    "bullet": B[find("Familiarize yourself", i_pre)],   # numbered list (objectives)
    "dot": B[find("Motor PID Gains", i_pre)],          # round bullets
    "step": B[find("Setup", i_pre)],                 # numbered, level 0 (bold)
    "sub": B[find("Open MATLAB/Simulink", i_pre)],   # level 1
    "img": B[find("ZumoSimulation_P2P", i_pre) + 1],
    "roadmap": B[find("The simulations listed below", i_pre) + 1],
    "code": B[find("6.1 Example", 0) + 1],
}
# original paragraphs that are kept as they are (they contain equations / images)
KEEP = {
    "params": [B[i] for i in range(find("Motor PID Gains", i_pre), find("Note: Changing", i_pre) + 1)],
    "pid_adjust": B[find("Adjust the motor PID gains", i_pre)],
    "record_obs": B[find("Record your observations", i_pre)],
    "transitions": B[find("Observe how the robot transitions", i_pre)],
    "attention": B[find("Pay special attention", i_pre)],
    "gradually": B[find("Gradually increase", i_pre)],
    "plot_final": B[find("Plot the final path", i_pre)],
    "adjust_gains": B[find("Adjust the algorithm's gains", i_pre)],
    "define_path": B[find("Define a path of your choosing", i_pre)],
    "example": B[find("Example:", i_pre)],
    "example_img": B[find("Example:", i_pre) + 1],
    "deliverables": B[find("5. Deliverables", i_pre):i_in],
}
KEEP = {k: [copy.deepcopy(e) for e in v] if isinstance(v, list) else copy.deepcopy(v)
        for k, v in KEEP.items()}


# ---------------------------------------------------------------- builders
def _run(text, bold=False, code=False, italic=False):
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    if code:
        f = OxmlElement("w:rFonts")
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            f.set(qn(a), "Roboto Mono")
        rpr.append(f)
    if bold:
        rpr.append(OxmlElement("w:b"))
    if italic:
        rpr.append(OxmlElement("w:i"))
    r.append(rpr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    return r


def para(tpl, *segs):
    """Clone template paragraph `tpl` and fill it with segments.
    A segment is a str, or a tuple (text, 'b'|'c'|'i') for bold / code / italic."""
    el = copy.deepcopy(T[tpl])
    for ch in list(el):
        if ch.tag != qn("w:pPr"):
            el.remove(ch)
    for s in segs:
        if isinstance(s, tuple):
            el.append(_run(s[0], bold="b" in s[1], code="c" in s[1], italic="i" in s[1]))
        else:
            el.append(_run(s))
    return el


def image(*files, width=6.3):
    el = para("img")
    p = Paragraph(el, doc._body)
    for f in files:
        p.add_run().add_picture(os.path.join(IMG, f), width=Inches(width))
        if len(files) > 1:
            p.add_run(" ")
    return el


def code(text):
    tbl = copy.deepcopy(T["code"])
    tc = tbl.find(".//" + qn("w:tc"))
    ps = tc.findall(qn("w:p"))
    tpl = ps[0]
    for p in ps:
        tc.remove(p)
    for line in text.strip("\n").split("\n"):
        p = copy.deepcopy(tpl)
        for ch in list(p):
            if ch.tag != qn("w:pPr"):
                p.remove(ch)
        r = OxmlElement("w:r")
        rpr = OxmlElement("w:rPr")
        f = OxmlElement("w:rFonts")
        for a in ("w:ascii", "w:hAnsi", "w:cs"):
            f.set(qn(a), "Consolas")
        rpr.append(f)
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), "18")
        rpr.append(sz)
        r.append(rpr)
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = line
        r.append(t)
        p.append(r)
        tc.append(p)
    return tbl


def roadmap(rows):
    tbl = copy.deepcopy(T["roadmap"])
    trs = tbl.findall(qn("w:tr"))
    body_tpl = trs[1]
    for tr in trs[1:]:
        tbl.remove(tr)
    for row in rows:
        tr = copy.deepcopy(body_tpl)
        for tc, cell in zip(tr.findall(qn("w:tc")), row):
            ps = tc.findall(qn("w:p"))
            for p in ps[1:]:
                tc.remove(p)
            p = ps[0]
            for ch in list(p):
                if ch.tag != qn("w:pPr"):
                    p.remove(ch)
            for s in (cell if isinstance(cell, list) else [cell]):
                if isinstance(s, tuple):
                    p.append(_run(s[0], bold="b" in s[1], code="c" in s[1]))
                else:
                    p.append(_run(s))
        tbl.append(tr)
    return tbl


def insert_after(anchor, elements):
    for e in elements:
        anchor.addnext(e)
        anchor = e
    return anchor


def set_text(el, text):
    """Replace the text of a simple paragraph, keeping the first run's format."""
    p = Paragraph(el, doc._body)
    runs = p.runs
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


# ================================================================ edits
# --- title
set_text(B[find("Path Control", 0, style="Title")], "Path Control - Python Simulation")

# --- roadmap sentence in section 1.1
set_text(B[find("Section 7 outlines", 0)],
         "Section 7 outlines the lab simulation instructions (Python simulator) and recommended "
         "parameter-tuning steps.")

# --- section 6.2: the PI controller as implemented in the simulation
tip = B[find("Tip: In real applications", 0)]
insert_after(tip, [
    para("h3", "6.2 PI Wheel-Speed Controller Used in the Simulation (Python)"),
    para("p", "Each wheel has its own PI speed controller (zumo_sim/motor.py). The output is the "
              "motor PWM duty, limited to [-1, 1], with clamping anti-windup: the integral is frozen "
              "while the output is saturated."),
    code('''
class PIController:
    def __init__(self, kp, ki, limit=1.0):
        self.kp, self.ki, self.limit = kp, ki, limit
        self.integ = 0.0

    def update(self, error):
        pre = self.kp * error + self.integ             # PI output before saturation
        out = min(self.limit, max(-self.limit, pre))   # PWM duty limited to [-1, 1]
        saturated = pre != out
        if not (saturated and (pre > 0) == (error > 0)):
            self.integ += self.ki * error              # running sum, once per 10 ms sample
        return out
'''),
    para("p", ("Note: ", "b"), "the integral is a running sum of Ki·e, evaluated once per 10 ms sample. "
         "The sample time is not multiplied in. This is how the Simulink PID blocks (accumulation mode) and the "
         "robot firmware implement it, so Ki = 0.01 per sample is equivalent to a continuous-time "
         "Ki of 0.01 / 0.01 s = 1.0 s⁻¹."),
])

# --- section 7: replace everything between the two Heading 1 titles
for el in B[i_pre + 1:i_in]:
    el.getparent().remove(el)

S = []   # new content, in order
S += [
    para("h3", "Overview & Objectives"),
    para("p", "Before the hardware lab session, you will explore a Python simulation of the two-wheel "
              "robot's motion and control. The simulator is a direct port of the four MATLAB/Simulink models "
              "(Simplified_OpenLoop, ZumoSimulatiom_P2P, ZumoSimulatiom_P2P_MultiPoint and "
              "ZumoSimulatiom_Path_Control), and its results agree with them to within a few millimetres. "
              "You can use either environment. MATLAB is not required. The goals of this pre-lab are:"),
    para("bullet", ("Familiarize yourself with the simulation environment ", "b"),
         "(the interactive GUI, the zumo_sim Python package, and the example scripts)."),
    para("bullet", ("Observe how changes to key control parameters ", "b"),
         "(e.g., PID gains, trapezoidal velocity limits, path-control gains) affect robot behavior."),
    para("bullet", ("Compare different path control strategies ", "b"),
         "(point-to-point vs. path-following) to understand their strengths and limitations."),
    para("bullet", ("Gain insight ", "b"), "into how simulation responses differ from real-world performance, "
         "laying the groundwork for your in-lab experiments."),

    para("h3", "1. Setting Up the Python Environment"),
    para("p", "The simulator is in the project GitHub folder ZumoPi_V02/Python_Simulation. It needs ",
         ("Python 3.10 or newer", "b"), " and the packages numpy, matplotlib and scipy. The GUI uses tkinter, "
         "which comes with the standard Python installer. The folder's README.md has detailed instructions "
         "for Windows, macOS and Linux."),
    para("dot", ("Install Python ", "b"), "from python.org. On Windows, tick ",
         ("Add python.exe to PATH", "b"), " during installation."),
    para("dot", ("Create a virtual environment ", "b"),
         "(a private copy of Python for this project). Install the packages and start the GUI. Run these "
         "commands in a terminal opened in the Python_Simulation folder:"),
    code('''
python -m venv .venv                  # create the virtual environment (once)
.venv\\Scripts\\activate                # activate - Windows
source .venv/bin/activate             # activate - macOS / Linux
pip install -r requirements.txt       # numpy, scipy, matplotlib (once)
python gui.py                         # start the simulator
'''),
    para("dot", ("Check the installation (optional): ", "b"),
         ("python tools/validate_against_matlab.py", "c"),
         " compares the Python simulation with results exported from the MATLAB models and prints the "
         "differences in mm."),
    para("dot", ("Recommended editor: ", "b"), "VS Code with the Python extension. Use ",
         ("Python: Select Interpreter", "b"), " and choose .venv."),

    para("h3", "2. Simulation Roadmap"),
    para("p", "All four MATLAB simulations are available in the Python simulator. Select them with the ",
         ("Controller", "b"), " drop-down in the GUI, or with the mode argument of simulate():"),
    roadmap([
        [[("Simplified open loop", "b"), " (Simplified_OpenLoop)"],
         "Robot motion where the motor commands come directly from the position error. There is no wheel-speed PI.",
         "Notice the limitations of control without wheel-speed feedback."],
        [[("Point to point – single point", "b"), " (ZumoSimulatiom_P2P)"],
         "Point-to-Point (P2P) control to a single target, with PI motor speed control.",
         "See how the PI loop and the θ gain affect reaching a single target (overshoot, settling time)."],
        [[("Point to point – multi way-point", "b"), " (ZumoSimulatiom_P2P_MultiPoint)"],
         "Extends P2P to multiple sequential waypoints.",
         "Observe transitions between waypoints and the overall path error."],
        [[("Path control", "b"), " (ZumoSimulatiom_Path_Control)"],
         "Full path following, using heading and cross-track errors relative to the path segment.",
         "Compare performance to P2P. Tune the path-control gains."],
    ]),
    para("p", "Each Simulink block has a Python counterpart. Open these files to see how the "
              "algorithms are implemented:"),
    para("dot", ("zumo_sim/controllers.py", "c"), " – the Path Control and Point to Point MATLAB function blocks "
         "(PathController, P2PController). ", ("This is the file to study and modify.", "b")),
    para("dot", ("zumo_sim/simulation.py", "c"), " – the block diagram: rate limiter (trapezoidal "
         "profile), θ and de gains, wheel PI loops and odometry, executed every 10 ms."),
    para("dot", ("zumo_sim/params.py", "c"), " – InitZumo.m and all gains in one place (ZumoParams)."),
    para("dot", ("zumo_sim/motor.py", "c"), " – DC motor, 75:1 gearbox, Hall encoder and the PI controller."),
    para("dot", ("zumo_sim/odometry.py", "c"), " – encoder position estimation (Section 2.2)."),

    para("h3", "3. Key Parameters to Explore"),
    para("p", "The left panel of the GUI groups the parameters that influence the robot's behavior:"),
]
S += KEEP["params"][:-1]
S += [
    para("dot", ("Way-point logic: ", "b"), "pass distance (advance to the next point) and stop distance "
         "(stop at the last point)."),
    para("dot", ("Motor mismatch: ", "b"), "makes one motor weaker than the other. This is not in the MATLAB "
         "model, but it is a useful way to see how robust each controller is to real hardware differences."),
    KEEP["params"][-1],

    para("h3", "4. The Simulator GUI"),
    para("p", "Start the GUI with ", ("python gui.py", "c"), ". The 2D path is on the left. The time responses "
              "(heading, cross-track error, velocities and PWM commands) are on the right."),
    image("gui_screenshot.png", width=6.5),
    para("dot", ("Controller: ", "b"), "choose Path control, Point to point or Simplified open loop."),
    para("dot", ("Desired path: ", "b"), "choose a preset, or type the points as x y; x y; ... (MATLAB style, "
         "in meters) and press Apply points. With ", ("Draw on plot", "b"),
         " ticked, left-click on the X-Y plot adds a point and right-click removes the last one. ",
         ("Load...", "b"), " reads a two-column text/CSV file."),
    para("dot", ("Sliders: ", "b"), "every change re-runs the simulation automatically. You can also type an "
         "exact value in the box next to a slider and press Enter."),
    para("dot", ("Pin run ", "b"), "keeps the current result on the plot (grey) so you can compare it with "
         "the next change. ", ("Clear pins", "b"), " removes them."),
    para("dot", ("Animate ", "b"), "replays the motion. The circle marks the way-point the controller is "
         "currently tracking."),
    para("dot", ("Result ", "b"), "panel: finish time, final position error, and maximum / RMS deviation from "
         "the desired path. Use these numbers to compare tuning experiments."),
    para("dot", ("Export CSV ", "b"), "saves all signals of the current run. The toolbar under the plots "
         "zooms and saves the figure as an image."),

    para("h3", "5. Step-by-Step Instructions"),
    para("step", ("Setup", "b")),
    para("sub", "Activate the virtual environment and run ", ("python gui.py", "c"), "."),
    para("sub", "Press ", ("Defaults", "b"), " to load the default parameters. These are the same values as "
         "InitZumo.m and the Simulink models."),

    para("step", ("Simplified open loop", "b"), " (Simplified_OpenLoop)"),
    para("sub", "Choose the preset ", ("Single point (-1, 1)", "b"), " and select the controller ",
         ("Simplified open loop", "b"), "."),
    para("sub", "Observe the robot's trajectory, the wheel speeds and the PWM commands. Note how the absence "
         "of wheel-speed feedback affects the motion. Compare with the P2P result in the next step."),

    para("step", ("Point to point – single point", "b"), " (ZumoSimulatiom_P2P)"),
    image("gui_p2p_single.png", width=6.0),
    para("sub", "Select ", ("Point to point", "b"), " with the preset ", ("Single point (-1, 1)", "b"),
         ". You can also type -1 1 in the path box and press Apply points."),
    para("sub", "Inspect how the robot moves to a single target (x,y)."),
    KEEP["pid_adjust"],
    para("sub", "Press ", ("Pin run", "b"), " before each change so the previous result stays on the plot "
         "for comparison."),
    KEEP["record_obs"],

    para("step", ("Point to point – multi way-point", "b"), " (ZumoSimulatiom_P2P_MultiPoint)"),
    para("sub", "Keep ", ("Point to point", "b"), " selected and enter the waypoints ",
         ("0 0.2; 0 0.4; 0 0.6; 0 0.8; 0 1", "c"), " (or the preset Line 1 m)."),
    para("sub", "Run the simulation and examine the time plots: heading, remaining distance, velocity "
         "profile and PWM commands."),
    para("sub", ("Try extending the path to 2 meters ", "b"), "(e.g., ", ("0 0.5; 0 1.0; 0 1.5; 0 2.0", "c"), ")."),
    KEEP["transitions"],

    para("step", ("Path control", "b"), " (ZumoSimulatiom_Path_Control)"),
    para("sub", "Select ", ("Path control", "b"), " and use the same points as in the previous step."),
    KEEP["attention"],
    KEEP["gradually"],
    KEEP["plot_final"],
    para("sub", ("Square path: ", "b"), "load the preset ", ("Square 0.5 m", "b"), " with the default gains. "
         "Does the robot complete the path? Use the way-point logic in PathController.update() (pass "
         "distance and the next-point-is-closer test) to explain what happens. Then find at least one fix: "
         "different gains, a different pass distance, or a change to the code. P2P mode completes this "
         "path. Why?"),

    para("step", ("Data Plotting and Analysis", "b")),
    para("sub", "The GUI records and plots the robot's position, heading, errors, velocities and PWM commands. "
         "Save figures with the toolbar's save icon, or export the data of a run with Export CSV."),
    para("sub", "For scripted analysis, call the simulator from Python, for example ",
         ("r = simulate(points, \"path\", ZumoParams(k_theta=0.3))", "c"), " and then ",
         ("plt.plot(r.x, r.y)", "c"), ". The result also holds t, phi, theta_t, de, dist, v_cmd, wl/wr "
         "(wheel speeds) and ul/ur (PWM)."),
    para("sub", ("examples/gain_sweep.py", "c"), " sweeps one gain. It plots the trajectories and prints a table "
         "of finish time, final error and path deviation. This is a good starting point for the tuning deliverable."),

    para("step", ("Concluding tasks", "b")),
    para("sub", "Open ", ("examples/plot_script.py", "c"), " (the Python version of plotScript.m). It runs the P2P "
         "and Path control simulations on the variable ", ("DesiredCoordinates", "b"), " and plots both:"),
    code('''
from zumo_sim import ZumoParams, simulate, paths

DesiredCoordinates = paths.line(2.0, 0.2)       # [0 0.2; 0 0.4; ... 0 2]
# DesiredCoordinates = paths.infinity()          # infinity sign (infSignMath.m)

Record_P2P  = simulate(DesiredCoordinates, "p2p",  ZumoParams(decel_factor=2.0, k_theta=0.1))
Record_Path = simulate(DesiredCoordinates, "path", ZumoParams(k_theta=0.1, k_de=0.25))

plt.plot(Record_P2P.x, Record_P2P.y, label="P2P")
plt.plot(Record_Path.x, Record_Path.y, label="Path")
'''),
    KEEP["adjust_gains"],
    image("plot_inf_untuned.png", "plot_inf_tuned.png", width=3.1),
    KEEP["define_path"],
    KEEP["example"],
    KEEP["example_img"],
    para("sub", ("Optional: ", "b"), ("examples/custom_controller.py", "c"), " is a template for writing your own "
         "controller. The example steers toward a look-ahead point (Pure Pursuit, Section 4.1). Compare its "
         "tracking with the original Path controller, and explain the difference."),
]
# deliverables + conclusion (kept), renumbered
deliv = KEEP["deliverables"]
for el in deliv:
    p = Paragraph(el, doc._body)
    if p.text.strip() == "5. Deliverables":
        set_text(el, "6. Deliverables")
S += deliv

insert_after(B[i_pre], S)
# the pre-lab heading itself: mention Python
set_text(B[i_pre], "7. Pre-Lab Activity (Python Simulation)")

# --- in-lab: plotting in Python first
for el in doc.element.body.iterchildren():
    if el.tag != qn("w:p"):
        continue
    for t in el.iter(qn("w:t")):
        if t.text and "using matlab or python" in t.text:
            t.text = t.text.replace("using matlab or python", "using Python (or MATLAB)")
        if t.text and "in matlab or python" in t.text:
            t.text = t.text.replace("in matlab or python", "in Python (or MATLAB)")

# --- appendix A: Python version of the conversion script
B2 = list(doc.element.body.iterchildren())
B[:] = B2
j = find("output_str", 0)
while True:          # last line of the MATLAB script
    nxt = B2[j + 1]
    if nxt.tag == qn("w:p") and Paragraph(nxt, doc._body).text.strip().startswith("output_str"):
        j += 1
    else:
        break
insert_after(B2[j], [
    para("p", ""),
    para("p", "Python version (zumo_sim.paths.to_cpp), including the conversion from meters to millimetres "
              "used by the robot code:"),
    code('''
from zumo_sim import paths
car_vec = [[0.1, 0], [0.2, 0.1], [0.3, 0.1]]       # desired path in meters
print(paths.to_cpp(car_vec, scale=1000))
# -> float desiredPath[][2] = { {100, 0}, {200, 100}, {300, 100} };
'''),
])

doc.save(DST)
print("saved", DST)

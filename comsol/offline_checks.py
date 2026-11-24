"""Checks that need no COMSOL: geometry against the Python model, and a dry run of the driver.

The dry run uses a stand-in for the COMSOL API that accepts every call.  It proves the script's
own logic (grid, resume, mode choice, CSV format).  It does NOT prove that COMSOL accepts the calls.
"""
import csv, math, os, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "code"))
import pcf_comsol as C
from pcf_fem import Design

# ---- 1. geometry: polygons of every COMSOL ellipse/sector against the Python holes
def params(isV, eta):
    env = {"sqrt": math.sqrt, "c_const": 299792458.0}
    for n, e, _ in C.PARAMS:
        e = e.replace("[um]", "")
        if n == "isV": v = isV
        elif n == "eta": v = eta
        elif e.startswith("if("):
            a, b = e[len("if(isV>0.5,"):-1].split(",")
            v = env[a] if isV > .5 else env[b]
        else: v = eval(e, {}, env)
        env[n] = v
    return env

for kind in "VH":
    for eta in (0.6, 0.7, 1.0):
        env, d = params(1 if kind == "V" else 0, eta), Design(kind=kind, eta=eta)
        X, Y = d.window()
        assert abs(env["X0"] - X) < 1e-12 and abs(env["Y0"] - Y) < 1e-12
        area = {"air": 0.0, "ana": 0.0}
        want = {(round(x, 6), round(y, 6)): (rx, ry, "air" if t == 2 else "ana")
                for x, y, rx, ry, t in d.holes() if x > -1e-9 and y > -1e-9}
        seen = set()
        for x, y, a, b, ang, rot, grp in C.quarter_holes():
            x, y, a, b = (eval(s, {}, env) for s in (x, y, a, b))
            k = (round(x, 6) + 0.0, round(y, 6) + 0.0)
            w = next(v for q, v in want.items() if abs(q[0]-k[0]) < 1e-5 and abs(q[1]-k[1]) < 1e-5)
            seen.add(k)
            th = np.linspace(0, math.radians(ang), 4001); px, py = a*np.cos(th), b*np.sin(th)
            if ang < 360: px, py = np.r_[0, px], np.r_[0, py]
            r = math.radians(rot); gx, gy = x + px*math.cos(r) - py*math.sin(r), y + px*math.sin(r) + py*math.cos(r)
            assert gx.min() > -1e-9 and gy.min() > -1e-9, "hole leaves the quadrant"
            assert gx.max() < X and gy.max() < Y
            assert abs(gx.max() - x - w[0]) < 1e-5 and abs(gy.max() - y - w[1]) < 1e-5 and grp == w[2], "wrong shape"
            area[grp] += .5*abs(np.dot(gx, np.roll(gy, -1)) - np.dot(gy, np.roll(gx, -1)))
        assert len(seen) == len(want), (len(seen), len(want))
        assert abs(area["air"] - 36*math.pi*eta/4) < 1e-4 and abs(area["ana"] - 7*math.pi*.08/4) < 1e-5
print("geometry: positions, orientation, quadrant cuts and areas match the Python model (V/H, eta 0.6/0.7/1.0)")
want_air = 36*math.pi*0.7/4

# ---- 2. dry run
class Fake:
    """Accepts any call; returns fake modes for EvalGlobal."""
    par = {}; tags_made = set(); pol = "x"; solves = 0; fail_at = None
    def __init__(self, path=()): self.p = path
    def __getattr__(self, n): return Fake(self.p + (n,))
    def __call__(self, *a):
        last = self.p[-1]
        if last == "tags": return list(Fake.tags_made)
        if last == "create" and a and a[0] in ("gev1", "pg1"): Fake.tags_made.add(a[0])
        if self.p[-2:] == ("param", "set"): Fake.par[a[0]] = a[1]
        if last == "active": Fake.pol = ("x" if a[0] else "y") if "pmc_y0" in str(self.p) else Fake.pol
        if last == "run" and "study" in self.p:
            Fake.solves += 1
            if Fake.fail_at and Fake.solves == Fake.fail_at: raise RuntimeError("simulated crash")
        if last in ("getReal", "getImag"): return Fake.modes(last)
        return Fake(self.p[:-1] + ((last,) + tuple(map(str, a)) if a else (last,)))
    @staticmethod
    def modes(which):
        lam = float(Fake.par["lam0"].replace("[um]", "")); n0 = 1.441 - .0369*lam + (.0026 if Fake.pol == "y" else 0)
        if which == "getReal": return [[1.39, n0, -1.4], [.1, 20., 1.], [100., 100., 100.], [5., 98., 99.]]
        return [[-1e-5, -1e-9, 0.], [0.]*3, [0.]*3, [0.]*3]

# make param().set / feature(..).active resolvable: chain names only, arguments kept in the path
class Model:
    java = Fake(("M",))
    def save(self, p): self.saved = p
class Client:
    version = "dry-run"
    def create(self, name): return Model()

tmp = tempfile.mkdtemp(); C.RES = tmp
pm, P = C.build(Client()); assert P == "ewfd"
q = C.solve_point(pm.java, P, "V", 1.33, "x", 1.0, .7, 1.405)
assert abs(q[0][0] - 1.4041) < 1e-9 and q[0][4] == .98 and len(q) == 2, "mode choice / negative-index filter"
assert abs(q[0][2] - 8.685889638*2*math.pi/1e-6*1e-9) < 1e-12
assert C.to_table([[1, 2], [3, 4], [5, 6]], 2) == [[1, 3, 5], [2, 4, 6]]
Fake.fail_at = Fake.solves + 50
try: C.run_sweep(pm, P, "paper"); raise SystemExit("crash was not simulated")
except RuntimeError as e: assert "simulated" in str(e)
Fake.fail_at = None; before = Fake.solves
C.run_sweep(pm, P, "paper")
rows = list(csv.DictReader(open(os.path.join(tmp, "raw_comsol.csv"))))
keys = {tuple(r[k] for k in C.KEYS) for r in rows}
assert len(rows) == len(keys) == 192 == 12*(11+5), len(rows)
assert Fake.solves - before == 192 - 49, "resume repeated or skipped points"
assert list(rows[0]) == C.COLS
assert sum(len(t[4]) for t in C.grid("full")) == 360
C.save_model(pm, P); C.run_converge(pm, P)
print("dry run: mode choice, loss formula, grid sizes (192 / 360), crash-and-resume, CSV format, convergence run all OK")
print("NOT checked here: whether COMSOL itself accepts the API calls - only 'pcf_comsol.py test' can show that")

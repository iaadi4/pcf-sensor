"""Builds, solves and saves the PCF model in COMSOL through the COMSOL Java API (MPh).

    python pcf_comsol.py test        one point, compared with the Python reference  (do this first)
    python pcf_comsol.py converge    mesh / PML / gap check at that point
    python pcf_comsol.py paper       only the points the paper marks with symbols, plus curve ends
    python pcf_comsol.py full        the complete grid used in the Python work (360 solves)

Options: --cores N   --classkit (college class-kit licence)   --version 6.2
`paper` and `full` append to results/raw_comsol.csv after every solve and resume if stopped.

Needs COMSOL with the Wave Optics (or RF) Module.  One quarter of the fibre is modelled:
x-pol = PEC on x=0, PMC on y=0;  y-pol = PMC on x=0, PEC on y=0.
"""
import argparse, csv, math, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
KEYS = ["sweep", "mat", "kind", "n", "pol", "lam", "eta"]
COLS = KEYS + ["neff", "neff_im", "loss", "r", "core", "neff2", "core2", "loss2", "r2"]
NEIGS = 12

PARAMS = [  # name, expression, description
    ("Lam", "2.4[um]", "Cladding pitch"), ("Lamc", "1[um]", "Core pitch"),
    ("da", "1[um]", "Cladding hole major semi-axis"), ("eta", "0.7", "Ellipticity db/da"),
    ("db", "eta*da", "Cladding hole minor semi-axis"),
    ("ds", "0.4[um]", "Core hole major semi-axis"), ("dc", "0.2[um]", "Core hole minor semi-axis"),
    ("isV", "1", "1 = V-PCF, 0 = H-PCF"),
    ("rx", "if(isV>0.5,db,da)", "Cladding hole x semi-axis"), ("ry", "if(isV>0.5,da,db)", "Cladding hole y semi-axis"),
    ("cx", "if(isV>0.5,dc,ds)", "Core hole x semi-axis"), ("cy", "if(isV>0.5,ds,dc)", "Core hole y semi-axis"),
    ("lam0", "1[um]", "Wavelength"), ("f0", "c_const/lam0", "Frequency"),
    ("nsi", "1.45", "Silica index"), ("na", "1.33", "Analyte index"),
    ("gap", "1[um]", "Silica between outermost hole and PML"), ("tpml", "2.5[um]", "PML thickness"),
    ("X0", "3*Lam+rx+gap", "Inner window half-width"), ("Y0", "3*Lam*sqrt(3)/2+ry+gap", "Inner window half-height"),
    ("hs", "1", "Mesh scale (smaller = finer)"), ("nguess", "1.405", "Mode search centre"),
]


def quarter_holes():
    """Holes of the closed first quadrant as COMSOL Ellipse settings.

    (x, y, a, b, sector angle, rotation, group).  Holes centred on an axis are cut there:
    180-degree sector upwards for y=0; 180-degree sector rotated by -90 for x=0 (its local
    x axis then points along -y, so the semi-axes are swapped); 90 degrees at the origin.
    """
    out = []
    for j in range(0, 4):
        for k in range(7 - j):
            xi = -(6 - j) / 2 + k                  # in units of Lam
            if xi < -1e-9 or (j == 0 and abs(xi) < 1e-9):
                continue
            x, y = f"{xi:g}*Lam", f"{j}*Lam*sqrt(3)/2"
            if j == 0:
                out.append((x, "0", "rx", "ry", 180, 0, "air"))
            elif abs(xi) < 1e-9:
                out.append(("0", y, "ry", "rx", 180, -90, "air"))
            else:
                out.append((x, y, "rx", "ry", 360, 0, "air"))
    out.append(("0", "0", "cx", "cy", 90, 0, "ana"))
    out.append(("0", "Lamc", "cy", "cx", 180, -90, "ana"))
    out.append(("Lamc*sqrt(3)/2", "Lamc/2", "cx", "cy", 360, 0, "ana"))
    return out


# ------------------------------------------------------------------ model building
def build(client):
    pm = client.create("PCF_liquid_sensor")
    M = pm.java
    for n, e, d in PARAMS:
        M.param().set(n, e, d)
    M.component().create("comp1", True)
    c = M.component("comp1")
    g = c.geom().create("geom1", 2)
    g.lengthUnit("um")
    for t in ("csel_air", "csel_ana", "csel_in"):
        g.selection().create(t, "CumulativeSelection")
    for tag, pos, size, inner in (("r0", ["0", "0"], ["X0", "Y0"], True),
                                  ("r1", ["X0", "0"], ["tpml", "Y0"], False),
                                  ("r2", ["0", "Y0"], ["X0", "tpml"], False),
                                  ("r3", ["X0", "Y0"], ["tpml", "tpml"], False)):
        f = g.create(tag, "Rectangle")
        f.set("pos", pos)
        f.set("size", size)
        if inner:
            f.set("contributeto", "csel_in")
    for i, (x, y, a, b, ang, rot, grp) in enumerate(quarter_holes()):
        f = g.create(f"e{i+1}", "Ellipse")
        f.set("pos", [x, y])
        f.set("semiaxes", [a, b])
        f.set("angle", str(ang))
        f.set("rot", str(rot))
        f.set("contributeto", "csel_" + grp)
    g.run()

    # selections: everything outside the inner window is PML
    c.selection().create("pmlsel", "Complement")
    c.selection("pmlsel").set("input", ["geom1_csel_in_dom"])
    for tag, (a, b, p, q) in {"wall_x0": ("-0.001", "0.001", "-0.1", "1000"),
                              "wall_y0": ("-0.1", "1000", "-0.001", "0.001")}.items():
        s = c.selection().create(tag, "Box")
        s.set("entitydim", "1")
        for name, v in zip(("xmin", "xmax", "ymin", "ymax"), (a, b, p, q)):
            s.set(name, v)
        s.set("condition", "inside")

    for tag, label, n, sel in (("mat1", "Silica", "nsi", None), ("mat2", "Air", "1", "geom1_csel_air_dom"),
                               ("mat3", "Analyte", "na", "geom1_csel_ana_dom")):
        m = c.material().create(tag, "Common")
        m.label(label)
        m.propertyGroup().create("RefractiveIndex", "Refractive index")
        m.propertyGroup("RefractiveIndex").set("n", [n, "0", "0", "0", n, "0", "0", "0", n])
        m.propertyGroup("RefractiveIndex").set("ki", ["0"] * 9)
        if sel:
            m.selection().named(sel)

    pml = c.coordSystem().create("pml1", "PML")
    pml.selection().named("pmlsel")

    try:
        ph, P = c.physics().create("ewfd", "ElectromagneticWavesFrequencyDomain", "geom1"), "ewfd"
    except Exception as first:
        print("Wave Optics interface not available, trying the RF Module:", str(first).splitlines()[0])
        ph, P = c.physics().create("emw", "ElectromagneticWaves", "geom1"), "emw"
    ph.feature("wee1").set("DisplacementFieldModel", "RefractiveIndex")
    for tag, sel in (("pmc_x0", "wall_x0"), ("pmc_y0", "wall_y0")):
        b = ph.create(tag, "PerfectMagneticConductor", 1)
        b.selection().named(sel)

    for tag, sel in (("intA", "geom1_csel_ana_dom"), ("intT", "geom1_csel_in_dom")):
        o = c.cpl().create(tag, "Integration")
        o.selection().named(sel)
        o.set("opname", tag)

    mesh = c.mesh().create("mesh1")
    sz = mesh.feature("size")
    sz.set("custom", "on")
    sz.set("hmax", "0.25[um]*hs")
    sz.set("hmin", "0.01[um]*hs")
    sz.set("hgrad", "1.2")
    sz.set("hcurve", "0.2")
    ft = mesh.create("ftri1", "FreeTri")
    s1 = ft.create("size1", "Size")
    s1.selection().geom("geom1", 2)
    s1.selection().named("geom1_csel_ana_dom")
    s1.set("custom", "on")
    s1.set("hmaxactive", True)
    s1.set("hmax", "0.08[um]*hs")

    st = M.study().create("std1")
    st.create("mode", "ModeAnalysis")
    md = st.feature("mode")
    md.set("modeFreq", "f0")
    md.set("neigsactive", True)
    md.set("neigs", NEIGS)
    md.set("shiftactive", True)
    md.set("shift", "nguess")
    return pm, P


def choose_pol(M, P, pol):
    ph = M.component("comp1").physics(P)
    ph.feature("pmc_y0").active(pol == "x")
    ph.feature("pmc_x0").active(pol == "y")


def to_table(j, nexpr):
    """Java double[][] -> list of rows per expression, whichever way round it comes."""
    a = [[float(v) for v in row] for row in j]
    if len(a) != nexpr and a and len(a[0]) == nexpr:
        a = [list(x) for x in zip(*a)]
    if len(a) != nexpr:
        raise RuntimeError(f"unexpected result shape {len(a)}x{len(a[0]) if a else 0}")
    return a


def solve_point(M, P, kind, n, pol, lam, eta, guess, extra=None):
    """Returns the modes found, most core-confined first: (neff, neff_im, loss, r, core)."""
    p = M.param()
    p.set("isV", "1" if kind == "V" else "0")
    p.set("na", repr(float(n)))
    p.set("lam0", f"{lam:.6g}[um]")
    p.set("eta", f"{eta:.6g}")
    p.set("nguess", f"{guess:.8f}")
    for k, v in (extra or {}).items():
        p.set(k, v)
    choose_pol(M, P, pol)
    M.component("comp1").geom("geom1").run()
    M.component("comp1").mesh("mesh1").run()
    M.study("std1").run()
    num = M.result().numerical()
    if "gev1" not in [str(t) for t in num.tags()]:
        ev = num.create("gev1", "EvalGlobal")
        ev.set("expr", [f"{P}.neff", f"intA({P}.Poavz)", f"intT({P}.Poavz)",
                        f"intT({P}.Poavz*(x^2+y^2<(2[um])^2))"])
    ev = M.result().numerical("gev1")
    re, im = to_table(ev.getReal(), 4), to_table(ev.getImag(), 4)
    out = []
    for m in range(len(re[0])):
        ne, ni, tot = re[0][m], im[0][m], re[2][m]
        if ne <= 0 or tot == 0 or not all(map(math.isfinite, (ne, ni, tot))):
            continue
        loss = 8.685889638 * 2 * math.pi / (lam * 1e-6) * abs(ni)
        out.append((ne, ni, loss, 100 * n / ne * re[1][m] / tot, re[3][m] / tot))
    if not out:
        raise RuntimeError("no usable mode found")
    return sorted(out, key=lambda q: -q[4])


# ------------------------------------------------------------------ runs
def reference():
    rows = {}
    with open(os.path.join(HERE, "..", "results", "raw_main.csv")) as f:
        for r in csv.DictReader(f):
            if r["sweep"] == "lam" and abs(float(r["lam"]) - 1) < 1e-9:
                rows[r["kind"], float(r["n"]), r["pol"]] = {k: float(r[k]) for k in ("neff", "loss", "r")}
    return rows


def run_test(pm, P):
    ref, ok = reference(), True
    for kind, n in (("V", 1.33), ("H", 1.366)):
        got = {}
        for pol in "xy":
            t = time.time()
            got[pol] = solve_point(pm.java, P, kind, n, pol, 1.0, 0.7, 1.405 if n < 1.34 else 1.414)[0]
            print(f"  {kind} n={n} {pol}-pol solved in {time.time()-t:.0f} s, core power {got[pol][4]:.3f}", flush=True)
        x, rx_, ry_ = got["x"], ref[kind, n, "x"], ref[kind, n, "y"]
        B, Br = abs(x[0] - got["y"][0]), abs(rx_["neff"] - ry_["neff"])
        for name, a, b, good in (("n_eff", x[0], rx_["neff"], abs(x[0] - rx_["neff"]) < 5e-5),
                                 ("B", B, Br, abs(B / Br - 1) < 0.01),
                                 ("loss dB/m", x[2], rx_["loss"], abs(x[2] / rx_["loss"] - 1) < 0.05),
                                 ("r %", x[3], rx_["r"], abs(x[3] - rx_["r"]) < 0.1)):
            print(f"    {name:10s} COMSOL {a:.6g}   Python {b:.6g}   {'PASS' if good else 'CHECK'}")
            ok &= good
    print("TEST", "PASSED" if ok else "NOT PASSED - see comsol/README_COMSOL.md, 'If the test fails'")
    return ok


def run_converge(pm, P):
    with open(os.path.join(RES, "convergence_comsol.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["setting", "neff", "B", "loss", "r"])
        base = {"hs": "1", "tpml": "2.5[um]", "gap": "1[um]"}
        for name, ch in (("base", {}), ("hs=1.5", {"hs": "1.5"}), ("hs=0.75", {"hs": "0.75"}),
                         ("PML 4um", {"tpml": "4[um]"}), ("gap 2um", {"gap": "2[um]"})):
            x, y = (solve_point(pm.java, P, "V", 1.33, p, 1.0, 0.7, 1.405, {**base, **ch})[0] for p in "xy")
            row = [name, x[0], abs(x[0] - y[0]), x[2], x[3]]
            w.writerow(row)
            f.flush()
            print("  {:9s} n={:.6f} B={:.5e} loss={:.4e} r={:.3f}".format(*row), flush=True)
        for k, v in base.items():
            pm.java.param().set(k, v)


def grid(mode):
    if mode == "full":
        lams, etas = [round(.7 + .05*i, 3) for i in range(21)], [round(.6 + .05*i, 3) for i in range(9)]
    else:
        lams, etas = [round(.7 + .1*i, 3) for i in range(11)], [.6, .7, .8, .9, 1.0]
    return [(s, k, n, p, pts) for s, pts in (("lam", lams), ("eta", etas))
            for k in "VH" for n in (1.33, 1.354, 1.366) for p in "xy"]


def key(sweep, kind, n, pol, lam, eta):
    return (sweep, "const", kind, round(n, 4), pol, round(lam, 4), round(eta, 4))


def run_sweep(pm, P, mode):
    path = os.path.join(RES, "raw_comsol.csv")
    done = {}
    if os.path.exists(path):
        with open(path) as f:
            for r in csv.DictReader(f):
                if r.get("r2") not in (None, ""):          # ignores a half-written last line
                    done[key(r["sweep"], r["kind"], float(r["n"]), r["pol"], float(r["lam"]), float(r["eta"]))] = float(r["neff"])
        print(f"resuming: {len(done)} points already done")
    new = not os.path.exists(path)
    total = sum(len(t[4]) for t in grid(mode))
    count = 0
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(COLS)
        for sweep, kind, n, pol, pts in grid(mode):
            mid = min(range(len(pts)), key=lambda i: abs(pts[i] - (1.1 if sweep == "lam" else 0.8)))
            start = None
            for seq in (range(mid, len(pts)), range(mid - 1, -1, -1)):   # march outwards from the middle
                hist = [start] if start else []
                for i in seq:
                    q = pts[i]
                    lam, eta = (q, 0.7) if sweep == "lam" else (1.0, q)
                    kk = key(sweep, kind, n, pol, lam, eta)
                    if len(hist) >= 2:
                        (p1, n1), (p2, n2) = hist[-2:]
                        g = n2 + (n2 - n1) / (p2 - p1) * (q - p2)
                    elif hist:
                        g = hist[-1][1] + (0.035 * (hist[-1][0] - q) if sweep == "lam" else 0)
                    else:
                        g = 1.405
                    if kk not in done:
                        ms = solve_point(pm.java, P, kind, n, pol, lam, eta, g)
                        a = ms[0]
                        b = ms[1] if len(ms) > 1 else (0.0,) * 5
                        w.writerow([*kk, a[0], a[1], a[2], a[3], a[4], b[0], b[4], b[2], b[3]])
                        f.flush()
                        done[kk] = a[0]
                    hist.append((q, done[kk]))
                    if start is None:
                        start = hist[0]
                    count += 1
            print(f"{count}/{total} {sweep} {kind} n={n} {pol}", flush=True)
    print("finished; now run:  python compare_comsol.py")


def save_model(pm, P):
    """Leaves the model solved at V, n=1.33, 1 um, x-pol, with field plots, and saves it."""
    M = pm.java
    solve_point(M, P, "V", 1.33, "x", 1.0, 0.7, 1.405)
    try:
        if "pg1" not in [str(t) for t in M.result().tags()]:
            M.result().create("pg1", "PlotGroup2D")
            M.result("pg1").label("Electric field norm")
            M.result("pg1").create("surf1", "Surface")
            M.result("pg1").feature("surf1").set("expr", f"{P}.normE")
    except Exception as e:
        print("plot group not created (harmless):", str(e).splitlines()[0])
    pm.save(os.path.join(RES, "PCF_liquid_sensor.mph"))
    print("saved", os.path.join(RES, "PCF_liquid_sensor.mph"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["test", "converge", "paper", "full"])
    ap.add_argument("--cores", type=int, default=2)
    ap.add_argument("--classkit", action="store_true")
    ap.add_argument("--version")
    a = ap.parse_args()
    os.makedirs(RES, exist_ok=True)
    import mph
    if a.classkit:
        mph.option("classkit", True)
    print("starting COMSOL ...", flush=True)
    client = mph.start(cores=a.cores, version=a.version)
    print("COMSOL", client.version, flush=True)
    pm, P = build(client)
    print("model built; physics interface:", P, flush=True)
    if a.mode == "test":
        ok = run_test(pm, P)
        save_model(pm, P)
        sys.exit(0 if ok else 1)
    if a.mode == "converge":
        run_converge(pm, P)
    else:
        run_sweep(pm, P, a.mode)
        save_model(pm, P)


if __name__ == "__main__":
    main()

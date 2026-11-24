"""Compares the COMSOL sweep with (1) the paper's digitised values and (2) the Python FEM results.

    python compare_comsol.py [raw_csv] [output_folder]
Defaults: results/raw_comsol.csv -> results/
Every available point is used in the 'all points' columns; nothing is dropped silently.
"""
import os, sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results", "raw_comsol.csv")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "results")
if not os.path.exists(RAW):
    sys.exit(f"{RAW} not found: run pcf_comsol.py paper (or full) first")
os.makedirs(OUT, exist_ok=True)
K = ["sweep", "mat", "kind", "n", "lam", "eta"]


def tidy(raw):
    raw = raw.dropna()
    for c in ("n", "lam", "eta"):
        raw[c] = raw[c].astype(float).round(4)
    raw = raw.drop_duplicates(K + ["pol"], keep="last")
    x = raw[raw.pol == "x"].set_index(K)
    y = raw[raw.pol == "y"].set_index(K)[["neff", "core"]].add_suffix("_y")
    d = x.join(y)                                   # B stays NaN where the y mode is missing
    d["B"] = (d.neff - d.neff_y).abs()
    d["clean"] = d.core > 0.85
    d["cleanB"] = d.clean & (d.core_y > 0.85)
    return d.reset_index().sort_values(K)


cs = tidy(pd.read_csv(RAW))
py = tidy(pd.read_csv(os.path.join(HERE, "..", "results", "raw_main.csv")))
paper = pd.read_csv(os.path.join(HERE, "..", "paper_data", "paper_digitised.csv"))
cs.to_csv(os.path.join(OUT, "results_comsol.csv"), index=False)

# ---- COMSOL against Python
j = cs.merge(py, on=K, suffixes=("", "_py"))
for q in ("neff", "B", "loss", "r"):
    j["d_" + q] = 100 * (j[q] / j[q + "_py"] - 1)
j.to_csv(os.path.join(OUT, "comsol_vs_python.csv"), index=False)

# ---- figures and COMSOL against paper
COL = {1.33: "#1f77b4", 1.354: "#d95f02", 1.366: "#2a9d4a"}
MK = {1.33: "s", 1.354: "^", 1.366: "o"}
Q = {"2": ("neff", "Effective index", False), "4": ("B", "Birefringence (×10⁻³)", False),
     "5": ("loss", "Confinement loss (dB/m)", True), "6": ("r", "Relative sensitivity r (%)", False)}
rows, missing = [], 0
for f, (q, lab, lg) in Q.items():
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.7))
    for A, sw, s in zip(ax, ("lam", "eta"), "ab"):
        for (k, n), c in cs[cs.sweep == sw].groupby(["kind", "n"]):
            sc = 1e3 if q == "B" else 1
            ok = c.cleanB if q == "B" else c.clean
            A.plot(c[sw], (c[q] * sc).where(ok), "-" if k == "V" else "--", color=COL[n], lw=1.5, label=f"{k}, n = {n}")
            A.plot(c[sw][~ok], c[q][~ok] * sc, "x", color=COL[n], ms=6)
        for _, t in paper[paper.fig == f + s].iterrows():
            A.plot(t.x, t.value * (1e3 if q == "B" else 1), MK[t.n], ms=5.5, ls="none", mec=COL[t.n],
                   mfc=COL[t.n] if t.kind == "V" else "white")
            m = cs[(cs.sweep == sw) & (cs.kind == t.kind) & (cs.n == t.n) & np.isclose(cs[sw], t.x)]
            if len(m) and np.isfinite(m.iloc[0][q]):
                m = m.iloc[0]
                rows.append(dict(fig=f + s, x=t.x, kind=t.kind, n=t.n, paper=t.value, comsol=m[q],
                                 clean=bool(m.cleanB if q == "B" else m.clean)))
            else:
                missing += 1
        A.set(xlabel="Wavelength (µm)" if sw == "lam" else "Ellipticity η", ylabel=lab,
              title=f"({s}) " + ("η = 0.7" if sw == "lam" else "λ = 1 µm"))
        if lg: A.set_yscale("log")
        A.grid(alpha=.25)
    h, _ = ax[0].get_legend_handles_labels()
    if h: ax[0].legend(fontsize=8)
    fig.suptitle("Lines: COMSOL.  Markers: values read from the paper (filled V, open H).  ×: weakly confined / mode-mixed.", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, f"comsol_fig{f}.png"), dpi=200)
    plt.close(fig)

out = [f"points: {len(cs)} COMSOL, {len(j)} shared with Python; paper markers without a COMSOL point: {missing}", "",
       "COMSOL vs Python, |difference| in %"]
for q in ("neff", "B", "loss", "r"):
    a = j["d_" + q].abs().dropna()
    b = j.loc[j.cleanB if q == "B" else j.clean, "d_" + q].abs().dropna()
    if len(a) and len(b):
        out.append(f"  {q:5s} all: median {a.median():.4f} mean {a.mean():.4f} max {a.max():.3f} (N={len(a)})"
                   f" | well confined: mean {b.mean():.4f} max {b.max():.3f} (N={len(b)})")
out += ["", "COMSOL vs paper, |difference| in %"]
if rows:
    c = pd.DataFrame(rows)
    c["err_pct"] = 100 * (c.comsol / c.paper - 1)
    c.to_csv(os.path.join(OUT, "comsol_vs_paper.csv"), index=False)
    for f, g in c.groupby("fig"):
        e, z = g.err_pct.abs(), g[g.clean].err_pct.abs()
        out.append(f"  {f}  all: median {e.median():.3f} mean {e.mean():.3f} max {e.max():.2f} (N={len(e)})"
                   f" | well confined: mean {z.mean():.3f} max {z.max():.2f} (N={len(z)})")
else:
    out.append("  no common points yet")
out.append("")
out.append("Losses below about 1e-8 dB/m come straight from the COMSOL eigenvalue and are round-off limited.")
txt = "\n".join(out)
open(os.path.join(OUT, "comsol_summary.txt"), "w").write(txt + "\n")
print(txt)

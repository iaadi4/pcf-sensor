"""Figures 2,4,5,6 (lines: this work, markers: paper), error statistics, trend checks."""
import numpy as np, pandas as pd, json, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
R = "../results/"
raw = pd.read_csv(R + "raw_main.csv"); paper = pd.read_csv("../paper_data/paper_digitised.csv")

def tidy(raw):
    k = ["sweep", "mat", "kind", "n", "lam", "eta"]
    x = raw[raw.pol == "x"].set_index(k); y = raw[raw.pol == "y"].set_index(k)
    d = x[["neff", "loss", "r", "core", "core2", "neff2"]].join(
        y[["neff", "loss", "r", "core", "core2"]].add_suffix("_y"))
    d["B"] = (d.neff - d.neff_y).abs()
    d["clean"] = d.core > 0.85                           # x-mode well confined and unmixed
    d["cleanB"] = d.clean & (d.core_y > 0.85)
    return d.reset_index().sort_values(k)

if __name__ == "__main__":
    df = tidy(raw); df.to_csv(R + "results_main.csv", index=False)
    print("points", len(df), "flagged (mode mixing):"); print(df[~df.cleanB][["sweep","kind","n","lam","eta","neff","core","core2","core_y","core2_y","loss","r"]].to_string())
    COL = {1.33: "#1f77b4", 1.354: "#d95f02", 1.366: "#2a9d4a"}; MK = {1.33: "s", 1.354: "^", 1.366: "o"}
    Q = {"2": ("neff", "Effective index", False), "4": ("B", "Birefringence (×10⁻³)", False),
         "5": ("loss", "Confinement loss (dB/m)", True), "6": ("r", "Relative sensitivity r (%)", False)}
    rows = []
    for f, (q, lab, lg) in Q.items():
        fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.7))
        for A, sw, s in zip(ax, ("lam", "eta"), "ab"):
            g = df[df.sweep == sw]
            for (k, n), c in g.groupby(["kind", "n"]):
                sc = 1e3 if q == "B" else 1
                ok = c.cleanB if q == "B" else c.clean
                A.plot(c[sw], (c[q] * sc).where(ok), "-" if k == "V" else "--", color=COL[n], lw=1.5, label=f"{k}, n = {n}")
                A.plot(c[sw][~ok], c[q][~ok] * sc, "x", color=COL[n], ms=6, mew=1.4)
                p = paper[(paper.fig == f + s) & (paper.kind == k) & (paper.n == n)]
                A.plot(p.x, p.value * sc, MK[n], ms=5.5, mfc=COL[n] if k == "V" else "white", mec=COL[n], ls="none")
                for _, t in p.iterrows():
                    m = c[np.isclose(c[sw], t.x)].iloc[0]
                    rows.append(dict(fig=f + s, x=t.x, kind=k, n=n, paper=t.value, ours=m[q], clean=bool(m.cleanB if q == "B" else m.clean)))
            A.set(xlabel="Wavelength (µm)" if sw == "lam" else "Ellipticity η", ylabel=lab,
                  title=f"({s}) " + ("η = 0.7" if sw == "lam" else "λ = 1 µm"))
            if lg: A.set_yscale("log")
            A.grid(alpha=.25)
        ax[0].legend(fontsize=8)
        fig.suptitle("Lines: this work (FEM).  Markers: values read from the paper (filled V, open H).  ×: weakly confined / mode-mixed points.", fontsize=10)
        fig.tight_layout(); fig.savefig(R + f"figures/fig{f}.png", dpi=200); plt.close(fig)
    c = pd.DataFrame(rows)
    c["rel_err_pct"] = 100 * (c.ours - c.paper) / c.paper
    c["dex"] = np.log10(c.ours / c.paper)
    c.to_csv(R + "comparison.csv", index=False)
    s = c.groupby("fig").agg(N=("x", "size"), mean_abs_pct=("rel_err_pct", lambda v: v.abs().mean()),
         median_abs_pct=("rel_err_pct", lambda v: v.abs().median()), max_abs_pct=("rel_err_pct", lambda v: v.abs().max()),
         median_abs_dex=("dex", lambda v: v.abs().median()), max_abs_dex=("dex", lambda v: v.abs().max()))
    cc = c[c.clean]
    s["N_clean"] = cc.groupby("fig").size()
    s["mean_abs_pct_clean"] = cc.groupby("fig").rel_err_pct.apply(lambda v: v.abs().mean())
    s["max_abs_pct_clean"] = cc.groupby("fig").rel_err_pct.apply(lambda v: v.abs().max())
    for lim in (1e-7,):
        z = c[(c.fig.str[0] == "5") & (c.paper > lim)]
        s[f"median_abs_pct_above_{lim:g}"] = z.groupby("fig").rel_err_pct.apply(lambda v: v.abs().median())
        s[f"N_above_{lim:g}"] = z.groupby("fig").size()
    s.to_csv(R + "error_summary.csv"); print(s.round(3).to_string())
    print(c[(c.fig.str[0] != "5")].assign(a=lambda t: t.rel_err_pct.abs()).nlargest(15, "a").round(4).to_string())
    print(c[c.fig.str[0] == "5"].assign(a=lambda t: t.dex.abs()).nlargest(15, "a").to_string())
    # trend checks: count of points at which each claim of the paper holds
    T = {}
    pv = lambda q, sw: df[df.sweep == sw].pivot_table(index=[sw, "n"], columns="kind", values=q)
    for q, sign in (("neff", "H>V"), ("B", "V>H"), ("loss", "H>V"), ("r", "V>H")):
        for sw in ("lam", "eta"):
            t = pv(q, sw); ok = t.H > t.V if sign == "H>V" else t.V > t.H
            T[f"{q} {sign} [{sw}]"] = (int(ok.sum()), len(ok), [f"{i[0]}/{i[1]}" for i in ok.index[~ok]])
    for q, sw, up in (("neff","lam",0),("neff","eta",0),("B","lam",1),("B","eta",0),("loss","eta",0),("r","lam",1),("r","eta",1)):
        a = b = 0; bad = []
        for (k, n), g in df[df.sweep == sw].groupby(["kind", "n"]):
            d = np.diff(g.sort_values(sw)[q]); ok = d > 0 if up else d < 0
            a += int(ok.sum()); b += len(ok); bad += [f"{k}/{n}/{v}" for v, o in zip(g.sort_values(sw)[sw][1:], ok) if not o]
        T[f"{q} {'increases' if up else 'decreases'} with {sw}"] = (a, b, bad)
    for q, up in (("neff", 1), ("loss", 0), ("r", 1), ("B", 0)):
        a = b = 0; bad = []
        for (sw, k, l, e), g in df.groupby(["sweep", "kind", "lam", "eta"]):
            d = np.diff(g.sort_values("n")[q]); ok = (d > 0 if up else d < 0).all(); a += int(ok); b += 1
            if not ok: bad.append(f"{sw}/{k}/{l}/{e}")
        T[f"{q} {'increases' if up else 'decreases'} with analyte index"] = (a, b, bad)
    json.dump(T, open(R + "trend_checks.json", "w"), indent=1)
    for k, v in T.items(): print(f"{k}: {v[0]}/{v[1]}", "exceptions:" if v[2] else "", v[2][:12])

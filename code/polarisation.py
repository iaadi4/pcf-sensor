"""Does 'V better than H' survive when each fibre is judged in both polarisations?"""
import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
R = "../results/"
d = pd.read_csv(R + "results_main.csv"); d = d[d.cleanB]
rows = []
for sw in ("lam", "eta"):
    for (n, p), g in d[d.sweep == sw].groupby(["n", sw]):
        if set(g.kind) != {"V", "H"}: continue
        v, h = g[g.kind == "V"].iloc[0], g[g.kind == "H"].iloc[0]
        rows.append(dict(sweep=sw, n=n, at=p, Vx=v.r, Vy=v.r_y, Hx=h.r, Hy=h.r_y, LVx=v.loss, LVy=v.loss_y, LHx=h.loss, LHy=h.loss_y, BV=v.B, BH=h.B))
t = pd.DataFrame(rows)
t["best_r_V"], t["best_r_H"] = t[["Vx", "Vy"]].max(axis=1), t[["Hx", "Hy"]].max(axis=1)
t["dbest_r"] = t.best_r_V - t.best_r_H; t["dxx"] = t.Vx - t.Hx; t["dyy"] = t.Vy - t.Hy
t["bestL_V"], t["bestL_H"] = t[["LVx", "LVy"]].min(axis=1), t[["LHx", "LHy"]].min(axis=1)
t["Lratio_best"] = t.bestL_H / t.bestL_V
t.to_csv(R + "polarisation_check.csv", index=False)
for sw, g in t.groupby("sweep"):
    print(sw, "N", len(g), "| x vs x: V>H", (g.dxx > 0).sum(), f"diff {g.dxx.min():.2f}..{g.dxx.max():.2f}",
          "| y vs y: V>H", (g.dyy > 0).sum(), f"diff {g.dyy.min():.2f}..{g.dyy.max():.2f}",
          "| best vs best: V>H", (g.dbest_r > 0).sum(), f"diff {g.dbest_r.min():.3f}..{g.dbest_r.max():.3f}, mean {g.dbest_r.mean():.3f}",
          "| best pol V is x", (g.Vx > g.Vy).sum(), "best pol H is y", (g.Hy > g.Hx).sum(),
          "| best loss H/V", f"{g.Lratio_best.min():.2f}..{g.Lratio_best.max():.2f}", "V lower:", (g.Lratio_best > 1).sum(), "| B V>H", (g.BV > g.BH).sum())
print(t[np.isclose(t["at"], 1.0) | np.isclose(t["at"], 1.5)].round(4).to_string())
fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.7))
for A, sw, xl in zip(ax, ("lam", "eta"), ("Wavelength (µm)", "Ellipticity η")):
    g = t[(t.sweep == sw) & (t.n == 1.33)]
    for c, col, ls, l in (("Vx", "#0E7C86", "-", "V, x-pol (paper)"), ("Vy", "#0E7C86", ":", "V, y-pol"), ("Hx", "#D95F02", "--", "H, x-pol (paper)"), ("Hy", "#D95F02", "-.", "H, y-pol")):
        A.plot(g["at"], g[c], ls, color=col, lw=2, label=l)
    A.set(xlabel=xl, ylabel="Relative sensitivity r (%)", title="η = 0.7" if sw == "lam" else "λ = 1 µm"); A.grid(alpha=.25)
ax[0].legend(); fig.suptitle("Sensitivity in both polarisations, n = 1.33 (well-confined points)", fontsize=11)
fig.tight_layout(); fig.savefig(R + "figures/polarisation.png", dpi=200)

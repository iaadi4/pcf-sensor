"""Extensions: dispersive silica, water 1.333 vs 1.33, index sensitivity of n_eff."""
import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from analyse import tidy
R = "../results/"
m = tidy(pd.read_csv(R+"raw_main.csv")); e = tidy(pd.read_csv(R+"raw_ext.csv"))
e.to_csv(R+"results_extension.csv", index=False)
s = e[e.mat == "sellmeier"]; m = m[m.sweep == "lam"]
COL = {1.33: "#1f77b4", 1.354: "#d95f02", 1.366: "#2a9d4a"}
fig, ax = plt.subplots(1, 3, figsize=(14, 4.4))
for A, q, lab in zip(ax, ("neff", "B", "r"), ("Effective index", "Birefringence (×10⁻³)", "Sensitivity r (%)")):
    for n in COL:
        for d, ls, t in ((m, "-", "n = 1.45"), (s, ":", "Sellmeier")):
            c = d[(d.kind == "V") & (d.n == n) & d.cleanB]
            A.plot(c.lam, c[q]*(1e3 if q=="B" else 1), ls, color=COL[n], label=f"{n}, {t}")
    A.set(xlabel="Wavelength (µm)", ylabel=lab); A.grid(alpha=.25)
ax[0].legend(fontsize=7); fig.suptitle("V-PCF, η = 0.7: constant silica index (paper) vs dispersive silica (well-confined points)", fontsize=10)
fig.tight_layout(); fig.savefig(R+"figures/ext_sellmeier.png", dpi=200)
j = s.merge(m, on=["kind", "n", "lam"], suffixes=("_s", "_c"))
j = j[j.cleanB_s & j.cleanB_c]
for q in ("neff", "B", "r", "loss"): j["d_"+q] = 100*(j[q+"_s"]/j[q+"_c"]-1)
print(j[["kind","n","lam","neff_s","neff_c","B_s","B_c","r_s","r_c","loss_s","loss_c","d_r","d_B","d_loss"]].round(5).to_string())
w = e[(e.mat == "const") & (e.n == 1.333)].merge(m[(m.kind == "V") & (m.n == 1.33)], on="lam", suffixes=("_w", "_0"))
print(w[["lam","neff_w","neff_0","r_w","r_0","B_w","B_0","loss_w","loss_0","core_w","core_0"]].round(5).to_string())
# dn_eff/dn between 1.354 and 1.366 at lam=1, eta=0.7
for k in "VH":
    t = m[(m.kind == k) & np.isclose(m.lam, 1.0)].set_index("n").neff
    print(k, "dneff/dn", (t[1.366]-t[1.354])/.012, (t[1.354]-t[1.33])/.024)
print(m[np.isclose(m.lam, 1.0)|np.isclose(m.lam,1.5)][["kind","n","lam","neff","B","loss","r"]].to_string())

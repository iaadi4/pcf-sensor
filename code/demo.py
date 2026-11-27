"""Live demo: solves one point of the paper and shows the result (about 1 minute).

    python demo.py            V-PCF, water (n = 1.33), 1 um
    python demo.py H 1.366    H-PCF, n = 1.366
Paper values for V, 1.33 are read from its plots (Figs. 2, 4, 5b, 6).
"""
import os, sys, time
os.environ.setdefault("OMP_NUM_THREADS", "4")
import numpy as np, matplotlib
import matplotlib.pyplot as plt, matplotlib.tri as mtri
from matplotlib.patches import Ellipse
from pcf_fem import Design, fundamental

kind = sys.argv[1].upper() if len(sys.argv) > 1 else "V"
n = float(sys.argv[2]) if len(sys.argv) > 2 else 1.33
lam, eta = 1.0, 0.7
d = Design(kind=kind, eta=eta)
print(f"\n{kind}-PCF, analyte n = {n}, wavelength {lam} um, ellipticity {eta}")
print("36 air holes, 7 liquid holes, quarter model with PML\n")
t = time.time()
mx = fundamental(d, lam, n, "x", guess=1.405 if n < 1.34 else 1.413, nev=8)
print(f"x-polarised mode solved in {time.time()-t:.1f} s")
t = time.time()
my = fundamental(d, lam, n, "y", guess=mx.neff.real + 0.002, nev=8)
print(f"y-polarised mode solved in {time.time()-t:.1f} s\n")
B = abs(mx.neff.real - my.neff.real)
rows = [("Effective index (x)", f"{mx.neff.real:.5f}", "1.404"),
        ("Birefringence", f"{B:.3e}", "2.58e-03"),
        ("Confinement loss (dB/m)", f"{mx.loss:.4f}", "0.044"),
        ("Sensitivity r (%)", f"{mx.r(n):.2f}", "20.59"),
        ("Power in liquid f (%)", f"{100*mx.f:.2f}", "-")]
show_paper = kind == "V" and abs(n - 1.33) < 1e-9
print(f"{'Quantity':26s}{'This work':>12s}" + (f"{'Paper':>10s}" if show_paper else ""))
for a, b, c in rows:
    print(f"{a:26s}{b:>12s}" + (f"{c:>10s}" if show_paper else ""))

e, _ = mx.basis.interpolate(mx.x)
X = mx.basis.global_coordinates().value
E = np.sqrt(abs(e[0])**2 + abs(e[1])**2).ravel(); x, y = X[0].ravel(), X[1].ravel()
s = (x < 4.5) & (y < 4.5); x, y, E = x[s], y[s], E[s] / E[s].max()
fig, ax = plt.subplots(figsize=(7, 6))
c = ax.tricontourf(mtri.Triangulation(np.r_[x, -x, x, -x], np.r_[y, y, -y, -y]), np.r_[E, E, E, E], levels=np.linspace(0, 1, 26), cmap="viridis")
for hx, hy, a, b, tg in d.holes():
    ax.add_patch(Ellipse((hx, hy), 2*a, 2*b, fc="none", ec="w", lw=1))
ax.set(xlim=(-4, 4), ylim=(-4, 4), aspect="equal", xlabel="x (µm)", ylabel="y (µm)",
       title=f"{kind}-PCF, n = {n}: n_eff = {mx.neff.real:.5f}, r = {mx.r(n):.2f} %")
fig.colorbar(c, label="|E| (normalised)"); fig.tight_layout()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", f"demo_{kind}_{n}.png")
fig.savefig(out, dpi=150); print(f"\nField plot saved to {os.path.normpath(out)}")
if matplotlib.get_backend().lower() != "agg":
    plt.show()

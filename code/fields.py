"""Fig. 3: field maps of the x-polarised LP01 mode, plus Fig. 1 geometry."""
import os; os.environ["OMP_NUM_THREADS"] = "2"
import numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import matplotlib.tri as mtri
import pcf_fem as P
from pcf_fem import Design, fundamental, AIR

fig, ax = plt.subplots(1, 2, figsize=(10, 4.9))
for A, k in zip(ax, "VH"):
    for x, y, rx, ry, t in Design(kind=k).holes():
        A.add_patch(Ellipse((x, y), 2*rx, 2*ry, fc="white" if t == AIR else "#2a78b8", ec="k", lw=.8))
    A.set(xlim=(-9.5, 9.5), ylim=(-9, 9), aspect="equal", facecolor="#e8eef3",
          xlabel="x (µm)", ylabel="y (µm)", title=f"({'ab'['VH'.index(k)]}) {k}-PCF, η = 0.7")
fig.tight_layout(); fig.savefig("../results/figures/fig1_geometry.png", dpi=200)

cases = [("V", .7, 1.33), ("H", .7, 1.33), ("V", .7, 1.366), ("V", 1., 1.366)]
fig, ax = plt.subplots(2, 2, figsize=(9.6, 9))
for A, (k, eta, na), tag in zip(ax.flat, cases, "abcd"):
    d = Design(kind=k, eta=eta); P._cache.clear()
    q = fundamental(d, 1.0, na, "x", guess=1.405, nev=6)
    e, ez = q.basis.interpolate(q.x)
    X = q.basis.global_coordinates().value
    E = np.sqrt(abs(e[0])**2 + abs(e[1])**2).ravel()
    x, y = X[0].ravel(), X[1].ravel()
    s = (x < 5) & (y < 5); x, y, E = x[s], y[s], E[s]/E[s].max()
    # mirror the quarter solution
    xx = np.r_[x, -x, x, -x]; yy = np.r_[y, y, -y, -y]; EE = np.r_[E, E, E, E]
    c = A.tricontourf(mtri.Triangulation(xx, yy), EE, levels=np.linspace(0, 1, 26), cmap="viridis")
    for hx, hy, rx, ry, t in d.holes():
        A.add_patch(Ellipse((hx, hy), 2*rx, 2*ry, fc="none", ec="w", lw=.7))
    A.set(xlim=(-4.5, 4.5), ylim=(-4.5, 4.5), aspect="equal", xlabel="x (µm)", ylabel="y (µm)",
          title=f"({tag}) {k}-PCF, η = {eta}, n = {na}\nn_eff = {q.neff.real:.5f}")
fig.colorbar(c, ax=ax, shrink=.6, label="|E_t| (normalised)")
fig.savefig("../results/figures/fig3_fields.png", dpi=200, bbox_inches="tight")

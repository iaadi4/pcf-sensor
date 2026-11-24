"""Solver checks: (1) exact step-index fibre, (2) mesh/PML convergence, (3) geometry reading."""
import numpy as np, json, sys
from dataclasses import replace
from scipy.special import jv, kv, jvp, kvp
from scipy.optimize import brentq
import pcf_fem as P
from pcf_fem import Design, fundamental, AIR, ANALYTE

out = {}
# ---- (1) step-index: air-clad... glass rod (n1=1.45) radius a in n2 medium, lam=1
def exact(n1, n2, a, lam, l=1):
    k = 2*np.pi/lam
    def F(n):
        u = a*k*np.sqrt(n1**2-n**2); w = a*k*np.sqrt(n**2-n2**2)
        J = jvp(l,u)/(u*jv(l,u)); K = kvp(l,w)/(w*kv(l,w))
        return (J+K)*(n1**2*J+n2**2*K) - (l*n)**2*(1/u**2+1/w**2)**2
    ns = np.linspace(n1-1e-6, n2+1e-6, 40000); v = np.array([F(x) for x in ns])
    roots = [brentq(F, ns[i+1], ns[i]) for i in range(len(ns)-1)
             if v[i]*v[i+1] < 0 and abs(v[i]) < 50 and abs(v[i+1]) < 50]
    return roots[0]

class Rod(Design):
    """one 'analyte' circle of radius 1 um standing for the rod; host index from n_si."""
    def holes(self):
        return [(0, 0, 1.0, 1.0, ANALYTE)]
# window() uses holes; widen the gap so that the bound mode has decayed
rod = Rod(gap=4.0)
for n1, n2 in ((1.45, 1.40), (1.45, 1.00)):
    ex = exact(n1, n2, 1.0, 1.0)
    row = {}
    for h in (2.0, 1.0, 0.7):
        r = replace(rod, h=h)
        P._cache.clear()
        q = {p: fundamental(r, 1.0, n1, p, guess=ex, nev=6, n_si=n2) for p in "xy"}
        row[h] = [abs(q[p].neff.real-ex) for p in "xy"]
    out[f"step_{n1}_{n2}"] = dict(exact=ex, err={str(k): v for k, v in row.items()})
    print("step-index", n1, n2, "exact", ex, {k: [f"{e:.1e}" for e in v] for k, v in row.items()}, flush=True)

# ---- (2) convergence, V and H, worst-case (H 1.33) and a low-loss case
for lbl, d, lam, na in (("V 0.7 1.33 lam1", Design(), 1.0, 1.33),
                        ("H 0.7 1.33 lam1", Design(kind="H"), 1.0, 1.33),
                        ("V 1.0 1.366 lam1", Design(eta=1.0), 1.0, 1.366),
                        ("V 0.7 1.366 lam1.7", Design(), 1.7, 1.366)):
    for name, dd in (("h=1.5", replace(d, h=1.5)), ("h=1", d), ("h=0.75", replace(d, h=.75)),
                     ("PML 4um", replace(d, t_pml=4.)), ("PML s=10", replace(d, s_pml=10.)),
                     ("gap 2um", replace(d, gap=2.))):
        P._cache.clear()
        x, y = (fundamental(dd, lam, na, p, guess=1.405 if lam == 1 else 1.387, nev=8) for p in "xy")
        rec = dict(neff=x.neff.real, B=abs(x.neff.real-y.neff.real), loss=x.loss, r=x.r(na))
        out[f"{lbl} | {name}"] = rec
        print(lbl, name, f"n={rec['neff']:.7f} B={rec['B']:.6e} L={rec['loss']:.3e} r={rec['r']:.3f}", flush=True)

# ---- (3) semi-axis vs full-axis interpretation (V, 1.33, lam=1; paper: n~1.4045, r~20.6, B~2.6e-3)
for name, d in (("all semi-axes", Design()),
                ("all full axes", Design(da=.5, ds=.2, dc=.1)),
                ("cladding semi, core full", Design(ds=.2, dc=.1)),
                ("cladding full, core semi", Design(da=.5))):
    P._cache.clear()
    x, y = (fundamental(d, 1.0, 1.33, p, guess=1.43 if d.da < 1 or d.ds < .4 else 1.405, nev=14) for p in "xy")
    rec = dict(neff=x.neff.real, B=abs(x.neff.real-y.neff.real), loss=x.loss, r=x.r(1.33), core=x.core)
    out["geom | " + name] = rec
    print(name, rec, flush=True)
json.dump(out, open("../results/validation.json", "w"), indent=1)

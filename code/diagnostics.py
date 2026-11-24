"""Explains the outliers: (a) mode mixing near 0.8 um, (b) round-off floor of confinement loss, (c) loss checks."""
import os; os.environ["OMP_NUM_THREADS"] = os.environ["OPENBLAS_NUM_THREADS"] = "1"
import numpy as np, pandas as pd, sys
from dataclasses import replace
from multiprocessing import Pool
import pcf_fem as P, scipy.sparse.linalg as spl
from pcf_fem import Design, solve

def scan(a):
    kind, lam, g, h = a
    P._cache.clear()
    ms = sorted(solve(Design(kind=kind, h=h), lam, 1.33, "x", g, nev=14), key=lambda q: -q.core)[:3]
    return [dict(kind=kind, lam=lam, h=h, rank=i, neff=q.neff.real, core=q.core, loss=q.loss, r=q.r(1.33)) for i, q in enumerate(ms)]

def chk(a):
    lbl, d, lam, na, g = a
    P._cache.clear()
    q = max(solve(d, lam, na, "x", g, nev=8), key=lambda m: m.core)
    return dict(case=lbl, lam=lam, n=na, kind=d.kind, eta=d.eta, h=d.h, neff=q.neff.real, loss=q.loss, r=q.r(na), core=q.core)

def naive(a):
    kind, eta, na = a
    P._cache.clear(); res = []
    for s in (0.0, 1e-4, 2e-4):        # tiny shift changes: an honest eigenvalue must not care
        g = 1.4047 + s if na == 1.354 else (1.3995 + s if na == 1.33 else 1.4077 + s)
        q = max(solve(Design(kind=kind, eta=eta), 1.0, na, "x", g, nev=6), key=lambda m: m.core)
        res.append((q.loss, q.naive))
    return dict(kind=kind, eta=eta, n=na, identity=[f"{x[0]:.3e}" for x in res], eigenvalue=[f"{x[1]:.3e}" for x in res])

if __name__ == "__main__":
    df = pd.read_csv("../results/raw_main.csv")
    q = df[(df.sweep == "lam") & (df.n == 1.33) & (df.pol == "x")]
    with Pool(2, maxtasksperchild=4) as pool:
        L = np.round(np.arange(0.70, 1.001, 0.01), 3)
        jobs = [("V", l, 1.4122 + 0.0343*(0.79-l), 1.0) for l in L]
        s = pd.DataFrame(sum(pool.map(scan, jobs, chunksize=1), []))
        s.to_csv("../results/diag_scan_V133.csv", index=False)
        print(s[s["rank"] < 2].pivot(index="lam", columns="rank", values=["neff", "core", "loss", "r"]).round(5).to_string())
        c = pool.map(chk, [("V0.9 " + str(h), Design(h=h), .9, 1.33, 1.408) for h in (1., .7)] +
            [("V0.9 pml4/gap2", Design(gap=2., t_pml=4.), .9, 1.33, 1.408)] +
            [(f"V1.5 {n} h{h}", Design(h=h), 1.5, n, g) for n, g in ((1.354, 1.392), (1.366, 1.395)) for h in (1., .7)], chunksize=1)
        c = pd.DataFrame(c); c.to_csv("../results/diag_checks.csv", index=False); print(c.to_string())
        n = pool.map(naive, [(k, e, v) for k in "VH" for e, v in ((1.0, 1.33), (1.0, 1.354), (1.0, 1.366))], chunksize=1)
        n = pd.DataFrame(n); n.to_csv("../results/diag_roundoff.csv", index=False); print(n.to_string())

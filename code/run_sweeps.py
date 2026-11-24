"""All data for Figs 2,4,5,6 (wavelength and ellipticity sweeps) plus the extension runs."""
import os
os.environ["OMP_NUM_THREADS"] = os.environ["OPENBLAS_NUM_THREADS"] = "1"
import sys, numpy as np, pandas as pd, gc
from multiprocessing import Pool
import pcf_fem as P

def sellmeier(l):   # fused silica, Malitson 1965
    B = (0.6961663, 0.4079426, 0.8974794); C = (0.0684043, 0.1162414, 9.896161)
    return np.sqrt(1 + sum(b*l*l/(l*l-c*c) for b, c in zip(B, C)))

LAMS = np.round(np.arange(0.7, 1.701, 0.05), 3)
ETAS = np.round(np.arange(0.6, 1.001, 0.05), 3)

def chain(task):
    """One curve: march outwards from the middle, using the previous n_eff as the shift."""
    sweep, kind, na, pol, points, mat = task
    rows = []
    pts = list(points)
    mid = min(range(len(pts)), key=lambda i: abs(pts[i] - (1.1 if sweep == "lam" else 0.8)))
    start = None
    for seq in (range(mid, len(pts)), range(mid-1, -1, -1)):
        hist = [] if start is None else [start]
        for i in seq:
            p = pts[i]
            lam, eta = (p, 0.7) if sweep == "lam" else (1.0, p)
            nsi = sellmeier(lam) if mat == "sellmeier" else 1.45
            # linear extrapolation of n_eff for the shift
            if len(hist) >= 2:
                (p1, n1), (p2, n2) = hist[-2:]
                g = n2 + (n2-n1)/(p2-p1)*(p-p2)
            elif hist:
                g = hist[-1][1] + (0.035*(hist[-1][0]-p) if sweep == "lam" else 0)
            else:
                g = 1.405 + (nsi-1.45)
            P._cache.clear()
            ms = P.solve(P.Design(kind=kind, eta=eta), lam, na, pol, g, nev=12, n_si=nsi)
            ms.sort(key=lambda q: -q.core)
            a, b = ms[0], ms[1]
            hist.append((p, a.neff.real))
            if start is None: start = hist[0]
            rows.append(dict(sweep=sweep, mat=mat, kind=kind, n=na, pol=pol, lam=lam, eta=eta,
                             neff=a.neff.real, neff_im=a.neff.imag, loss=a.loss, r=a.r(na),
                             core=a.core, neff2=b.neff.real, core2=b.core, loss2=b.loss, r2=b.r(na)))
            del ms; gc.collect()
    return rows

if __name__ == "__main__":
    which = sys.argv[1]
    if which == "main":
        tasks = [("lam", k, n, p, LAMS, "const") for k in "VH" for n in (1.33, 1.354, 1.366) for p in "xy"]
        tasks += [("eta", k, n, p, ETAS, "const") for k in "VH" for n in (1.33, 1.354, 1.366) for p in "xy"]
    else:
        L = LAMS[::2]
        tasks = [("lam", k, n, p, L, "sellmeier") for k in "VH" for n in (1.33, 1.354, 1.366) for p in "xy"]
        tasks += [("lam", "V", 1.333, p, L, "const") for p in "xy"]
    rows = []
    with Pool(2, maxtasksperchild=1) as pool:
        for k, r in enumerate(pool.imap_unordered(chain, tasks, chunksize=1)):
            rows += r
            print(f"{k+1}/{len(tasks)} {r[0]['sweep']} {r[0]['mat']} {r[0]['kind']} {r[0]['n']} {r[0]['pol']}", flush=True)
            pd.DataFrame(rows).to_csv(f"../results/raw_{which}.csv", index=False)

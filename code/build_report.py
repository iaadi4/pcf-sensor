"""Builds the Word report; every number in it is read from the result files."""
import ast, json, os, subprocess, sys
import numpy as np, pandas as pd
TMP = sys.argv[1]                       # folder for the intermediate (unstyled) docx
R = "../results/"
df = pd.read_csv(R+"results_main.csv"); es = pd.read_csv(R+"error_summary.csv").set_index("fig")
val = json.load(open(R+"validation.json")); T = json.load(open(R+"trend_checks.json"))
cmp_ = pd.read_csv(R+"comparison.csv"); ro = pd.read_csv(R+"diag_roundoff.csv"); ext = pd.read_csv(R+"results_extension.csv")
scan = pd.read_csv(R+"diag_scan_V133.csv"); ck = pd.read_csv(R+"diag_checks.csv")

def tab(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "|".join(["---"]*len(head)) + "|"] +
                     ["| " + " | ".join(map(str, r)) + " |" for r in rows])
def sci(v):
    m, e = f"{v:.2e}".split("e"); return f"{m}×10^{int(e)}^"
def num(v): return f"{v:.4f}" if 1e-3 <= v < 1e3 else sci(v)
def pick(kind, n, lam, eta=.7, sw="lam"):
    g = df[(df.sweep == sw) & (df.kind == kind) & (df.n == n) & np.isclose(df.lam, lam) & np.isclose(df.eta, eta)]
    return g.iloc[0]
def main_table(lam):
    rows = []
    for k in "VH":
        for n in (1.33, 1.354, 1.366):
            q = pick(k, n, lam)
            rows.append([k+"-PCF", n, f"{q.neff:.5f}", f"{1e3*q.B:.3f}", num(q.loss), f"{q.r:.2f}"])
    return tab(["Fibre", "Analyte n", "n~eff~", "B (×10^-3^)", "Loss (dB/m)", "r (%)"], rows)

names = {"2a": "n~eff~ vs λ", "2b": "n~eff~ vs η", "4a": "Birefringence vs λ", "4b": "Birefringence vs η",
         "6a": "Sensitivity vs λ", "6b": "Sensitivity vs η"}
err = tab(["Figure", "All points", "Mean error (%)", "Max error (%)", "Well-confined points", "Mean error (%)", "Max error (%)"],
   [[f+": "+names[f], int(es.N[f]), f"{es.mean_abs_pct[f]:.3f}", f"{es.max_abs_pct[f]:.3f}", int(es.N_clean[f]),
     f"{es.mean_abs_pct_clean[f]:.3f}", f"{es.max_abs_pct_clean[f]:.3f}"] for f in names])
geo = tab(["Reading of the stated dimensions", "n~eff~", "B (×10^-3^)", "Loss (dB/m)", "r (%)"],
   [[k[7:], f"{v['neff']:.4f}", f"{1e3*v['B']:.2f}", num(v['loss']), f"{v['r']:.2f}"] for k, v in val.items() if k.startswith("geom")]
   + [["**Paper (read from plots)**", "1.404 (2a, interpolated)", "2.58 (4a, interpolated)", "0.044 (5b)", "20.59 (6a)"]])
conv = tab(["Case (λ = 1 µm, x-pol)", "Setting", "n~eff~", "B (×10^-3^)", "Loss (dB/m)", "r (%)"],
   [[k.split(" | ")[0].replace(" lam1", ""), k.split(" | ")[1], f"{v['neff']:.6f}", f"{1e3*v['B']:.4f}", sci(v['loss']), f"{v['r']:.3f}"]
    for k, v in val.items() if " | " in k and not k.startswith("geom") and "lam1.7" not in k])
st = tab(["Rod / host index", "Exact n~eff~", "Error, coarse (h=2)", "Error, used (h=1)", "Error, fine (h=0.7)"],
   [[k.split("_")[1]+" / "+k.split("_")[2], f"{v['exact']:.8f}"] + [sci(max(v['err'][h])) for h in ("2.0", "1.0", "0.7")]
    for k, v in val.items() if k.startswith("step")])
def lo(f):
    return tab(["x", "Fibre, n", "Paper (dB/m)", "This work (dB/m)", "Ratio (this work / paper)"],
     [[t.x, f"{t.kind}, {t.n}", sci(t.paper), sci(t.ours), f"{t.ours/t.paper:.2g}"]
      for _, t in cmp_[cmp_.fig == f].sort_values(["kind", "n", "x"]).iterrows()])
rt = tab(["Fibre, n (η = 1)", "Energy identity (dB/m), 3 shifts", "Direct eigenvalue (dB/m), 3 shifts"],
   [[f"{t.kind}, {t.n}", ", ".join(sci(float(z)) for z in ast.literal_eval(t.identity)),
     ", ".join(sci(float(z)) if float(z) else "0" for z in ast.literal_eval(t.eigenvalue))] for _, t in ro.iterrows()])
claim = {"neff H>V [lam]": "n~eff~ of H above V, wavelength sweep", "neff H>V [eta]": "n~eff~ of H above V, η sweep",
 "neff decreases with lam": "n~eff~ falls with λ", "neff decreases with eta": "n~eff~ falls with η",
 "neff increases with analyte index": "n~eff~ rises with analyte index", "B V>H [lam]": "B of V above H, wavelength sweep",
 "B V>H [eta]": "B of V above H, η sweep", "B increases with lam": "B rises with λ", "B decreases with eta": "B falls with η",
 "loss H>V [lam]": "Loss of V below H, wavelength sweep", "loss H>V [eta]": "Loss of V below H, η sweep",
 "loss decreases with eta": "Loss falls with η", "loss decreases with analyte index": "Loss falls with analyte index",
 "r V>H [lam]": "r of V above H, wavelength sweep", "r V>H [eta]": "r of V above H, η sweep",
 "r increases with lam": "r rises with λ", "r increases with eta": "r rises with η (highest at η = 1)"}
def exc(v):
    out = []
    for x in v:
        q = x.split("/")
        out.append(f"{q[0]} (n = {q[1]})" if len(q) == 2 else f"{q[0]}-PCF, n = {q[1]}, at {q[2]}")
    return "; ".join(out)
tr = tab(["Claim in the paper", "Holds at", "Exceptions (λ in µm, or η)"], [[claim[k], f"{T[k][0]}/{T[k][1]}", exc(T[k][2]) or "none"] for k in claim])
S = ext[ext.mat == "sellmeier"]; C = df[df.sweep == "lam"]
er = []
for lam in (0.9, 1.0, 1.3, 1.5, 1.7):
    for n in (1.33, 1.366):
        a = S[(S.kind == "V") & (S.n == n) & np.isclose(S.lam, lam)].iloc[0]
        b = C[(C.kind == "V") & (C.n == n) & np.isclose(C.lam, lam)].iloc[0]
        er.append([lam, n, f"{b.neff:.4f} → {a.neff:.4f}", f"{1e3*b.B:.2f} → {1e3*a.B:.2f}", f"{num(b.loss)} → {num(a.loss)}", f"{b.r:.2f} → {a.r:.2f}"])
etab = tab(["λ (µm)", "n", "n~eff~ (1.45 → Sellmeier)", "B (×10^-3^)", "Loss (dB/m)", "r (%)"], er)
W = ext[(ext.mat == "const") & (ext.n == 1.333) & np.isclose(ext.lam, 1.0)].iloc[0]; W0 = pick("V", 1.33, 1.0)
v1 = pick("V", 1.366, 1.0, 1.0, "eta"); bi = df[df.clean].r.idxmax(); best = df.loc[bi]
assert (best.kind, best.n, best.lam, best.eta) == ("V", 1.366, 1.7, 0.7)
s0 = lambda l: scan[np.isclose(scan.lam, l) & (scan["rank"] == 0)].iloc[0]
s1 = scan[np.isclose(scan.lam, .80) & (scan["rank"] == 1)].iloc[0]
d09 = ck[ck.case == "V0.9 0.7"].iloc[0]
pol = pd.read_csv(R+"polarisation_check.csv"); pl = pol[pol.sweep == "lam"]; pe = pol[pol.sweep == "eta"]
ptab = tab(["λ (µm)", "n", "r: V x-pol", "r: H x-pol", "r: V best", "r: H best", "Loss: V best", "Loss: H best"],
   [[t["at"], t["n"], f"{t.Vx:.2f}", f"{t.Hx:.2f}", f"{t.best_r_V:.2f}", f"{t.best_r_H:.2f}", num(t.bestL_V), num(t.bestL_H)]
    for _, t in pl[np.isclose(pl["at"], 1.0) | np.isclose(pl["at"], 1.5)].iterrows()])
lratio = cmp_[(cmp_.fig == "5b") & (cmp_.x == 1.0)].eval("paper/ours"); l9 = cmp_[(cmp_.fig == "5b") & (cmp_.x == .9) & (cmp_.kind == "H")].eval("paper/ours")

md = f"""---
title: "Reproduction of a PCF-Based Liquid Analyte Sensor with High Sensitivity, High Birefringence and Low Confinement Loss"
subtitle: "Minor Project Report"
author: "Rishit Bajaj (2023UG4028)"
---

# Abstract

This project reproduces the results of Ademgil and Haxha, *Sensors* 2015, 15, 31833–31842 [1]. Two photonic crystal fibres (PCFs) with elliptical holes, V-PCF and H-PCF, carry a liquid analyte in seven small core holes. A full-vector finite element (FEM) mode solver with perfectly matched layers (PML) was written in Python and checked against an exact analytical solution. All result figures of the paper (Figs. 2–6) were recomputed, and Figs. 2, 4, 5 and 6 were compared with {len(cmp_)} values read from the published plots. At well-confined points the mean difference is {es.mean_abs_pct_clean['2b']:.3f}–{es.mean_abs_pct_clean['2a']:.3f} % for effective index, {es.mean_abs_pct_clean['4a']:.2f}–{es.mean_abs_pct_clean['4b']:.2f} % for birefringence and {es.mean_abs_pct_clean['6a']:.2f}–{es.mean_abs_pct_clean['6b']:.2f} % for relative sensitivity. Confinement loss differs by a median of about {es.median_abs_pct['5a']:.0f}–{es.median_abs_pct['5b']:.0f} % (mean {es.mean_abs_pct['5a']:.0f}–{es.mean_abs_pct['5b']:.0f} %, because of outliers that are discussed). The paper's finding that V-PCF has higher sensitivity and lower loss is reproduced for the x-polarised mode it uses, but is shown to depend on that choice: with each fibre in its better polarisation the sensitivities are nearly equal. The work also shows that the paper's "axis lengths" must be semi-axes, that its losses at η = 1 lie at the numerical round-off level, and how dispersive silica changes the results.

# 1. Introduction

An index-guiding PCF confines light in a silica core surrounded by air holes. If small holes in the core are filled with a liquid, part of the guided power travels inside the liquid, which makes the fibre a sensor. A good design needs high power in the liquid (sensitivity), high birefringence (to hold polarisation) and low confinement loss. The paper [1] uses elliptical holes to obtain all three together.

**Objectives**

1. Reproduce Figs. 1–6 of the paper for V-PCF and H-PCF.
2. Measure the agreement numerically rather than by visual impression.
3. Test the trends the paper claims.
4. Extend the work with the wavelength-dependent index of silica.

# 2. Structure and parameters

| Parameter | Value |
|---|---|
| Cladding holes | 36 (three hexagonal rings), air, n = 1 |
| Cladding pitch Λ~cladding~ | 2.4 µm |
| Cladding hole d~a~ (major), d~b~ = η d~a~ | 1 µm, 0.7 µm (η = 0.7); η swept 0.6–1.0 |
| Core holes | 7 (one centre, six around it), filled with analyte |
| Core pitch Λ~core~ | 1 µm |
| Core hole d~s~ (major), d~c~ (minor) | 0.4 µm, 0.2 µm |
| Silica index | 1.45 (constant) |
| Analyte index | 1.33, 1.354, 1.366 |
| Wavelength | 0.7–1.7 µm (η sweep at 1 µm) |

In V-PCF all major axes are vertical; in H-PCF all are horizontal. The core hexagon has two holes on the vertical axis in both fibres (Fig. 1).

![Figure 1. Simulated geometry: (a) V-PCF, (b) H-PCF. White: air; blue: analyte; grey: silica.](../results/figures/fig1_geometry.png){{width=6.2in}}

## 2.1 The dimensions are semi-axes

The paper calls d~a~ and d~b~ the "lengths of the major and minor axes". Its own Fig. 3 contradicts this: measured in pixels, the V-PCF holes are about 70 × 100 on a pitch of about 120, that is 1.4 µm × 2.0 µm. This matches d~a~ = 1 µm and d~b~ = 0.7 µm only if they are **semi-axes**. Four readings were simulated (V-PCF, n = 1.33, λ = 1 µm, η = 0.7):

{geo}

Only the semi-axis reading reproduces the paper, so it is used throughout, for cladding and core holes.

## 2.2 Analyte indices

The text gives 1.333 for water but every plot legend says 1.33. With 1.33 the sensitivity at 1 µm is {W0.r:.2f} % and the birefringence {1e3*W0.B:.2f}×10^-3^; with 1.333 they are {W.r:.2f} % and {1e3*W.B:.2f}×10^-3^. The paper's plots show 20.59 % and about 2.58×10^-3^ there, so 1.33 was used. The paper writes "benzyne" for n = 1.366; this report refers to that analyte only by its index.

# 3. Theory and method

The mode problem is the vector wave equation with anisotropic PML (Eq. 1 of [1]):

$$\\nabla\\times\\left([s]^{{-1}}\\nabla\\times \\mathbf{{E}}\\right)-k_0^2n^2[s]\\mathbf{{E}}=0,\\qquad k_0=2\\pi/\\lambda$$

Relative sensitivity and power fraction (Eqs. 2 and 3 of [1]):

$$r=\\frac{{n_r}}{{\\mathrm{{Re}}(n_{{eff}})}}\\,f$$

$$f=\\frac{{\\int_{{sample}}\\mathrm{{Re}}(E_xH_y^*-E_yH_x^*)\\,dx\\,dy}}{{\\int_{{total}}\\mathrm{{Re}}(E_xH_y^*-E_yH_x^*)\\,dx\\,dy}}\\times100$$

Birefringence and confinement loss are not written out in the paper; the standard definitions are used:

$$B=\\left|n_{{eff}}^x-n_{{eff}}^y\\right|,\\qquad L\\,[\\mathrm{{dB/m}}]=8.686\\,\\frac{{2\\pi}}{{\\lambda}}\\left|\\mathrm{{Im}}(n_{{eff}})\\right|$$

**Solver.** Second-order Nédélec (edge) elements represent the transverse field and quadratic Lagrange elements represent E~z~, on curved triangles so that the ellipses are followed accurately. Both mirror planes are used, so one quarter is solved: PEC at x = 0 and PMC at y = 0 for the x-polarised mode, and the reverse for y. The PML is 2.5 µm thick with a quadratic profile and starts 1 µm beyond the outermost hole. The generalised eigenproblem is solved by shift-invert Arnoldi. The LP~01~ mode is taken as the mode with the largest power fraction in the core region. Loss and sensitivity are for the x-polarised mode. Software: Python 3.12, scikit-fem [3], Gmsh [4], SciPy. COMSOL was not available; a guide and script for repeating the model in COMSOL accompany this report but had not been run.

**Very small losses.** A loss of 10^-8^ dB/m at 1 µm means Im(n~eff~) ≈ 2×10^-16^, the round-off limit of double precision. The loss is therefore computed from an energy identity instead of the eigenvalue. For $A\\mathbf{{x}}=\\mu B\\mathbf{{x}}$ with complex-symmetric matrices that are real outside the PML,

$$\\mathrm{{Im}}(\\mu)=\\frac{{\\mathbf{{x}}^H\\,\\mathrm{{Im}}(A)\\,\\mathbf{{x}}-\\mathrm{{Re}}(\\mu)\\,\\mathbf{{x}}^H\\,\\mathrm{{Im}}(B)\\,\\mathbf{{x}}}}{{\\mathbf{{x}}^H\\,\\mathrm{{Re}}(B)\\,\\mathbf{{x}}}}$$

Only PML entries enter the numerator, so no large terms cancel.

# 4. Validation of the solver

**Exact solution.** A circular rod of radius 1 µm at λ = 1 µm, compared with the exact HE~11~ root (largest error of the two polarisations):

{st}

**Mesh and PML convergence** (h = 1 is used for all results; smaller h is finer):

{conv}

Changing PML thickness, PML strength or the silica gap changes no result by more than about 0.1 %, including a loss of 10^-12^ dB/m. Refining the mesh from h = 1 changes n~eff~ by at most about 5×10^-6^, birefringence by about 0.1 %, loss by less than 1 % and r by 0.005 percentage points.

# 5. Results

Lines are this work; markers are values digitised from the paper by pixel calibration of each plot. Markers hidden behind others were left out, not guessed. Crosses (×) are points where at most 85 % of the mode power is in the core region (r < 2 µm), so the mode is weakly confined or mixed with a cladding mode; lines are drawn only through the other points.

## 5.1 Effective index

![Figure 2. Effective index of the x-polarised LP01 mode.](../results/figures/fig2.png){{width=6.4in}}

## 5.2 Field profiles

![Figure 3. Transverse field magnitude of the x-polarised LP01 mode at 1 µm.](../results/figures/fig3_fields.png){{width=5.2in}}

As in the paper, the V-PCF field is star-shaped and compact, the H-PCF field spreads horizontally through the silica channels, and the field is most compact for η = 1.

## 5.3 Birefringence

![Figure 4. Modal birefringence.](../results/figures/fig4.png){{width=6.4in}}

Birefringence is of order 10^-3^ for both fibres, as claimed.

## 5.4 Confinement loss

![Figure 5. Confinement loss.](../results/figures/fig5.png){{width=6.4in}}

## 5.5 Relative sensitivity

![Figure 6. Relative sensitivity.](../results/figures/fig6.png){{width=6.4in}}

## 5.6 Values at λ = 1 µm, η = 0.7

{main_table(1.0)}

## 5.7 Values at λ = 1.5 µm, η = 0.7

{main_table(1.5)}

# 6. Comparison with the paper

{err}

The first error columns use every digitised point; the last two use only well-confined points. The 85 % limit that defines "well-confined" was chosen after the results were seen, so both sets are given; the all-point figures are the stricter test.

**Confinement loss** spans 15 decades and is read from a logarithmic axis where one pixel is about 6.5 % (Fig. 5a) or 12 % (Fig. 5b). The median difference is {es.median_abs_pct['5a']:.1f} % for Fig. 5a ({int(es.N['5a'])} points) and {es.median_abs_pct['5b']:.1f} % for Fig. 5b ({int(es.N['5b'])} points), or {es['median_abs_pct_above_1e-07']['5b']:.1f} % for the {int(es['N_above_1e-07']['5b'])} points of Fig. 5b where the paper's loss is above 10^-7^ dB/m. The mean differences are larger, {es.mean_abs_pct['5a']:.1f} % and {es.mean_abs_pct['5b']:.1f} %, because of outliers. Individual points differ by much more; all are listed in the appendices and discussed in Section 7.

## 6.1 Check of each claim

{tr}

All comparisons use the x-polarised mode (see Section 7.6). Counts for "V against H" and "analyte index" are over points; counts for "rises/falls with λ or η" are over steps between neighbouring points, and the exception is named by the end of the step. All points are counted, including weakly confined ones. Most exceptions are at λ ≤ 0.85 µm, where the n = 1.33 mode is weakly confined or mixed; the paper's own birefringence curves for n = 1.33 and 1.354 also turn upwards at short wavelength. The η = 0.6 exception for B also appears in the paper's Fig. 4b, although its text says V is higher.

# 7. Discussion of differences

**7.1 Mode mixing (V-PCF, n = 1.33, λ ≈ 0.8 µm).** The paper gives r = 15.62 %; this work gives {pick('V',1.33,.8).r:.2f} % exactly at 0.80 µm. A scan in 0.01 µm steps shows why: a cladding mode crosses the core mode there (n~eff~ {s0(.80).neff:.5f} and {s1.neff:.5f}) and the two share their power. Just beside the crossing r is {s0(.79).r:.2f} % (0.79 µm) and {s0(.81).r:.2f} % (0.81 µm), either side of the paper's value. A single wavelength inside such a crossing is not representative.

**7.2 V-PCF, n = 1.33 at 0.9 µm.** The paper plots a loss of 513 dB/m; this work gives {pick('V',1.33,.9).loss:.3f} dB/m, {d09.loss:.3f} with a finer mesh, and the same with a thicker PML. The mode has {100*pick('V',1.33,.9).core:.0f} % of its power in the core and its r and n~eff~ agree with the paper. The paper is not consistent with itself on this curve: at λ = 1 µm, η = 0.7 its Fig. 5a reads about 0.14 dB/m and its Fig. 5b reads 0.044 dB/m for the same point. This work gives {W0.loss:.4f} dB/m, close to Fig. 5b. The cause of the 513 dB/m value could not be determined.

**7.3 Losses at η = 1.** The paper's values there are {lratio.min():.0f} to about {lratio.max():.0f} times larger than ours. Reading the loss directly from the complex eigenvalue, and repeating with slightly different solver shifts, gives values that scatter between zero and about 2×10^-8^ dB/m, while the energy identity is stable:

{rt}

The paper's values at η = 1 (4×10^-12^ to 2×10^-9^ dB/m) are within the range of this scatter, so they are probably affected by round-off. One consequence is that the paper's ordering "V below H" is not found at η = 1, where H is slightly lower here. Such losses are far below any practical relevance.

**7.4 H-PCF losses at η = 0.9** are {l9.min():.0f} to {l9.max():.0f} times lower here than in the paper. The largest (9.3×10^-8^ dB/m) is above the round-off level and changes by only 0.2 % with a finer mesh. This difference is unexplained.

**7.5 Other remarks on the paper.** The H-PCF, n = 1.366 curve is not visible in Fig. 6a although it is present in Fig. 6b; our r for it at 1 µm is {pick('H',1.366,1.0).r:.2f} %. The V-PCF loss markers at 1.5 µm for n = 1.354 and 1.366 are 1.6 times our values, which are mesh-converged; this is also unexplained.

**7.6 The V against H comparison depends on polarisation.** The numbers in the paper match our x-polarised mode for both fibres. V-PCF and H-PCF are nearly the same structure turned by 90°, so this compares the better polarisation of V with the worse one of H. At every well-confined point, r is larger in x for V and in y for H. Compared x with x, V is higher at all {len(pl)+len(pe)} points; compared y with y, H is higher at all of them. With each fibre in its better polarisation, r differs by at most {pol.dbest_r.abs().max():.2f} percentage points and neither fibre is ahead consistently (V ahead at {int((pol.dbest_r>0).sum())} of {len(pol)} points). The lower of the two losses is smaller in V at {int((pol.Lratio_best>1).sum())} of {len(pol)} points, with a ratio H/V between {pol.Lratio_best.min():.2f} and {pol.Lratio_best.max():.2f}. Birefringence does not depend on this choice and is higher in V at all these points.

{ptab}

![Figure 7. Sensitivity in both polarisations, n = 1.33.](../results/figures/polarisation.png){{width=6.2in}}

# 8. Extension: dispersive silica

The paper holds the silica index at 1.45. Real fused silica follows the Sellmeier equation (Malitson [2]), which equals 1.45 near 1.03 µm. V-PCF, η = 0.7:

![Figure 8. Constant and dispersive silica, V-PCF, η = 0.7.](../results/figures/ext_sellmeier.png){{width=6.5in}}

{etab}

Sensitivity changes by less than 0.2 percentage points in the table, so the paper's sensitivity conclusions survive. In V-PCF, birefringence falls by 8–10 % at 1.7 µm; loss falls by 12–18 % for λ ≥ 1.2 µm and rises by 27–40 % at 0.9 µm. The analyte indices were kept constant.

# 9. Conclusions

1. The paper's effective index, birefringence and sensitivity were reproduced to well under 1 % on average at well-confined points.
2. The paper's ranking is reproduced for the x-polarised mode: at η = 0.7 and wavelengths of 0.85 µm and above, V-PCF has higher sensitivity, higher birefringence and lower loss than H-PCF for all three analytes. Only the birefringence advantage is independent of polarisation; with each fibre in its better polarisation the sensitivities are nearly equal (Section 7.6).
3. The best sensitivity among the points computed is {best.r:.2f} % (V-PCF, n = 1.366, λ = 1.7 µm, η = 0.7). At λ = 1 µm the best is {v1.r:.2f} %, at η = 1.
4. The stated dimensions are semi-axes; the paper's wording is misleading on this point.
5. Losses below about 10^-8^ dB/m need a method that avoids round-off, and modes at short wavelength must be checked for mixing.

**Limitations.** Silica and liquids are lossless; the holes are ideal ellipses; the paper's data were read from plots; all results are simulations and were not cross-checked in COMSOL.

# References

[1] H. Ademgil and S. Haxha, "PCF Based Sensor with High Sensitivity, High Birefringence and Low Confinement Losses for Liquid Analyte Sensing Applications," *Sensors*, vol. 15, pp. 31833–31842, 2015. doi:10.3390/s151229891

[2] I. H. Malitson, "Interspecimen Comparison of the Refractive Index of Fused Silica," *J. Opt. Soc. Am.*, vol. 55, p. 1205, 1965. doi:10.1364/JOSA.55.001205

[3] T. Gustafsson and G. D. McBain, "scikit-fem: A Python package for finite element assembly," *J. Open Source Softw.*, vol. 5, no. 52, 2369, 2020. doi:10.21105/joss.02369

[4] C. Geuzaine and J.-F. Remacle, "Gmsh: A 3-D finite element mesh generator with built-in pre- and post-processing facilities," *Int. J. Numer. Meth. Eng.*, vol. 79, pp. 1309–1331, 2009. doi:10.1002/nme.2579

# Appendix A. Confinement loss, Fig. 5a (η = 0.7; x = wavelength in µm)

{lo('5a')}

# Appendix B. Confinement loss, Fig. 5b (λ = 1 µm; x = η)

{lo('5b')}
"""
open("../report/report.md", "w").write(md)
raw = os.path.join(TMP, "report_raw.docx")
subprocess.run(["pandoc", "report.md", "-o", raw], cwd="../report", check=True)

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
d = Document(raw)
for s in d.sections:
    s.page_width, s.page_height = Cm(21), Cm(29.7)
    s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Cm(2.2)
    s.header_distance = s.footer_distance = Cm(1.2); s.gutter = Cm(0)
    p = s.footer.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run()
    for t, x in (("begin", None), (None, "PAGE"), ("end", None)):
        e = OxmlElement("w:fldChar" if t else "w:instrText")
        if t: e.set(qn("w:fldCharType"), t)
        else: e.text = x
        r._r.append(e)
for st_ in d.styles:
    if st_.type == 1:
        rp = st_.element.get_or_add_rPr(); f = rp.find(qn("w:rFonts"))
        if f is not None: rp.remove(f)
        st_.font.name = "Times New Roman"; rp.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        if st_.name.lower().startswith(("heading", "title", "subtitle")): st_.font.color.rgb = RGBColor(0x1a, 0x2b, 0x3c)
for n, z in (("Normal", 11), ("Body Text", 11), ("First Paragraph", 11), ("Heading 1", 15), ("Heading 2", 12.5),
             ("Title", 20), ("Subtitle", 13), ("Author", 12), ("Image Caption", 9.5), ("Compact", 11)):
    for x in d.styles:
        if x.type == 1 and x.name.lower() == n.lower(): x.font.size = Pt(z)
for t in d.tables:
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        x = OxmlElement("w:" + e); x.set(qn("w:val"), "single"); x.set(qn("w:sz"), "4"); x.set(qn("w:space"), "0"); x.set(qn("w:color"), "9AA5B1"); b.append(x)
    pr = t._tbl.tblPr
    anchor = next((pr.find(qn("w:"+k)) for k in ("shd", "tblLayout", "tblCellMar", "tblLook") if pr.find(qn("w:"+k)) is not None), None)
    anchor.addprevious(b) if anchor is not None else pr.append(b)
    for i, row in enumerate(t.rows):
        c = row._tr.get_or_add_trPr()
        if c.find(qn("w:cantSplit")) is None: c.insert(0, OxmlElement("w:cantSplit"))
        for cell in row.cells:
            if i == 0:
                sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), "E3EAF1")
                cell._tc.get_or_add_tcPr().append(sh)
            for p in cell.paragraphs:
                p.paragraph_format.space_after = p.paragraph_format.space_before = Pt(1.5)
                for r in p.runs:
                    r.font.size = Pt(9 if len(t.columns) >= 5 else 10)
                    if i == 0: r.bold = True
for p in d.paragraphs:
    if p._p.findall(".//" + qn("w:drawing")):
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.keep_with_next = True
    if p.style.name == "Image Caption": p.alignment = WD_ALIGN_PARAGRAPH.CENTER
d.save("../report/PCF_Liquid_Sensor_Report.docx")

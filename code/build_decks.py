import numpy as np, pandas as pd
from pptlib import *
d = pd.read_csv("../results/results_main.csv"); paper = pd.read_csv("../paper_data/paper_digitised.csv")
def curves(sw, q, fig, kinds="VH", ns=(1.366, 1.354, 1.33), sc=1):
    out = []
    for n in ns:
        for k in kinds:
            g = d[(d.sweep == sw) & (d.kind == k) & (d.n == n) & (d.cleanB if q == "B" else d.clean)].sort_values(sw)
            out.append((f"{k}, n = {n}", g[sw], g[q]*sc, NC[n], k == "H", None))
    for n in ns:
        for k in kinds:
            g = paper[(paper.fig == fig) & (paper.kind == k) & (paper.n == n)]
            out.append((f"paper {k} {n}", g.x, g.value*sc, NC[n], k == "H", MK[n]))
    return out

REF = ('[1] H. Ademgil and S. Haxha, “PCF based sensor with high sensitivity, high birefringence and low confinement losses '
       'for liquid analyte sensing applications,” ', "Sensors", ', vol. 15, no. 12, pp. 31833–31842, Dec. 2015, doi: 10.3390/s151229891.')
WHO = ["Rishit Bajaj (2023UG4028)", "Electronics and Communication (ES & IoT)", "Supervisor: Dr. Akash Srivastava"]
# ===================================================================== 1. progress
D = Deck("Progress review: PCF liquid sensor")
D.dark("Photonic crystal fibre sensor for liquid analytes", ["Minor project: progress review"] + WHO, ref=REF, notes=
  "Introduce yourself, the topic and that this is a progress review.")
s = D.slide("A fibre can sense a liquid that fills holes in its core", "A PCF is a glass fibre with air holes along its length. If holes in the core are filled with a liquid, part of the light travels in the liquid. The larger that part, the more sensitive the sensor.")
D.pic(s, "study_dims.png", .5, 1.5, 6.3, 5.5, "V-PCF cross-section")
D.card(s, 7.2, 1.6, 5.5, 1.35, "Light stays in the core", "Air holes lower the index around the silica core", 20, 16)
D.card(s, 7.2, 3.4, 5.5, 1.35, "Liquid fills seven core holes", "Part of the guided light passes through the liquid", 20, 16)
D.card(s, 7.2, 5.2, 5.5, 1.35, "Uses", "Sensing water, alcohol and other liquids in chemistry and biology", 20, 16)
s = D.slide("Task: reproduce Ademgil & Haxha, Sensors 2015", "State the paper, what it claims, and my objectives.")
D.card(s, .6, 1.7, 5.9, 3.9, "What the paper proposes", ["Elliptical holes in cladding **and** core", "Two fibres: **V-PCF** (vertical) and **H-PCF** (horizontal)", "Three liquids: n = 1.33, 1.354, 1.366", "Reports sensitivity, birefringence and confinement loss"], 26, 21)
D.card(s, 6.85, 1.7, 5.9, 3.9, "My objectives", ["Model both fibres with full-vector FEM and PML", "Reproduce the paper's figures", "Compare with the paper using numbers", "Study where they agree and differ"], 26, 21)
s = D.slide("The structure and its parameters are fixed", "The hole lengths in the text are semi-axes; I found this by measuring Fig. 3 of the paper.")
D.pic(s, "fig1_geometry.png", .5, 1.5, 7.6, 4.6, "V and H fibres")
D.table(s, [["Parameter", "Value"], ["Cladding holes", "36, air"], ["Cladding pitch", "2.4 µm"], ["Cladding semi-axes", "1.0, 0.7 µm"], ["Core holes", "7, liquid"], ["Core pitch", "1 µm"], ["Core semi-axes", "0.4, 0.2 µm"], ["Silica index", "1.45"]], 8.4, 1.75, [2.5, 1.85], 15, .48)
D.text(s, .6, 6.25, 12.1, .6, "Finding so far: the paper's “axis lengths” are **semi-axes** (checked against its Fig. 3).", 17)
s = D.slide("Progress so far: the model works for the first test point", "These five steps are complete and are what I present today.")
for i, (a, b) in enumerate((("Paper studied", "Theory, structure, formulas"), ("Geometry fixed", "All holes located, semi-axes confirmed"), ("Solver built", "Python FEM with PML"), ("Solver checked", "Error below 10⁻⁶ against exact fibre"), ("First point", "V-PCF, n = 1.33, 1 µm"))):
    x = .6 + i*2.46
    D.card(s, x, 2.35, 2.26, 1.75, a, b, 18, 16)
    D.text(s, x+.18, 1.8, 2.1, .4, f"{i+1}  Done", 18, TEAL, True)
D.text(s, .6, 4.7, 12.1, 1.2, ["**Software:** Python (scikit-fem, Gmsh). A COMSOL model script is written; it has not been run yet."], 18)
s = D.slide("First result agrees with the paper", "Values at lambda = 1 um, eta = 0.7, n = 1.33, x-polarised mode. Paper values are read from its plots.")
D.pic(s, "field_V.png", .5, 1.5, 6.2, 5.4, "Field of V-PCF")
D.table(s, [["V-PCF, n = 1.33, λ = 1 µm", "Mine", "Paper"], ["Effective index", "1.4041", "1.404"], ["Sensitivity (%)", "20.59", "20.59"], ["Birefringence (×10⁻³)", "2.58", "2.58"], ["Confinement loss (dB/m)", "0.049", "0.044"]], 7.0, 1.9, [3.3, 1.2, 1.2], 16, .58)
D.text(s, 7.0, 5.2, 5.7, 1.5, ["Light is confined in the core and overlaps the liquid holes.", "Paper values are read from its plots; index and birefringence are interpolated."], 16)
s = D.slide("The final review will cover the full comparison", "If asked what is complete, answer truthfully.")
for i, (a, b) in enumerate((("Wavelength and ellipticity", "Index, birefringence, loss and sensitivity curves"), ("V-PCF against H-PCF", "Three liquids, both fibres"), ("Comparison with the paper", "Error values and reasons for differences"), ("COMSOL", "Cross-check, depending on licence access"))):
    D.card(s, .6 + (i % 2)*6.2, 1.8 + (i//2)*2.1, 5.9, 1.7, a, b, 24, 19)
D.save("../presentation/1_Progress_Presentation.pptx")

# ===================================================================== 2. final
D = Deck("PCF liquid sensor: final presentation")
D.dark("Reproducing a PCF sensor for liquid analytes", ["Minor project"] + WHO, ref=REF, notes=
  "Good morning. My project reproduces a 2015 paper on a photonic crystal fibre that senses liquids, checks every claim, and adds an extension.")
s = D.slide("Elliptical holes target three goals at once", "Liquid fills seven core holes. V and H have the same holes, vertical or horizontal. The dimensions in the paper are semi-axes: Fig. 3 shows 1.4 x 2.0 um holes, and only this reading gives r = 20.59 %.", 28)
D.pic(s, "fig1_geometry.png", .5, 1.45, 7.9, 4.2, "Geometry")
D.card(s, 8.7, 1.5, 4.05, 1.15, "Sensitivity", "Power inside the liquid", 20, 16); D.card(s, 8.7, 2.95, 4.05, 1.15, "Birefringence", "Difference of the two polarisations", 20, 16); D.card(s, 8.7, 4.4, 4.05, 1.15, "Confinement loss", "Light leaking out of the core", 20, 16)
D.text(s, .6, 5.95, 12.1, 1.0, ["36 air holes, pitch 2.4 µm, semi-axes 1.0 and 0.7 µm (η = 0.7). 7 liquid holes, pitch 1 µm, semi-axes 0.4 and 0.2 µm. Silica 1.45. Liquids 1.33, 1.354, 1.366.", "The paper calls these “axis lengths”; its Fig. 3 and my runs show they are **semi-axes**."], 15)
s = D.slide("Full-vector FEM with PML, verified before use", "One quarter is solved. PEC and PMC walls select the polarisation. Loss is from an energy identity because values below 1e-8 dB/m are lost in round-off.")
D.pic(s, "study_mesh.png", .5, 1.5, 7.6, 4.0, "Mesh")
D.table(s, [["Check", "Result"], ["Exact step-index fibre", "n_eff error < 10⁻⁶"], ["Finer mesh", "B changes ≈ 0.1 %"], ["PML and gap", "change ≤ 0.1 %"]], 8.4, 1.7, [2.5, 2.0], 13, .52)
D.text(s, 8.4, 4.1, 4.4, 1.6, ["Python: scikit-fem, Gmsh, SciPy", "COMSOL script written, not yet run"], 15)
D.card(s, .6, 5.7, 3.9, 1.2, "r = (n_r / n_eff) · f", "f: share of power in the liquid", 17, 14); D.card(s, 4.72, 5.7, 3.9, 1.2, "B = |n_x − n_y|", "difference of effective indices", 17, 14); D.card(s, 8.84, 5.7, 3.9, 1.2, "L = 8.686 k₀ |Im n_eff|", "confinement loss in dB/m", 17, 14)
s = D.slide("The modes reproduce Fig. 3 of the paper", "V: compact star. H: spreads sideways through silica channels in x-polarisation. eta = 1: most compact.")
D.pic(s, "fig3_fields.png", .4, 1.4, 6.9, 5.7, "Fields")
D.card(s, 7.7, 1.8, 5.0, 1.2, "V-PCF", "Star-shaped, compact", 22, 17); D.card(s, 7.7, 3.4, 5.0, 1.2, "H-PCF", "x-pol field spreads sideways in silica channels", 22, 17); D.card(s, 7.7, 5.0, 5.0, 1.2, "η = 1", "Larger holes, most compact field", 22, 17)
s = D.slide("Sensitivity agrees to 0.1–0.2 % on average at well-confined points", "Lines: this work. Symbols: paper, dark V, light H. With all points the mean error in Fig 6a is 0.98 percent and the maximum 38.7, from the mode crossing at 0.8 um. Sensitivity rises with wavelength, eta and analyte index.", 28)
D.chart(s, .4, 1.4, 6.4, 5.1, curves("lam", "r", "6a"), "Wavelength (µm), η = 0.7", "r (%)", (.7, 1.7), (10, 28), xu=.2, yu=4, fmt="0")
D.chart(s, 6.7, 1.4, 6.4, 5.1, curves("eta", "r", "6b"), "Ellipticity η, λ = 1 µm", "r (%)", (.6, 1.0), (10, 28), xu=.1, yu=4, fmt="0")
D.text(s, .6, 6.6, 11.2, .6, "Lines: this work, x-polarised. Symbols: paper (dark V, light H). Best: 25.75 % (V, n = 1.366, 1.7 µm).", 15)
s = D.slide("Birefringence agrees to 0.2–0.4 %; loss to 14–16 % (median)", "Loss mean errors are 20 and 40 percent because of outliers; say so. Fig 5a outlier V 1.33 at 0.9 um: paper 513, mine 0.41, unexplained.", 28)
D.chart(s, .4, 1.4, 6.4, 5.1, curves("lam", "B", "4a", sc=1e3), "Wavelength (µm), η = 0.7", "B (×10⁻³)", (.7, 1.7), (.8, 3.8), xu=.2, yu=.6, fmt="0.0")
D.chart(s, 6.7, 1.4, 6.4, 5.1, curves("lam", "loss", "5a"), "Wavelength (µm), η = 0.7", "Loss (dB/m)", (.7, 1.7), (1e-4, 1e3), log=True, xu=.2, fmt="0E+00")
D.text(s, .6, 6.6, 11.2, .6, "Lines: this work. Symbols: paper (dark V, light H). Loss means are 20 % (Fig. 5a) and 40 % (Fig. 5b) because of outliers.", 15)
s = D.slide("New finding: “V beats H” depends on the polarisation chosen", "The paper compares x-pol of both. V and H are almost the same fibre turned by 90 degrees, so that is V's good axis against H's bad axis. With each fibre in its better polarisation, r differs by at most 0.12 points over 85 points. Only birefringence is higher in V independent of the choice.", 28)
D.pic(s, "polarisation.png", .4, 1.4, 8.1, 4.6, "Both polarisations")
D.table(s, [["n = 1.33, 1 µm", "V", "H"], ["r, x-pol (%)", "20.59", "18.51"], ["r, y-pol (%)", "18.42", "20.62"], ["Lowest loss (dB/m)", "0.049", "0.067"], ["B (×10⁻³)", "2.58", "2.37"]], 8.8, 1.7, [2.3, .85, .85], 14, .5)
D.text(s, 8.8, 4.5, 4.0, 1.6, ["Compared x with x: **V higher** at 85 of 85", "Compared y with y: **H higher** at 85 of 85", "Birefringence: **V higher** in all 85"], 15)
D.text(s, .6, 6.2, 11.2, .9, "V and H are nearly the same fibre turned by 90°. Best against best, r differs by at most 0.12 points.", 17, AC, True)
s = D.slide("Four differences from the paper", "Be honest: two are explained or likely explained, two are not.")
D.table(s, [["Point", "Paper", "This work", "Status"],
 ["V, 1.33, 0.8 µm: r", "15.62 %", "9.57 %", "Explained: a cladding mode crosses; 14.5 % and 15.9 % just beside it"],
 ["V, 1.33, 0.9 µm: loss", "513 dB/m", "0.41 dB/m", "Unexplained; the paper's 5a and 5b disagree at 1 µm for this curve (0.14, 0.044)"],
 ["η = 1: loss", "10⁻¹²–10⁻⁹", "3–825× lower", "Probably round-off: a direct eigenvalue scatters up to 2×10⁻⁸"],
 ["H, η = 0.9: loss", "up to 6×10⁻⁷", "5–7× lower", "Unexplained; mesh change is 0.2 % (n = 1.33)"]], .6, 1.6, [2.5, 1.9, 1.9, 5.8], 15, .6)
D.pic(s, "study_crossing.png", .6, 4.95, 8.2, 2.3, "Mode crossing")
D.text(s, 8.9, 5.2, 3.2, 1.6, "Row 1: at 0.80 µm the core mode shares its power with a cladding mode, so r dips.", 15)
s = D.slide("Extension: real silica dispersion barely changes sensitivity", "Malitson Sellmeier equation. Table wavelengths 0.9 to 1.7 um. Analyte index constant.")
D.pic(s, "ext_sellmeier.png", .5, 1.4, 12.3, 3.9, "Sellmeier")
D.card(s, .6, 5.5, 3.9, 1.45, "Sensitivity", "under 0.2 points change (0.9–1.7 µm)", 19, 15); D.card(s, 4.72, 5.5, 3.9, 1.45, "Birefringence", "8–10 % lower at 1.7 µm", 19, 15); D.card(s, 8.84, 5.5, 3.9, 1.45, "Loss", "12–18 % lower for λ ≥ 1.2 µm; 27–40 % higher at 0.9 µm", 19, 15)
D.dark("The paper is largely reproduced, with a caution on its ranking", ["Index, birefringence and sensitivity match to well under 1 % on average at well-confined points", "Dimensions are semi-axes", "V leads in x-polarisation; only its birefringence lead is independent of polarisation", "Next: run the COMSOL cross-check; add liquid absorption and dispersion"],
  "Thank you. Limitations: lossless materials, ideal ellipses, constant analyte index, paper data read from plots, no COMSOL or experiment.", 36)
D.save("../presentation/2_Final_Presentation.pptx")

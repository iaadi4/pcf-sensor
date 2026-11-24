# Repeating the model in COMSOL by hand

For the scripted version see `README_COMSOL.md`.

Needs the Wave Optics or RF Module. **This guide was not run: COMSOL was not available.** Check it against the target values at the end. Menu names can differ slightly between versions.

1. **New model:** 2D > Electromagnetic Waves, Frequency Domain (ewfd; `emw` in the RF Module) > Mode Analysis.
2. **Parameters:** Global Definitions > Parameters > Load from File > `pcf_parameters.txt`.
3. **Geometry** (unit µm, full cross-section). COMSOL's Ellipse takes *semi-axes*, as here.
   - Cladding: for each row j = -3..3, y = j·Λ·√3/2, 7-|j| holes spaced Λ, first hole at x = -(6-|j|)·Λ/2. Leave out the hole at the origin. Total 36. Semi-axes V-PCF: a = db, b = da. H-PCF: a = da, b = db.
   - Core: holes at (0,0), (0,±Lamc), (±0.866·Lamc, ±0.5·Lamc). Total 7. Semi-axes V: a = dc, b = ds. H: a = ds, b = dc.
   - Background rectangle: half-width 3Λ + (x semi-axis) + gap; half-height 3·Λ·√3/2 + (y semi-axis) + gap. Then enlarge both half-sizes by tpml and add layers of thickness tpml on all four sides for the PML (COMSOL puts layers inside the rectangle).
4. **Materials:** silica nsi (background and PML), air 1, analyte na (refractive index, imaginary part 0).
5. **PML:** Definitions > Perfectly Matched Layer on the outer layers (Cartesian). Outer boundary: Perfect Electric Conductor (default).
6. **Mesh:** triangular; maximum element about 0.1 µm in the core, 0.2-0.3 µm elsewhere; use quadratic elements. Refine until n_eff is stable to 1e-5.
7. **Study > Mode Analysis:** frequency f0; search for modes around 1.405 (near the expected n_eff); about 10 modes.
8. **Pick the mode:** LP01 is compact in the core. The x-polarised one has mainly Ex, the y-polarised one mainly Ey. At wavelengths below 0.85 µm with n = 1.33, look at several modes: cladding modes mix with it.
9. **Results:** define integration operators `intA` over the 7 analyte holes and `intT` over everything except the PML.
   - r (%) = 100*(na/real(ewfd.neff))*intA(ewfd.Poavz)/intT(ewfd.Poavz)
   - loss (dB/m) = 8.686*2*pi/lam0*abs(imag(ewfd.neff))
   - B = |n_eff(x-pol) - n_eff(y-pol)|
10. **Sweeps:** Parametric Sweep over lam0 (0.7-1.7 µm) and eta (0.6-1.0) for na = 1.33, 1.354, 1.366. Update the search index with the wavelength.

## Target values (this work, λ = 1 µm, η = 0.7)

| Fibre | n | n_eff (x) | B | Loss (dB/m) | r (%) |
|---|---|---|---|---|---|
| V-PCF | 1.33 | 1.40413 | 2.576e-03 | 0.0486 | 20.59 |
| V-PCF | 1.354 | 1.40971 | 1.769e-03 | 0.00202 | 22.17 |
| V-PCF | 1.366 | 1.41260 | 1.424e-03 | 0.000463 | 22.93 |
| H-PCF | 1.33 | 1.40656 | 2.366e-03 | 0.835 | 18.51 |
| H-PCF | 1.354 | 1.41137 | 1.621e-03 | 0.039 | 20.52 |
| H-PCF | 1.366 | 1.41394 | 1.307e-03 | 0.0091 | 21.47 |

Losses below about 1e-8 dB/m cannot be trusted from the eigenvalue (round-off).

# PCF liquid-analyte sensor: reproduction

Reproduces Ademgil & Haxha, Sensors 2015, 15, 31833 (doi:10.3390/s151229891).

| Folder | Contents |
|---|---|
| `report/` | Word and PDF report (`report.md` is the source) |
| `presentation/` | `1_Progress_Presentation.pptx` (7 slides), `2_Final_Presentation.pptx` (10 slides) |
| `results/` | CSV data, validation, error statistics, `figures/` |
| `paper_data/` | Values digitised from the paper's plots |
| `code/` | Solver and scripts |
| `comsol/` | COMSOL script, install/run guide, manual guide (not yet run in COMSOL) |

## Live demo (about 1 minute)

`code/demo.py` solves one point of the paper and shows the result. Each mode takes about 5–15 s.

**1. Set up once**

Linux (from the project folder):

```
uv venv .venv
uv pip install --python .venv/bin/python numpy scipy matplotlib pandas gmsh scikit-fem meshio
```

Windows (Command Prompt in the project folder; Python 3.10 or newer, 64-bit):

```
pip install numpy scipy matplotlib pandas gmsh scikit-fem meshio
```

**2. Run**

```
cd code
../.venv/bin/python demo.py          (Windows: python demo.py)
```

It prints this table and opens a window with the field plot:

```
Quantity                     This work     Paper
Effective index (x)            1.40413     1.404
Birefringence                2.576e-03  2.58e-03
Confinement loss (dB/m)         0.0486     0.044
Sensitivity r (%)                20.59     20.59
Power in liquid f (%)            21.73         -
```

The plot is also saved as `results/demo_V_1.33.png`.

**Other cases:** `demo.py <V or H> <analyte index>`, for example `demo.py H 1.366` or `demo.py V 1.354`. Wavelength 1 µm, η = 0.7. The paper column appears only for V-PCF with n = 1.33. Paper values are read from its plots.

**Tips**
- Run it once before presenting; the first run is slower.
- Do not run the full sweeps live; they take about 40 minutes. Show the figures in the slides instead.
- No plot window (for example over SSH): the plot is still saved to `results/`.
- If `gmsh` fails to install on Windows, try `pip install --upgrade pip` and install again.

## Full reproduction

Run in `code/` with `../.venv/bin/python`, in this order:
`make_paper_csv.py`, `validate.py`, `run_sweeps.py main`, `run_sweeps.py ext`, `diagnostics.py`, `fields.py`, `analyse.py`, `extension.py`, `polarisation.py`, `study_figures.py`, `build_report.py <temp folder>`, `build_decks.py`.

To recreate the environment: `uv venv .venv && uv pip install --python .venv/bin/python numpy scipy matplotlib pandas gmsh scikit-fem meshio pillow python-docx python-pptx`
(tested with scikit-fem 12.0.2, gmsh 4.15.2, scipy 1.18.1). The report also needs pandoc.

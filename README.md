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

Run in `code/` with `../.venv/bin/python`, in this order:
`make_paper_csv.py`, `validate.py`, `run_sweeps.py main`, `run_sweeps.py ext`, `diagnostics.py`, `fields.py`, `analyse.py`, `extension.py`, `polarisation.py`, `study_figures.py`, `build_report.py <temp folder>`, `build_decks.py`.

To recreate the environment: `uv venv .venv && uv pip install --python .venv/bin/python numpy scipy matplotlib pandas gmsh scikit-fem meshio pillow python-docx python-pptx`
(tested with scikit-fem 12.0.2, gmsh 4.15.2, scipy 1.18.1). The report also needs pandoc.

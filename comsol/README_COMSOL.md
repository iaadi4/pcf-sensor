# COMSOL version: install and run

**Status: the script has not been run in COMSOL yet.** `offline_checks.py` verifies the geometry and the script's own logic; only `pcf_comsol.py test` can show that COMSOL accepts it. Do not report COMSOL results until that test passes.

## 1. Install
- Use a licensed copy (college licence or COMSOL's trial). COMSOL 6.x is recommended.
- Tick only **COMSOL Multiphysics** and **Wave Optics Module** (or RF Module). Skip documentation and the other modules to save space.
- On this laptop `/` had about 12 GB free. `/media/Programming` has more (21 GB) but is an NTFS-type drive, where Linux program installs can break (permissions, links). Install on `/` (default `/usr/local`) and compare the installer's size with the free space first; free some space if it does not fit comfortably. If the laptop also has Windows, installing there is fine too.
- If `comsol` is not found afterwards, link it: `ln -s <install folder>/multiphysics/bin/comsol ~/.local/bin/comsol`
- Check: `comsol -version` works in a new terminal.
- On Linux, start `comsol mphserver` once by hand. If it asks for a username and password, create them (they are local to this PC), then close it.

## 2. Run (from this folder)
Close other programs; COMSOL needs memory.

| Step | Command | What it does |
|---|---|---|
| 1 | `../.venv/bin/python pcf_comsol.py test` | 4 solves; prints PASS/CHECK against Python; saves `results/PCF_liquid_sensor.mph` |
| 2 | `../.venv/bin/python pcf_comsol.py converge` | Mesh, PML and gap check (10 solves) |
| 3 | `../.venv/bin/python pcf_comsol.py paper` | 192 solves at the paper's points. Can be stopped and restarted |
| 4 | `../.venv/bin/python compare_comsol.py` | Figures, CSVs and error summary in `results/` |
| optional | `../.venv/bin/python pcf_comsol.py full` | Full 360-point grid; keeps the points already done |

Options: `--classkit` for a class-kit licence, `--cores 4`, `--version 6.2`.

On a Windows lab PC: install Python 3, then `pip install mph pandas matplotlib numpy`, copy the whole project folder, and use `python` instead of `../.venv/bin/python`.

`results/PCF_liquid_sensor.mph` opens in the normal COMSOL window, to show your guide the geometry, mesh and field.

## 3. If the test fails
| Message | Likely cause |
|---|---|
| Could not find a supported Comsol installation | `comsol` is not on the PATH |
| License error | Wave Optics/RF not licensed, or try `--classkit` |
| Login / server error | Run `comsol mphserver` once by hand (section 1) |
| Unknown property / operator | API differs in your version: send me the full message |
| n_eff agrees, loss says CHECK | PML setting: run `converge` and send me its output |
| n_eff differs a lot | Wrong mode or geometry: open the .mph and send a screenshot |

## 4. What is independent and what is not
COMSOL builds its own mesh, uses its own PML and solver, and finds its own modes. The Python results are used only for the starting search values in `test` and for the comparison. Mode choice (largest power within 2 µm of the centre) follows the same rule in both. Losses below about 1e-8 dB/m come straight from COMSOL's eigenvalue and are round-off limited.

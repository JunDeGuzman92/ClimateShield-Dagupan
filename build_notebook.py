import sys
import py_compile

BASE = r"C:\Users\junbu\Documents\ClimateShieldProject for Dagupan"
sys.path.insert(0, BASE)

try:
    py_compile.compile(f"{BASE}\\nbcells_part6.py", doraise=True)
    print("part6 syntax OK")
except py_compile.PyCompileError as e:
    print("part6 FAIL:", e)
    sys.exit(1)

import nbformat as nbf

from nbcells_part1 import CELLS_P1
from nbcells_part2 import CELLS_P2
from nbcells_part3 import CELLS_P3
from nbcells_part4 import CELLS_P4
from nbcells_part5 import CELLS_P5
from nbcells_part6 import CELLS_P6

ALL = CELLS_P1 + CELLS_P2 + CELLS_P3 + CELLS_P4 + CELLS_P5 + CELLS_P6
nb_cells = []
skipped = 0
for kind, src in ALL:
    if kind == "code" and not src.strip():
        skipped += 1
        continue
    nb_cells.append(nbf.v4.new_code_cell(src) if kind == "code" else nbf.v4.new_markdown_cell(src))

nb = nbf.v4.new_notebook(cells=nb_cells)
nb.metadata = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.12"},
}

code_errors = 0
for idx, cell in enumerate(nb.cells):
    if cell.cell_type != "code":
        continue
    try:
        compile(cell.source, f"cell_{idx}", "exec")
    except SyntaxError as e:
        code_errors += 1
        print(f"SYNTAX PROBLEM in cell {idx} (line {e.lineno}): {e.msg}")
        lines = cell.source.splitlines()
        if e.lineno and e.lineno - 1 >= 0 and e.lineno - 1 < len(lines):
            print(f"   context: {lines[max(0, e.lineno - 2):e.lineno + 1]}")
if code_errors:
    print(f"ABORTING: {code_errors} code cells have syntax problems (fix part files)")
    sys.exit(1)
print("all code cells compile cleanly")

out = f"{BASE}\\ClimateShield_Dagupan_Analysis.ipynb"
with open(out, "w", encoding="utf-8") as f:
    nbf.write(nb, f)

md_count = sum(1 for k, _ in ALL if k == "md")
print(f"Notebook written: {out}")
print(f"cells: {len(nb_cells)} (md {md_count}, code {len(nb_cells) - md_count}); empty code cells skipped: {skipped}")

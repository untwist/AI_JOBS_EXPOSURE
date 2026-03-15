"""
Build ILO 4-digit ISCO-08 exposure CSV from pgmyrek/2025_GenAI_scores_ISCO08 data.

Reads data/4digits_with_tasks.xlsx (from https://github.com/pgmyrek/2025_GenAI_scores_ISCO08).
Writes data/ilo_exposure_isco08.csv with columns: isco08, exposure_pct, exposure_gradient.

Usage:
    uv run python scripts/build_ilo_isco08_exposure.py
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

import openpyxl


def main() -> None:
    xlsx_path = Path("data/4digits_with_tasks.xlsx")
    if not xlsx_path.exists():
        print("Download 4digits_with_tasks.xlsx to data/ from:")
        print("  https://github.com/pgmyrek/2025_GenAI_scores_ISCO08")
        return

    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws = wb["Sheet1"]
    scores_by_4d: dict[str, list[float]] = defaultdict(list)
    gradient_by_4d: dict[str, list[str]] = defaultdict(list)

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or len(row) < 6:
            continue
        isco4 = row[3]
        task_text = row[4]
        pot = row[5]
        if not isco4 or not isinstance(isco4, str):
            continue
        if "-" in isco4:
            code = isco4.split("-")[0].strip().replace(" ", "")[:4]
        else:
            code = str(isco4).strip()[:4]
        if not code.isdigit():
            continue
        if task_text and isinstance(task_text, str):
            m = re.search(r"\(\s*([0-9.]+)\s*\)", task_text)
            if m:
                try:
                    scores_by_4d[code].append(float(m.group(1)))
                except ValueError:
                    pass
        if pot:
            gradient_by_4d[code].append(str(pot).strip())

    wb.close()

    out_path = Path("data/ilo_exposure_isco08.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["isco08", "exposure_pct", "exposure_gradient"])
        for code in sorted(scores_by_4d.keys()):
            scores = scores_by_4d[code]
            mean_score = sum(scores) / len(scores) if scores else None
            exposure_pct = round(mean_score * 100) if mean_score is not None else ""
            grads = gradient_by_4d.get(code, [])
            gradient = max(set(grads), key=grads.count) if grads else ""
            w.writerow([code, exposure_pct, gradient])

    print(f"Wrote {out_path} with {len(scores_by_4d)} ISCO-08 4-digit occupations")


if __name__ == "__main__":
    main()

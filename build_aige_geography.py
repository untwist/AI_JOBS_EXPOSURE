"""
Build AIGE (county-level AI exposure) JSON for the geography map.

Reads data/AIOE_DataAppendix.xlsx Appendix C (FIPS Code, Geographic Area, AIGE).
Outputs docs/aige_by_county.json: { "FIPS": AIGE_value, ... } with 5-digit FIPS keys.
AIGE raw values are min-max scaled to 0-100 for consistent choropleth coloring.

Usage:
    uv run python build_aige_geography.py
"""

import json
from pathlib import Path

import openpyxl


def main():
    xlsx_path = Path("data/AIOE_DataAppendix.xlsx")
    if not xlsx_path.exists():
        print("Download AIOE_DataAppendix.xlsx to data/ from https://github.com/AIOE-Data/AIOE")
        return

    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws = wb["Appendix C"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    wb.close()

    # FIPS (int) -> raw AIGE
    raw = {}
    for row in rows:
        if len(row) < 3 or row[0] is None or row[2] is None:
            continue
        try:
            fips_int = int(row[0])
            val = float(row[2])
        except (TypeError, ValueError):
            continue
        # 5-digit FIPS string for GeoJSON (e.g. 1001 -> "01001")
        fips_str = str(fips_int).zfill(5)
        raw[fips_str] = val

    if not raw:
        print("No AIGE values in Appendix C")
        return

    # Min-max scale to 0-100 for map coloring
    lo, hi = min(raw.values()), max(raw.values())
    span = hi - lo if hi != lo else 1.0
    out = {fips: round((v - lo) / span * 100, 1) for fips, v in raw.items()}

    Path("docs").mkdir(exist_ok=True)
    out_path = Path("docs/aige_by_county.json")
    with open(out_path, "w") as f:
        json.dump(out, f)

    print(f"Wrote {out_path} with {len(out)} FIPS codes (AIGE 0-100)")


if __name__ == "__main__":
    main()

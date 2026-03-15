"""
Merge Felten et al. AIOE (occupation-level AI exposure) into docs data.

Reads occupations.csv (for SOC codes), data/AIOE_DataAppendix.xlsx (Appendix A),
and docs/data.json. Writes docs/data.json with aioe_exposure_pct (0-100) added.
AIOE raw values are min-max scaled to 0-100 for display parity with Anthropic.

Usage:
    uv run python merge_aioe_exposure.py

Requires: data/AIOE_DataAppendix.xlsx from https://github.com/AIOE-Data/AIOE
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

import openpyxl


def main():
    # Load slug -> soc_code from occupations.csv
    slug_to_soc = {}
    with open("occupations.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            slug_to_soc[row["slug"]] = (row.get("soc_code") or "").strip()

    # Load AIOE from Appendix A
    xlsx_path = Path("data/AIOE_DataAppendix.xlsx")
    if not xlsx_path.exists():
        print("Download AIOE_DataAppendix.xlsx to data/ from:")
        print("  https://github.com/AIOE-Data/AIOE")
        return

    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws = wb["Appendix A"]
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    wb.close()

    # SOC -> raw AIOE (skip header; SOC Code col 0, AIOE col 2)
    raw = {}
    for row in rows:
        if len(row) < 3 or row[0] is None or row[2] is None:
            continue
        try:
            soc = str(row[0]).strip()
            val = float(row[2])
        except (TypeError, ValueError):
            continue
        if soc:
            raw[soc] = val

    if not raw:
        print("No AIOE values found in Appendix A")
        return

    # Min-max scale to 0-100 for display (same scale as Anthropic %)
    lo, hi = min(raw.values()), max(raw.values())
    span = hi - lo if hi != lo else 1.0
    exact = {soc: round((v - lo) / span * 100) for soc, v in raw.items()}

    # Prefix fallback for BLS broad codes (e.g. 11-3010)
    prefix_exposures = defaultdict(list)
    for soc, pct in exact.items():
        if len(soc) >= 5:
            prefix_exposures[soc[:5]].append(pct)

    def get_aioe_pct(soc_code: str) -> int | None:
        if not soc_code:
            return None
        soc_code = soc_code.strip()
        if soc_code in exact:
            return exact[soc_code]
        if len(soc_code) >= 5:
            pre = soc_code[:5]
            if pre in prefix_exposures:
                return round(sum(prefix_exposures[pre]) / len(prefix_exposures[pre]))
        return None

    # Load docs data
    with open("docs/data.json") as f:
        data = json.load(f)

    matched = 0
    for rec in data:
        slug = rec.get("slug")
        soc_code = slug_to_soc.get(slug, "")
        rec["aioe_exposure_pct"] = get_aioe_pct(soc_code)
        if rec["aioe_exposure_pct"] is not None:
            matched += 1

    Path("docs").mkdir(exist_ok=True)
    with open("docs/data.json", "w") as f:
        json.dump(data, f)

    print(f"Wrote docs/data.json with aioe_exposure_pct for {len(data)} occupations")
    print(f"Matched AIOE (Felten et al.): {matched}/{len(data)}")


if __name__ == "__main__":
    main()

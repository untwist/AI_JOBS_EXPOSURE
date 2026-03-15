"""
Merge ILO (task-based) job exposure into docs data.

Reads occupations.csv (for SOC codes), data/ilo_exposure_isco08.csv (ILO WP140 by ISCO-08),
data/isco08_soc2010_crosswalk.csv, and docs/data.json. Aggregates ILO exposure from ISCO-08
to SOC via the crosswalk, then writes docs/data.json with ilo_exposure_pct (0-100) added.

Usage:
    uv run python merge_ilo_exposure.py

Requires: data/ilo_exposure_isco08.csv (run scripts/build_ilo_isco08_exposure.py),
          data/isco08_soc2010_crosswalk.csv (from IBS or BLS).
"""

import csv
import json
from collections import defaultdict
from pathlib import Path


def main() -> None:
    # Load slug -> soc_code from occupations.csv
    slug_to_soc: dict[str, str] = {}
    with open("occupations.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            slug_to_soc[row["slug"]] = (row.get("soc_code") or "").strip()

    # Load ILO exposure by ISCO-08 4-digit
    ilo_path = Path("data/ilo_exposure_isco08.csv")
    if not ilo_path.exists():
        print("Run scripts/build_ilo_isco08_exposure.py to create data/ilo_exposure_isco08.csv")
        return
    isco_to_pct: dict[str, int] = {}
    with open(ilo_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            isco = (row.get("isco08") or "").strip()
            if not isco:
                continue
            isco = isco.zfill(4)[:4]
            raw = row.get("exposure_pct")
            if raw == "":
                continue
            try:
                isco_to_pct[isco] = int(float(raw))
            except (TypeError, ValueError):
                continue

    # Load crosswalk: soc_code <-> isco08 (many-to-many)
    cw_path = Path("data/isco08_soc2010_crosswalk.csv")
    if not cw_path.exists():
        print("Place data/isco08_soc2010_crosswalk.csv (SOC code, isco08).")
        print("  Source: IBS onetsoc_to_isco_cws_ibs (soc10_isco08.dta) or BLS ISCO_SOC_Crosswalk.xls")
        return
    soc_to_iscos: dict[str, list[str]] = defaultdict(list)
    with open(cw_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            soc = (row.get("soc_code") or "").strip()
            isco = (row.get("isco08") or "").strip()
            if not soc or not isco:
                continue
            isco = str(isco).replace(".0", "").zfill(4)[:4]
            soc_to_iscos[soc].append(isco)

    # Aggregate: for each SOC, mean of ILO exposure over linked ISCOs
    exact: dict[str, int] = {}
    prefix_exposures: dict[str, list[int]] = defaultdict(list)
    for soc, iscos in soc_to_iscos.items():
        values = [isco_to_pct[i] for i in iscos if i in isco_to_pct]
        if not values:
            continue
        exact[soc] = round(sum(values) / len(values))
        if len(soc) >= 5:
            prefix_exposures[soc[:5]].append(exact[soc])

    def get_ilo_pct(soc_code: str) -> int | None:
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
        rec["ilo_exposure_pct"] = get_ilo_pct(soc_code)
        if rec["ilo_exposure_pct"] is not None:
            matched += 1

    Path("docs").mkdir(exist_ok=True)
    with open("docs/data.json", "w") as f:
        json.dump(data, f)

    print(f"Wrote docs/data.json with ilo_exposure_pct for {len(data)} occupations")
    print(f"Matched ILO (task-based) exposure: {matched}/{len(data)}")


if __name__ == "__main__":
    main()

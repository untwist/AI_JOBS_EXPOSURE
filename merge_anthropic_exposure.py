"""
Merge Anthropic job exposure (observed exposure %) into docs data.

Reads occupations.csv (for SOC codes), data/job_exposure.csv (Anthropic),
and docs/data.json. Writes docs/data.json with observed_exposure_pct (0-100) added.

Usage:
    uv run python merge_anthropic_exposure.py
"""

import csv
import json
from collections import defaultdict
from pathlib import Path


def main():
    # Load slug -> soc_code from occupations.csv
    slug_to_soc = {}
    with open("occupations.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            slug_to_soc[row["slug"]] = (row.get("soc_code") or "").strip()

    # Load Anthropic job_exposure: exact occ_code -> exposure, and prefix -> list of exposures
    job_exposure_path = Path("data/job_exposure.csv")
    if not job_exposure_path.exists():
        print("Download job_exposure.csv to data/job_exposure.csv from:")
        print("  https://huggingface.co/datasets/Anthropic/EconomicIndex/blob/main/labor_market_impacts/job_exposure.csv")
        return
    exact = {}
    prefix_exposures = defaultdict(list)
    with open(job_exposure_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("occ_code") or "").strip()
            try:
                val = float(row.get("observed_exposure", 0))
            except (TypeError, ValueError):
                continue
            if not code:
                continue
            exact[code] = val
            # prefix = first 5 chars (e.g. 11-30) for fallback when BLS has broad code like 11-3010
            if len(code) >= 5:
                prefix_exposures[code[:5]].append(val)

    def get_observed_pct(soc_code: str) -> int | None:
        if not soc_code:
            return None
        soc_code = soc_code.strip()
        if soc_code in exact:
            return round(exact[soc_code] * 100)
        # Fallback: average of Anthropic codes with same 5-char prefix
        if len(soc_code) >= 5:
            pre = soc_code[:5]
            if pre in prefix_exposures:
                avg = sum(prefix_exposures[pre]) / len(prefix_exposures[pre])
                return round(avg * 100)
        return None

    # Load docs data
    with open("docs/data.json") as f:
        data = json.load(f)

    # Merge
    matched = 0
    for rec in data:
        slug = rec.get("slug")
        soc_code = slug_to_soc.get(slug, "")
        pct = get_observed_pct(soc_code)
        rec["observed_exposure_pct"] = pct
        if pct is not None:
            matched += 1

    Path("docs").mkdir(exist_ok=True)
    with open("docs/data.json", "w") as f:
        json.dump(data, f)

    print(f"Wrote docs/data.json with observed_exposure_pct for {len(data)} occupations")
    print(f"Matched Anthropic exposure: {matched}/{len(data)}")


if __name__ == "__main__":
    main()

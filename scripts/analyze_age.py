"""How long have the failed lab tests been on record? Median days since each village's most recent failed test.

Reads data/snapshot/ (FY 2026-27), writes data/analysis/days_since_test.json. Usage: python scripts/analyze_age.py
"""

from __future__ import annotations

import json
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from jalsaathi import parse  # noqa: E402

AS_OF = date(2026, 10, 9)  # the snapshot date


def analyse() -> dict:
    snap = ROOT / "data" / "snapshot"
    latest: dict[tuple, int] = {}
    for f in json.loads((snap / "manifest.json").read_text(encoding="utf-8"))["files"]:
        if not f["fy"].startswith("2026"):
            continue
        for v in json.loads((snap / f["file"]).read_text(encoding="utf-8"))["villages"]:
            for s in v.get("samples") or []:
                r = parse.sample_from_portal(v, s, f["param"])
                if r.get("lab_approval"):
                    days = (AS_OF - date.fromisoformat(r["lab_approval"][:10])).days
                    key = (v.get("VillageId"), f["param"])
                    latest[key] = min(latest.get(key, 10**6), days)
    vals = sorted(latest.values())
    return {
        "question": "How many days before the snapshot was each village's most recent failed lab test (per parameter)?",
        "as_of": AS_OF.isoformat(), "village_parameter_failures": len(vals),
        "median_days": statistics.median(vals), "p25_days": vals[len(vals) // 4], "p75_days": vals[3 * len(vals) // 4],
        "max_days": vals[-1], "share_over_60_days": round(sum(v > 60 for v in vals) / len(vals), 3),
        "share_over_90_days": round(sum(v > 90 for v in vals) / len(vals), 3),
        "caveat": "The portal records the failure; we found nothing in it that tells the village or forces a fix. "
                  "We cannot see whether villages were told some other way.",
    }


if __name__ == "__main__":
    result = analyse()
    out = ROOT / "data" / "analysis" / "days_since_test.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"median {result['median_days']} days; {result['share_over_60_days']:.0%} over 60 days ({result['village_parameter_failures']} failures)")

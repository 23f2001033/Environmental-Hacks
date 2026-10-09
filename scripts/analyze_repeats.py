"""Proof from real data: villages that failed in FY 2025-26 and failed again in FY 2026-27 (same parameter).

Reads data/snapshot/, writes data/analysis/repeat_failures.json. Usage: python scripts/analyze_repeats.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAP = ROOT / "data" / "snapshot"


def village_ids(fy: str, state: str, param: str) -> dict[int, dict]:
    path = SNAP / f"wqmis_{fy}_{state.replace(' ', '')}_{param.replace(' ', '')}.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {v["VillageId"]: v for v in data["villages"] if v.get("VillageId")}


def analyse() -> dict:
    manifest = json.loads((SNAP / "manifest.json").read_text(encoding="utf-8"))
    combos = sorted({(f["state"], f["param"]) for f in manifest["files"]})
    rows, totals = [], {"last_year": 0, "this_year": 0, "both": 0}
    for state, param in combos:
        last, this = village_ids("2025-2026", state, param), village_ids("2026-2027", state, param)
        both = sorted(set(last) & set(this))
        if not last and not this:
            continue
        rows.append({
            "state": state, "parameter": param, "failed_last_year": len(last), "failed_this_year": len(this),
            "failed_both_years": len(both),
            "share_of_last_year_failing_again": round(len(both) / len(last), 3) if last else None,
            "examples": [f"{this[i]['Village']} ({this[i]['Block']}, {this[i]['District']})" for i in both[:5]],
        })
        totals["last_year"] += len(last)
        totals["this_year"] += len(this)
        totals["both"] += len(both)
    totals["share_of_last_year_failing_again"] = round(totals["both"] / totals["last_year"], 3) if totals["last_year"] else None
    return {
        "question": "Of the villages whose drinking-water samples failed in FY 2025-26, how many failed again for the same parameter in FY 2026-27 (April to 9 Oct 2026)?",
        "source": "JJM-WQMIS Format WQ6, piped-water sources, lab tests; snapshot " + manifest.get("written_at", ""),
        "caveats": [
            "FY 2026-27 covers only April to early October, so the repeat share will rise as the year goes on.",
            "A village counts once per parameter even if several samples failed.",
            "Failing again does not prove nothing was fixed; it shows the problem was still there at the next test.",
        ],
        "totals": totals,
        "by_state_and_parameter": rows,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


if __name__ == "__main__":
    result = analyse()
    out = ROOT / "data" / "analysis" / "repeat_failures.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    t = result["totals"]
    print(f"failed last year: {t['last_year']}, this year: {t['this_year']}, both: {t['both']} "
          f"({t['share_of_last_year_failing_again']:.1%} of last year's)")
    for r in result["by_state_and_parameter"]:
        print(f"  {r['state']:14} {r['parameter']:14} last {r['failed_last_year']:4} this {r['failed_this_year']:4} both {r['failed_both_years']:4}")

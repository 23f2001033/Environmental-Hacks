"""Contaminant classes, severity and deadlines. Plain code: no model decides any of this (DECISIONS.md D-06)."""

from __future__ import annotations

from . import parse

# WQMIS parameter names and the aliases we accept -> our codes.
_ALIASES = {
    "ecoil": "ecoli", "ecoli": "ecoli", "e. coli": "ecoli", "e.coli": "ecoli", "totalecoil": "ecoli",
    "coliform": "coliform", "totalcoliform": "coliform", "total coliform": "coliform",
    "nitrate": "nitrate",
    "fluoride": "fluoride",
    "total arsenic": "arsenic", "totalarsenic": "arsenic", "arsenic": "arsenic",
    "iron": "iron",
    "tds": "tds",
    "turbidity": "turbidity",
    "residual chlorine": "chlorine", "residual_chlorine": "chlorine", "chlorine": "chlorine",
}

CLASS = {
    "ecoli": "microbial", "coliform": "microbial", "chlorine": "microbial",
    "nitrate": "chemical", "fluoride": "chemical", "arsenic": "chemical",
    "turbidity": "physical", "iron": "aesthetic", "tds": "aesthetic",
}

# Fallback limits (IS 10500:2012) when a sample arrives without its own.
DEFAULT_LIMITS = {
    "ecoli": (0, 0), "coliform": (0, 0), "nitrate": (45, 45), "fluoride": (1.0, 1.5),
    "arsenic": (0.01, 0.05), "turbidity": (1, 5), "iron": (1.0, 1.0), "tds": (500, 2000), "chlorine": (0.2, 1.0),
}

SEVERITY_ORDER = {"red": 0, "amber": 1, "yellow": 2, "review": 3}

# (fix deadline, re-test deadline) in seconds.
_DEADLINES = {
    "red": (48 * 3600, 7 * 86400),
    "amber": (7 * 86400, 14 * 86400),
    "yellow": (30 * 86400, 30 * 86400),
    "review": (7 * 86400, 14 * 86400),
}
_DEMO_DEADLINES = {"red": (240, 300), "amber": (360, 420), "yellow": (480, 480), "review": (360, 420)}
_LAB_WAIT = 30 * 86400
_DEMO_LAB_WAIT = 900


def param_code(name: str | None) -> str | None:
    if not name:
        return None
    key = str(name).strip().lower()
    return _ALIASES.get(key) or _ALIASES.get(key.replace(" ", ""))


def contaminant_class(code: str | None) -> str:
    return CLASS.get(code or "", "unknown")


def severity(code: str | None, value: float | None, acceptable: float | None = None, permissible: float | None = None) -> str:
    """red = act today, amber = this week, yellow = monitor, review = a person must look."""
    if code not in CLASS or value is None:
        return "review"
    acc, perm = acceptable, permissible
    if acc is None or perm is None:
        d_acc, d_perm = DEFAULT_LIMITS[code]
        acc = d_acc if acc is None else acc
        perm = d_perm if perm is None else perm

    if code in ("ecoli", "coliform"):
        return "red" if value > acc else "review"
    if code == "chlorine":
        return "amber" if value < acc else "review"
    if code in ("nitrate", "arsenic"):
        if value > perm:
            return "red"
        return "amber" if value > acc else "review"
    if code in ("fluoride", "turbidity", "tds"):
        if value > perm:
            return "amber"
        return "yellow" if value > acc else "review"
    if code == "iron":
        return "yellow" if value > acc else "review"
    return "review"


def timers(sev: str, demo: bool) -> dict:
    fix, retest = (_DEMO_DEADLINES if demo else _DEADLINES).get(sev, _DEADLINES["review"])
    return {"fix_seconds": fix, "retest_seconds": retest, "lab_seconds": _DEMO_LAB_WAIT if demo else _LAB_WAIT}


def case_id(state_id, village_key: str, code: str) -> str:
    """Stable, Step Functions-safe ID: one case per village and contaminant."""
    return ("c-" + parse.slug(state_id, village_key, code))[:80]

"""Locations of bundled files. Works both from the repo and inside the Lambda bundle."""

from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _find(name: str) -> Path:
    # In the repo: src/jalsaathi/../../<name>. In Lambda: <bundle>/<name> next to the package.
    for base in (_HERE.parent.parent, _HERE.parent):
        candidate = base / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(name)


def content_file(name: str) -> Path:
    return _find("content") / name


def policies_file(name: str) -> Path:
    return _find("policies") / name


def fixtures_file(name: str) -> Path:
    return _find("data") / "fixtures" / name

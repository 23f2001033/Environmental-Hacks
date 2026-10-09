"""Build the Lambda bundle (build/lambda) and the dependency layer (build/layer) for Linux arm64.

Usage: python scripts/build.py [--force-layer]
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"


def build_lambda() -> None:
    out = BUILD / "lambda"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(ROOT / "src" / "jalsaathi", out / "jalsaathi", ignore=ignore)
    shutil.copytree(ROOT / "content", out / "content")
    shutil.copytree(ROOT / "policies", out / "policies")
    shutil.copytree(ROOT / "data" / "fixtures", out / "data" / "fixtures")
    shutil.copytree(ROOT / "data" / "analysis", out / "data" / "analysis")
    print(f"lambda bundle: {out}")


def build_layer(force: bool = False) -> None:
    target = BUILD / "layer" / "python"
    stamp = BUILD / "layer" / ".requirements"
    req = (ROOT / "requirements.txt").read_text()
    if not force and target.exists() and stamp.exists() and stamp.read_text() == req:
        print("layer: up to date")
        return
    shutil.rmtree(BUILD / "layer", ignore_errors=True)
    cmd = ["uv", "pip", "install", "--target", str(target), "--python-platform", "aarch64-manylinux2014",
           "--python-version", "3.12", "--only-binary", ":all:", "-r", str(ROOT / "requirements.txt")]
    subprocess.run(cmd, check=True)
    stamp.write_text(req)
    print(f"layer: {target}")


if __name__ == "__main__":
    build_lambda()
    build_layer(force="--force-layer" in sys.argv)

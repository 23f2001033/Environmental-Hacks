"""Build the small geography file behind the About-page map: state outlines, rivers and reference cities.

Source: Natural Earth 1:10m, v5.1.2 (public domain): admin-1 states and rivers/lake centrelines. Download once:
  https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_10m_admin_1_states_provinces.geojson
  https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_10m_rivers_lake_centerlines.geojson
Usage: python scripts/build_map_shapes.py <admin1.geojson> <rivers.geojson>
Writes frontend/src/map-shapes.json (simplified, a few tens of KB).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BBOX = (68.6, 23.0, 85.2, 31.0)  # west, south, east, north: Rajasthan and Uttar Pradesh with a margin
FOCUS = {"Rajasthan", "Uttar Pradesh"}
NEIGHBOURS = {"Punjab", "Haryana", "Delhi", "Uttarakhand", "Madhya Pradesh", "Gujarat", "Bihar", "Himachal Pradesh",
              "Jharkhand", "Chhattisgarh"}
RIVERS = {"Ganges", "Ganga", "Yamuna", "Chambal", "Ghaghara", "Gomati", "Gomti", "Betwa", "Son", "Luni", "Banas",
          "Sarda", "Ramganga", "Gandak", "Ken", "Sindh", "Mahi", "Rapti", "Tons"}
# Well-known reference points (city centres), for orientation only
CITIES = [("Jaipur", 75.79, 26.91), ("Jodhpur", 73.02, 26.24), ("Bikaner", 73.31, 28.02), ("Kota", 75.83, 25.18),
          ("Udaipur", 73.71, 24.59), ("Lucknow", 80.95, 26.85), ("Kanpur", 80.33, 26.45), ("Agra", 78.01, 27.18),
          ("Varanasi", 82.97, 25.32), ("Gorakhpur", 83.37, 26.76), ("Delhi", 77.21, 28.61)]


def simplify(points: list, tol: float) -> list:
    """Douglas-Peucker on [lon, lat] points."""
    if len(points) < 3:
        return points
    (x1, y1), (x2, y2) = points[0], points[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = (dx * dx + dy * dy) ** 0.5 or 1e-12
    dmax, idx = 0.0, 0
    for i in range(1, len(points) - 1):
        x, y = points[i]
        d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norm
        if d > dmax:
            dmax, idx = d, i
    if dmax <= tol:
        return [points[0], points[-1]]
    return simplify(points[: idx + 1], tol)[:-1] + simplify(points[idx:], tol)


def simplify_ring(ring: list, tol: float) -> list:
    """A closed ring starts and ends at the same point, so simplify its two halves separately."""
    mid = len(ring) // 2
    return simplify(ring[: mid + 1], tol)[:-1] + simplify(ring[mid:], tol)


def inside(p) -> bool:
    return BBOX[0] <= p[0] <= BBOX[2] and BBOX[1] <= p[1] <= BBOX[3]


def rnd(points: list) -> list:
    return [[round(x, 3), round(y, 3)] for x, y in points]


def polygons(geom: dict) -> list[list]:
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    if geom["type"] == "MultiPolygon":
        return [poly[0] for poly in geom["coordinates"]]
    return []


def lines(geom: dict) -> list[list]:
    if geom["type"] == "LineString":
        return [geom["coordinates"]]
    if geom["type"] == "MultiLineString":
        return geom["coordinates"]
    return []


def main(admin1: str, rivers: str) -> None:
    states = []
    for f in json.loads(Path(admin1).read_text(encoding="utf-8"))["features"]:
        p = f["properties"]
        if p.get("adm0_a3") != "IND" or p.get("name") not in FOCUS | NEIGHBOURS:
            continue
        rings = [rnd(simplify_ring(ring, 0.02 if p["name"] in FOCUS else 0.04)) for ring in polygons(f["geometry"])]
        rings = [r for r in rings if len(r) > 3 and any(inside(pt) for pt in r)]
        if rings:
            states.append({"name": p["name"], "focus": p["name"] in FOCUS, "rings": rings})
    river_out: dict[str, list] = {}
    for f in json.loads(Path(rivers).read_text(encoding="utf-8"))["features"]:
        p = f["properties"]
        name = (p.get("name_en") or p.get("name") or "").strip()
        if not any(k.lower() in name.lower() for k in RIVERS):
            continue
        for line in lines(f["geometry"]):
            seg: list = []
            for pt in line:
                if inside(pt):
                    seg.append(pt)
                elif seg:
                    if len(seg) > 1:
                        river_out.setdefault(name, []).append(rnd(simplify(seg, 0.01)))
                    seg = []
            if len(seg) > 1:
                river_out.setdefault(name, []).append(rnd(simplify(seg, 0.01)))
    out = {"source": "Natural Earth 1:10m v5.1.2 (public domain); simplified", "bbox": BBOX,
           "states": states, "rivers": [{"name": n, "lines": ls} for n, ls in river_out.items()],
           "cities": [{"name": n, "lon": x, "lat": y} for n, x, y in CITIES]}
    target = ROOT / "frontend" / "src" / "map-shapes.json"
    target.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"{len(states)} states, {len(out['rivers'])} rivers, {target.stat().st_size // 1024} KB -> {target}")
    print("states:", sorted(s["name"] for s in states))
    print("rivers:", sorted(out["rivers"][i]["name"] for i in range(len(out["rivers"]))))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

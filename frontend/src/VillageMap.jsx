import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { useNavigate } from "react-router-dom";
import { get } from "./api.js";
import { useLang } from "./i18n.jsx";

const ENTITIES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ENTITIES[c]);
const COLORS = { unsafe: "#c2412d", provisional: "#b26b00", safe_again: "#23804f", unknown: "#7b8b93" };

// Approximate pins (block or district centre) would stack exactly; spread them a little, on the map only.
function spread(key) {
  let h = 0;
  for (const ch of String(key)) h = (h * 31 + ch.charCodeAt(0)) | 0;
  const angle = ((h % 360) * Math.PI) / 180;
  const r = 0.01 + ((h >>> 9) % 100) / 4000;
  return [Math.cos(angle) * r, Math.sin(angle) * r];
}

function toGeoJson(villages) {
  return {
    type: "FeatureCollection",
    features: villages.filter((v) => v.lat != null).map((v) => {
      const approx = v.geo_precision !== "village";
      const [dx, dy] = approx ? spread(v.key) : [0, 0];
      return {
        type: "Feature",
        geometry: { type: "Point", coordinates: [v.lon + dx, v.lat + dy] },
        properties: { key: v.key, name: v.name, status: v.status, approx: approx ? 1 : 0, open: v.open_cases,
                      where: [v.block, v.district].filter(Boolean).join(", "), params: (v.parameters || []).join(", ") },
      };
    }),
  };
}

export default function VillageMap({ villages, height }) {
  const { t } = useLang();
  const box = useRef(null);
  const map = useRef(null);
  const navigate = useNavigate();
  const [ready, setReady] = useState(false);
  const [noMap, setNoMap] = useState(false);
  const [q, setQ] = useState("");
  const data = useMemo(() => toGeoJson(villages || []), [villages]);

  useEffect(() => {
    let alive = true;
    get("/config").then((cfg) => {
      if (!alive || !box.current) return;
      if (!cfg.map || !cfg.map.style_url) { setNoMap(true); return; }
      const m = new maplibregl.Map({ container: box.current, style: cfg.map.style_url, center: cfg.map.center, zoom: cfg.map.zoom,
                                     attributionControl: { compact: true } });
      m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      m.on("load", () => {
        m.addSource("villages", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
        const color = ["match", ["get", "status"], "unsafe", COLORS.unsafe, "provisional", COLORS.provisional, "safe_again", COLORS.safe_again, COLORS.unknown];
        m.addLayer({ id: "villages-glow", type: "circle", source: "villages", filter: ["==", ["get", "status"], "unsafe"],
                     paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 6, 10, 16], "circle-color": COLORS.unsafe, "circle-opacity": 0.12 } });
        m.addLayer({ id: "villages", type: "circle", source: "villages", paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 3.2, 8, 6, 12, 9],
          "circle-color": ["case", ["==", ["get", "approx"], 1], "rgba(255,255,255,0.6)", color],
          "circle-stroke-color": color, "circle-stroke-width": ["case", ["==", ["get", "approx"], 1], 2, 1.2] } });
        const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
        m.on("mouseenter", "villages", (e) => {
          m.getCanvas().style.cursor = "pointer";
          const p = e.features[0].properties;
          popup.setLngLat(e.features[0].geometry.coordinates).setHTML(
            `<b>${esc(p.name)}</b><br><span style="color:#587080">${esc(p.where)}</span><br>${esc(p.params)}`).addTo(m);
        });
        m.on("mouseleave", "villages", () => { m.getCanvas().style.cursor = ""; popup.remove(); });
        m.on("click", "villages", (e) => navigate(`/village/${e.features[0].properties.key}`));
        setReady(true);
      });
      map.current = m;
    }).catch(() => setNoMap(true));
    return () => { alive = false; if (map.current) map.current.remove(); map.current = null; };
  }, [navigate]);

  useEffect(() => {
    if (ready && map.current && map.current.getSource("villages")) map.current.getSource("villages").setData(data);
  }, [ready, data]);

  const matches = q.trim().length < 2 ? [] : (villages || []).filter((v) =>
    `${v.name} ${v.block} ${v.district}`.toLowerCase().includes(q.trim().toLowerCase())).slice(0, 8);

  return (
    <div className="card map-card">
      <div className="map-tools">
        <input className="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("search")} aria-label={t("search")} />
        {q.trim().length >= 2 && (
          <div className="results">
            {matches.length ? matches.map((v) => (
              <a key={v.key} href={`/village/${v.key}`} onClick={(e) => { e.preventDefault(); navigate(`/village/${v.key}`); }}>
                <b>{v.name}</b> <span className="small muted">{v.block}, {v.district}</span>
              </a>
            )) : <div className="small muted" style={{ padding: 10 }}>{t("no_match")}</div>}
          </div>
        )}
      </div>
      {noMap ? <div className="map" style={{ height, display: "grid", placeItems: "center" }}>Map unavailable</div>
        : <div ref={box} className="map" style={height ? { height } : undefined} />}
      <div className="legend">
        <span><i className="dot unsafe" />{t("legend_unsafe")}</span>
        <span><i className="dot provisional" />{t("legend_provisional")}</span>
        <span><i className="dot safe_again" />{t("legend_safe")}</span>
        <span><i className="dot ring" />{t("legend_approx")}</span>
      </div>
    </div>
  );
}

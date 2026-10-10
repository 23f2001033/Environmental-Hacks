import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";

export async function mountMap(container, villages, config, onSelect) {
  const [maplibre] = await Promise.all([
    import("maplibre-gl"),
    import("maplibre-gl/dist/maplibre-gl.css"),
  ]);
  if (!container.isConnected) return null;
  // Let Vite serve/copy the worker explicitly in both dev and production.
  maplibre.setWorkerUrl(workerUrl);
  const map = new maplibre.Map({
    container,
    style: config.style_url,
    center: config.center || [78.5, 26.5],
    zoom: config.zoom ?? 5,
  });
  map.addControl(new maplibre.NavigationControl());
  map.on("error", () => {
    if (container.isConnected && !map.loaded())
      container.setAttribute("data-map-error", "true");
  });
  map.on("load", () => {
    const points = villages.filter(
      (v) => Number.isFinite(v.lon) && Number.isFinite(v.lat),
    );
    map.addSource("villages", {
      type: "geojson",
      data: {
        type: "FeatureCollection",
        features: points.map((v) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [v.lon, v.lat] },
          properties: {
            key: v.key,
            approximate: v.geo_precision !== "village",
            status: v.status,
          },
        })),
      },
    });
    const color = [
      "match",
      ["get", "status"],
      "unsafe",
      "#b43c35",
      "safe_again",
      "#287553",
      "provisional",
      "#966315",
      "#536879",
    ];
    map.addLayer({
      id: "village-points",
      source: "villages",
      type: "circle",
      paint: {
        "circle-radius": 7,
        "circle-color": ["case", ["get", "approximate"], "#ffffff", color],
        "circle-stroke-width": 2,
        "circle-stroke-color": color,
      },
    });
    map.on("click", "village-points", (ev) =>
      onSelect(ev.features[0].properties.key),
    );
    map.on("mouseenter", "village-points", () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "village-points", () => {
      map.getCanvas().style.cursor = "";
    });
  });
  return map;
}

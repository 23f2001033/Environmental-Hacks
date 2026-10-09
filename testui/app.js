// JalSaathi test console. Talks only to /api/v1 (same origin). See docs/API.md.
(function () {
  "use strict";
  const API = "/api/v1";
  let lang = "hi";
  let current = null;
  let villages = [];
  let map = null;
  const COLORS = { unsafe: "#b23a22", provisional: "#946000", safe_again: "#2c7a39", unknown: "#77858a" };

  const $ = (sel) => document.querySelector(sel);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const token = () => { try { return localStorage.getItem("js-admin-token") || ""; } catch { return ""; } };

  async function get(path) {
    const r = await fetch(API + path);
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
    return r.json();
  }
  async function admin(path, body) {
    const r = await fetch(API + "/admin/" + path, {
      method: "POST", headers: { "content-type": "application/json", "x-admin-token": token() }, body: JSON.stringify(body || {}),
    });
    const text = await r.text();
    $("#admin-out").textContent = `${r.status} ${path}\n${text}`;
    if (current) setTimeout(() => openVillage(current), 1500);
    setTimeout(loadVillages, 1500);
    return r.ok;
  }

  const secs = (s) => (s == null ? "-" : s < 120 ? `${s}s` : s < 7200 ? `${Math.round(s / 60)} min` : `${(s / 3600).toFixed(1)} h`);

  async function loadStats() {
    try {
      const s = await get("/stats");
      const r = s.last_run;
      const run = r ? `Last ingest: ${esc(r.source)} · ${r.cases_planned} cases planned · ${r.new_cases} new · ${r.villages_located ?? "-"}/${r.villages ?? "-"} villages located · data as of ${esc(r.data_as_of)} · took ${secs(r.seconds)}` : "No ingest yet.";
      const lat = s.alert_latency;
      const sc = s.scale_run;
      const rep = s.repeat_failures && s.repeat_failures.totals;
      const cost = r && r.cost_estimate;
      $("#stats").innerHTML = `<strong>${s.villages}</strong> villages (${s.villages_on_map} on map) · <strong>${s.open_cases}</strong> open cases · <strong>${s.closed_cases}</strong> closed
        <div class="sub">${run}</div>
        <div class="grid">
          <div><strong>Test found → village warned</strong><br>${lat ? `median ${secs(lat.median_s)} · p95 ${secs(lat.p95_s)} · ${lat.cases} cases` : "no alerts yet"}</div>
          <div><strong>Scale run</strong><br>${sc ? `${esc(sc.status)} · ${sc.items ? `${sc.items.succeeded}/${sc.items.total} started, ${sc.items.failed} failed` : ""} ${sc.seconds ? "· " + secs(sc.seconds) : ""}` : "not run"}</div>
          <div><strong>Failed again next year</strong><br>${rep ? `${rep.both} of ${rep.last_year} villages (${Math.round(rep.share_of_last_year_failing_again * 1000) / 10}%)` : "-"}</div>
          <div><strong>Estimated AWS cost of last run</strong><br>${cost ? `$${cost.usd_total} (${cost.usd_per_case ? "$" + cost.usd_per_case + " per case" : "-"})` : "-"}</div>
        </div>`;
    } catch (e) { $("#stats").textContent = "API not reachable: " + e.message; }
  }

  function renderVillages() {
    const q = ($("#filter").value || "").toLowerCase();
    const shown = villages.filter((v) => !q || `${v.name} ${v.block} ${v.district} ${v.state}`.toLowerCase().includes(q));
    $("#villages").innerHTML = villages.length ? shown.slice(0, 150).map((v) => `
        <div class="vrow" data-key="${esc(v.key)}">
          <span><strong>${esc(v.name)}</strong> <span class="sub">${esc(v.block)}, ${esc(v.district)}, ${esc(v.state)}${v.source === "fixtures" ? " · demo" : ""}</span></span>
          <span><span class="pill ${esc(v.worst_severity || v.status)}">${esc(v.parameters.join(", "))}</span>
                <span class="pill ${esc(v.status)}">${esc(v.status)}</span></span>
        </div>`).join("") + (shown.length > 150 ? `<div class="sub">${shown.length - 150} more; search to narrow down.</div>` : "")
      : "No villages yet. Use Demo controls → Ingest demo records.";
    document.querySelectorAll(".vrow").forEach((el) => el.addEventListener("click", () => openVillage(el.dataset.key)));
  }

  // Approximate points (block or district centre) would stack exactly; spread them a little, on the map only.
  function spread(key) {
    let h = 0;
    for (const ch of String(key)) h = (h * 31 + ch.charCodeAt(0)) | 0;
    const angle = (h % 360) * Math.PI / 180, r = 0.01 + ((h >>> 9) % 100) / 4000;
    return [Math.cos(angle) * r, Math.sin(angle) * r];
  }

  function geojson() {
    return { type: "FeatureCollection", features: villages.filter((v) => v.lat != null).map((v) => {
      const approx = v.geo_precision !== "village";
      const [dx, dy] = approx ? spread(v.key) : [0, 0];
      return { type: "Feature", geometry: { type: "Point", coordinates: [v.lon + dx, v.lat + dy] },
        properties: { key: v.key, name: v.name, status: v.status, block: approx ? 1 : 0 } };
    }) };
  }

  async function initMap() {
    let cfg;
    try { cfg = await get("/config"); } catch (e) { $("#map").textContent = "Map config unavailable."; return; }
    if (!cfg.map.style_url || !window.maplibregl) { $("#map").textContent = "Map not configured."; return; }
    $("#map").innerHTML = "";
    map = new maplibregl.Map({ container: "map", style: cfg.map.style_url, center: cfg.map.center, zoom: cfg.map.zoom });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.on("load", () => {
      map.addSource("villages", { type: "geojson", data: geojson() });
      const color = ["match", ["get", "status"], "unsafe", COLORS.unsafe, "provisional", COLORS.provisional, "safe_again", COLORS.safe_again, COLORS.unknown];
      map.addLayer({ id: "villages", type: "circle", source: "villages", paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 3, 10, 8],
        "circle-color": ["case", ["==", ["get", "block"], 1], "rgba(0,0,0,0)", color],
        "circle-stroke-color": color, "circle-stroke-width": ["case", ["==", ["get", "block"], 1], 2, 1] } });
      map.on("click", "villages", (e) => openVillage(e.features[0].properties.key));
      map.on("mouseenter", "villages", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "villages", () => { map.getCanvas().style.cursor = ""; });
    });
  }

  async function loadVillages() {
    loadStats();
    try {
      villages = (await get("/villages")).villages;
      renderVillages();
      if (map && map.getSource("villages")) map.getSource("villages").setData(geojson());
    } catch (e) { $("#villages").textContent = e.message; }
  }

  function timeline(rows) {
    if (!rows || !rows.length) return "";
    return `<table><tr><th>Time</th><th>Event</th><th>Details</th></tr>${rows.map((e) => `
      <tr><td>${esc((e.at || "").replace("T", " ").slice(0, 19))}</td><td>${esc(e.kind)}</td>
      <td>${e.decision ? `<span class="${e.decision}">${esc(e.decision)}</span> ${esc(e.action || "")} · ${esc(e.reason || "")}` : ""}
          ${esc(e.note || "")} ${e.result ? "→ " + esc(e.result) : ""} ${e.actor && e.actor !== "system" ? `<span class="sub">(${esc(e.actor)})</span>` : ""}</td></tr>`).join("")}</table>`;
  }

  function caseBlock(c) {
    const audio = c.audio_url ? `<audio controls preload="none" src="${esc(c.audio_url)}"></audio>` : `<span class="sub">voice note not generated yet</span>`;
    return `<div class="case">
      <h3>${esc(c.parameter_name[lang])} <span class="pill ${esc(c.severity)}">${esc(c.severity)}</span> <span class="pill">${esc(c.status)}</span></h3>
      <div class="facts">
        <span>${lang === "hi" ? "मात्रा" : "Measured"}: <strong>${esc(c.value)} ${esc(c.unit || "")}</strong> (${lang === "hi" ? "सीमा" : "limit"} ${esc(c.acceptable_limit)})</span>
        <span>${lang === "hi" ? "लैब जांच" : "Lab test"}: ${esc((c.lab_approval || "").slice(0, 10))}</span>
        <span>${esc(c.source_type || "")} · scheme ${esc(c.scheme_id || "-")}</span>
        ${c.sample_id ? `<span>sample ${esc(c.sample_id)}</span>` : ""}
      </div>
      <ol>${c.advice[lang].map((a) => `<li>${esc(a)}</li>`).join("")}</ol>
      ${audio}
      <div class="row">
        <button class="ghost" data-act="engineer-action" data-case="${esc(c.case_id)}">Engineer: chlorination done</button>
        <button class="ghost" data-act="try-close" data-case="${esc(c.case_id)}">Engineer: close case</button>
        <button class="ghost" data-act="kit-clean" data-case="${esc(c.case_id)}">Kit: clean</button>
        <button class="ghost" data-act="kit-dirty" data-case="${esc(c.case_id)}">Kit: contaminated</button>
        <button class="ghost" data-act="lab-pass" data-case="${esc(c.case_id)}">Lab: pass (simulated)</button>
        <button class="ghost" data-act="lab-fail" data-case="${esc(c.case_id)}">Lab: fail (simulated)</button>
      </div>
      <details><summary>Timeline</summary>${timeline(c.timeline)}</details>
    </div>`;
  }

  async function openVillage(key) {
    current = key;
    const el = $("#detail");
    el.hidden = false;
    try {
      const b = await get("/villages/" + encodeURIComponent(key));
      el.innerHTML = `
        <h2>${esc(b.village.name)} <span class="sub">${esc(b.village.block)}, ${esc(b.village.district)}, ${esc(b.village.state)}</span></h2>
        <div class="status ${esc(b.status)}">${esc(b.status_text[lang])}</div>
        <div class="join">
          <div id="qr"></div>
          <div>
            <div>Telegram (village): <a href="${esc(b.links.telegram_join)}" target="_blank" rel="noopener">${esc(b.links.telegram_join)}</a></div>
            <div>Telegram (engineer, block): <a href="${esc(b.links.engineer_join)}" target="_blank" rel="noopener">${esc(b.links.engineer_join)}</a></div>
            <div class="sub">Data: ${esc(b.source)}, as of ${esc(b.data_as_of)}</div>
            <button class="ghost" id="print-poster" type="button">Print poster</button>
          </div>
        </div>
        ${b.cases.map(caseBlock).join("")}`;
      if (window.QRCode) new QRCode($("#qr"), { text: b.links.telegram_join, width: 110, height: 110 });
      $("#print-poster").addEventListener("click", () => poster(b));
      el.querySelectorAll("[data-act]").forEach((btn) => btn.addEventListener("click", () => act(btn.dataset.act, btn.dataset.case)));
    } catch (e) { el.textContent = e.message; }
  }

  function act(kind, caseId) {
    const map = {
      "engineer-action": ["engineer-action", { action: "chlorination" }], "try-close": ["try-close", {}],
      "kit-clean": ["kit-result", { result: "clean" }], "kit-dirty": ["kit-result", { result: "contaminated" }],
      "lab-pass": ["lab-result", { result: "pass" }], "lab-fail": ["lab-result", { result: "fail" }],
    };
    const [path, body] = map[kind];
    admin(path, { case_id: caseId, ...body });
  }

  function poster(b) {
    const c = b.cases.find((x) => x.status !== "CLOSED") || b.cases[0];
    $("#poster").innerHTML = `<div class="poster">
      <h1>⚠️ ${esc(b.village.name)}: ${esc(b.status_text.hi)}</h1>
      ${c ? `<p>पानी की जांच में <strong>${esc(c.parameter_name.hi)}</strong> मिला (${esc(c.value)} ${esc(c.unit || "")}, सीमा ${esc(c.acceptable_limit)}).</p>
      <ol>${c.advice.hi.map((a) => `<li>${esc(a)}</li>`).join("")}</ol>` : ""}
      <div id="qr-poster"></div><p>स्कैन करें: Telegram पर सूचना पाएं · स्रोत: JJM-WQMIS, ${esc(b.data_as_of)}</p></div>`;
    $("#poster").hidden = false;
    if (window.QRCode) new QRCode($("#qr-poster"), { text: b.links.telegram_join, width: 160, height: 160 });
    setTimeout(() => window.print(), 300);
  }

  $("#lang").addEventListener("click", () => { lang = lang === "hi" ? "en" : "hi"; $("#lang").textContent = lang === "hi" ? "English" : "हिंदी"; if (current) openVillage(current); });
  $("#save-token").addEventListener("click", () => { try { localStorage.setItem("js-admin-token", $("#token").value.trim()); } catch {} $("#admin-out").textContent = "Token saved in this browser."; });
  document.querySelectorAll("[data-admin]").forEach((b) => b.addEventListener("click", () => {
    if (b.dataset.admin === "scale-run" && !confirm("Start a workflow for every real WQMIS failure in the snapshot (about 580 cases, real deadlines)?")) return;
    if (b.dataset.admin === "reset" && !confirm("Stop all workflows and delete all cases and villages?")) return;
    admin(b.dataset.admin, b.dataset.admin === "ingest" ? { source: "fixtures" } : {});
  }));
  $("#filter").addEventListener("input", renderVillages);
  const params = new URLSearchParams(location.search);
  initMap();
  loadVillages();
  setInterval(loadStats, 15000);
  if (params.get("v")) openVillage(params.get("v"));
})();

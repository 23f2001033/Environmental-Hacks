// JalSaathi test console. Talks only to /api/v1 (same origin). See docs/API.md.
(function () {
  "use strict";
  const API = "/api/v1";
  let lang = "hi";
  let current = null;

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

  async function loadStats() {
    try {
      const s = await get("/stats");
      const run = s.last_run ? `Last ingest: ${esc(s.last_run.source)} · ${s.last_run.cases_planned} cases planned · ${s.last_run.new_cases} new · data as of ${esc(s.last_run.data_as_of)}` : "No ingest yet.";
      $("#stats").innerHTML = `<strong>${s.villages}</strong> villages · <strong>${s.open_cases}</strong> open cases · <strong>${s.closed_cases}</strong> closed<div class="sub">${run}</div>`;
    } catch (e) { $("#stats").textContent = "API not reachable: " + e.message; }
  }

  async function loadVillages() {
    loadStats();
    try {
      const { villages } = await get("/villages");
      $("#villages").innerHTML = villages.length ? villages.map((v) => `
        <div class="vrow" data-key="${esc(v.key)}">
          <span><strong>${esc(v.name)}</strong> <span class="sub">${esc(v.block)}, ${esc(v.district)}, ${esc(v.state)}</span></span>
          <span><span class="pill ${esc(v.worst_severity || v.status)}">${esc(v.parameters.join(", "))}</span>
                <span class="pill ${esc(v.status)}">${esc(v.status)}</span></span>
        </div>`).join("") : "No villages yet. Use Demo controls → Ingest demo records.";
      document.querySelectorAll(".vrow").forEach((el) => el.addEventListener("click", () => openVillage(el.dataset.key)));
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
  document.querySelectorAll("[data-admin]").forEach((b) => b.addEventListener("click", () => admin(b.dataset.admin, b.dataset.admin === "ingest" ? { source: "fixtures" } : {})));
  const params = new URLSearchParams(location.search);
  loadVillages();
  if (params.get("v")) openVillage(params.get("v"));
})();

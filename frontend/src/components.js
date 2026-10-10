import { t, language, local, words, pair, eventNames } from "./i18n.js";
import {
  escapeHTML as e,
  safeURL,
  formatDate,
  caseProgress,
  routeURL,
  sortCases,
} from "./model.js";

const paths = {
  drop: '<path d="M12 2C9 7 4 11 4 15a8 8 0 0 0 16 0c0-4-5-8-8-13Z"/><path d="M8 16a4 4 0 0 0 4 3"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  pin: '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
  arrow: '<path d="m9 5 7 7-7 7"/>',
  speaker:
    '<path d="M11 4 5 9H2v6h3l6 5V4Z"/><path d="M15 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/>',
  alert:
    '<path d="M10.3 3.7 2 18a2 2 0 0 0 1.7 3h16.6a2 2 0 0 0 1.7-3L13.7 3.7a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4m0 4v.1"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  print:
    '<path d="M6 9V3h12v6M6 18H3V9h18v9h-3M6 15h12v7H6Z"/><path d="M17 12h1"/>',
  send: '<path d="m22 2-7 20-4-9-9-4 20-7ZM11 13 22 2"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  share: '<path d="M12 16V2m-5 5 5-5 5 5M5 12H3v9h18v-9h-2"/>',
  x: '<path d="m6 6 12 12M6 18 18 6"/>',
  flask: '<path d="M9 2h6m-5 0v7L4 20q0 2 2 2h12q2 0 2-2L14 9V2M7 15h10"/>',
};
export function icon(name, cls = "") {
  return `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.drop}</svg>`;
}
export function badge(status) {
  return `<span class="badge ${e(status)}">${icon(status === "safe_again" ? "check" : status === "unsafe" ? "alert" : "clock")}${e(t(status))}</span>`;
}
export function link(href, label, cls = "button", glyph = "arrow") {
  const url = safeURL(href);
  return url
    ? `<a class="${cls}" href="${e(url)}" ${url.startsWith("https:") ? 'target="_blank" rel="noopener noreferrer"' : ""}>${icon(glyph)}${e(label)}</a>`
    : "";
}
export function shell(route, bundle) {
  const block = route.view === "block" ? route.key : bundle?.village?.block_key;
  document.documentElement.lang = language;
  document.querySelector("#header").innerHTML = `<div class="header-inner">
    <a class="brand" data-nav href="${routeURL("about", "", route.demo)}"><span class="brand-symbol">${icon("drop")}</span><span><strong>${e(t("brand"))}</strong><small>${e(t("tagline"))}</small></span></a>
    <nav aria-label="${language === "hi" ? "मुख्य मेन्यू" : "Main navigation"}">
      <a data-nav ${route.view === "about" ? 'aria-current="page"' : ""} href="${routeURL("about", "", route.demo)}">${e(t("about"))}</a>
      <a data-nav class="nav-primary" ${route.view === "directory" ? 'aria-current="page"' : ""} href="${routeURL("directory", "", route.demo)}">${icon("search")}<span>${e(t("villages"))}</span></a>
      ${block ? `<a data-nav ${route.view === "block" ? 'aria-current="page"' : ""} href="${routeURL("block", block, route.demo)}">${e(t("block"))}</a>` : ""}
    </nav>
    <div class="language-switch" role="group" aria-label="Language / भाषा">
      <button type="button" data-lang="hi" lang="hi" aria-pressed="${language === "hi"}">हिंदी</button>
      <button type="button" data-lang="en" lang="en" aria-pressed="${language === "en"}">English</button>
    </div></div>`;
  document.querySelector("#preview-notice").innerHTML = route.demo
    ? `<div class="preview-banner">${icon("flask")}<span>${e(t("preview"))}</span></div>`
    : "";
  document.querySelector("#footer").innerHTML =
    `<div class="footer-inner"><span class="footer-brand">${icon("drop")} ${e(t("brand"))}</span><div><p>${e(t("record"))}</p><p>${e(t("disclaimer"))}</p></div><a href="https://ejalshakti.gov.in/WQMIS/Main/report" target="_blank" rel="noopener noreferrer">JJM-WQMIS</a></div>`;
}

export function waterArt(status) {
  return `<div class="water-art ${e(status)}" aria-hidden="true"><svg viewBox="0 0 240 200" fill="none"><ellipse cx="120" cy="169" rx="90" ry="16"/><ellipse cx="120" cy="169" rx="65" ry="10"/><path class="droplet" d="M120 22c-16 26-51 53-51 85a51 51 0 0 0 102 0c0-32-35-59-51-85Z"/><path class="shine" d="M84 108c0 16 11 28 26 30"/><circle class="art-badge" cx="168" cy="127" r="29"/>${status === "safe_again" ? '<path class="art-symbol" d="m155 128 9 9 17-20"/>' : status === "unsafe" ? '<path class="art-symbol" d="M168 111v18m0 9v1"/>' : '<path class="art-symbol" d="M168 113v15l9 6"/>'}</svg></div>`;
}

function timeline(c) {
  const stages = caseProgress(c);
  return `<div class="case-journey"><h3>${e(local(c.parameter_name) || c.parameter)}</h3><ol class="progress-track">${stages.map((state, i) => `<li class="${state}" ${state === "current" ? 'aria-current="step"' : ""}><span class="step-mark">${state === "complete" ? icon("check") : i + 1}</span><strong>${e(pair(words.stages[i]))}</strong><small>${e(t(state))}</small></li>`).join("")}</ol>
    <details class="event-disclosure"><summary>${e(t("eventHistory"))}${icon("arrow")}</summary><ol class="events">${(c.timeline || []).map((event) => `<li><span class="event-dot"></span><div><strong>${e(pair(eventNames[event.kind]) || pair(["गतिविधि दर्ज हुई", "Activity recorded"]))}</strong>${event.result ? `<p>${e({ clean: pair(["साफ़", "Clean"]), contaminated: pair(["दूषित", "Contaminated"]), pass: pair(["पास", "Pass"]), fail: pair(["विफल", "Fail"]), grounded: pair(["जांचा हुआ जवाब भेजा", "Checked answer sent"]), fallback: pair(["सरकारी सलाह भेजी", "Official advice sent"]) }[event.result] || event.result)}</p>` : ""}${event.decision ? `<p>${e(event.decision === "deny" ? pair(["नियम ने अनुरोध रोका", "The rule denied the request"]) : pair(["नियम ने अनुरोध स्वीकार किया", "The rule allowed the request"]))}</p>` : ""}${/SIMULATED/i.test(event.note || "") ? `<small>${e(pair(["काल्पनिक घटना", "Simulated event"]))}</small>` : ""}<time datetime="${e(event.at)}">${e(formatDate(event.at, language, true))}</time></div></li>`).join("") || `<li>${e(t("noEvents"))}</li>`}</ol></details></div>`;
}

function caseAdvice(c) {
  const closed = c.status === "CLOSED";
  const urgency =
    { red: "actToday", amber: "actWeek", yellow: "monitor", review: "review" }[
      c.severity
    ] || "review";
  return `<article class="advice-case"><div class="case-heading"><span class="case-icon">${icon("flask")}</span><h3>${e(local(c.parameter_name) || c.parameter)}</h3><span class="urgency ${closed ? "resolved" : e(c.severity)}">${e(t(closed ? "resolved" : urgency))}</span></div>
    <div class="measurements"><div><span>${e(t("measured"))}</span><strong>${e(c.value ?? "—")} <small>${e(c.unit)}</small></strong></div><div><span>${e(t("limit"))}</span><strong>${e(c.acceptable_limit ?? "—")} <small>${e(c.unit)}</small></strong></div><div><span>${e(t("labDate"))}</span><strong class="date-value">${e(formatDate(c.lab_approval, language))}</strong></div></div>
    ${closed ? `<p class="muted">${e(t("closedAdvice"))}</p>` : ""}
    <ul class="advice-list">${(c.advice?.[language] || []).map((line, i) => `<li><span class="advice-symbol">${icon(c.actions?.[i] === "no_boil" ? "x" : c.actions?.[i] === "boil" ? "drop" : c.actions?.[i] === "ors" || c.actions?.[i] === "infant_warning" ? "alert" : "check")}</span><span>${e(line)}</span></li>`).join("")}</ul>
    ${closed ? "" : `<div class="audio-panel"><span class="audio-icon">${icon("speaker")}</span><div><strong>${e(t("listen"))}</strong>${safeURL(c.audio?.[language] || c.audio_url) ? `<audio controls preload="metadata" aria-label="${e(t("listen") + ": " + local(c.parameter_name))}" src="${e(safeURL(c.audio?.[language] || c.audio_url))}"></audio><p class="audio-error" hidden>${e(t("audioError"))}</p>` : `<p>${e(t("noAudio"))}</p>`}</div></div>`}
    <details class="test-disclosure"><summary>${e(t("details"))}${icon("arrow")}</summary><dl>${[
      ["source", c.source_type],
      ["scheme", c.scheme_name],
      ["lab", c.lab],
      ["sample", c.sample_id],
    ]
      .map(
        ([key, value]) =>
          `<div><dt>${e(t(key))}</dt><dd>${e(value || t("unavailable"))}</dd></div>`,
      )
      .join("")}</dl></details></article>`;
}

export function villagePage(bundle, route) {
  const v = bundle.village;
  const cases = sortCases(bundle.cases || []);
  const active = cases.filter((c) => c.status !== "CLOSED");
  const archived = cases.filter((c) => c.status === "CLOSED");
  const status = ["unsafe", "provisional", "safe_again", "unknown"].includes(
    bundle.status,
  )
    ? bundle.status
    : "unknown";
  return `<div class="breadcrumb"><a data-nav href="${routeURL("directory", "", route.demo)}">${e(t("villages"))}</a>${icon("arrow")}<span>${e(v.name)}</span><button class="text-button refresh" data-refresh>${icon("clock")}${e(t("refresh"))}</button></div>
    <section class="village-heading"><div><p class="location">${icon("pin")}${e([v.block, v.district, v.state].filter(Boolean).join(", "))}</p><h1>${e(v.name)}</h1></div><button class="button secondary" data-share>${icon("share")}${e(t("share"))}</button></section>
    <section class="water-notice ${status}" aria-labelledby="water-status"><div class="notice-copy">${badge(status)}<h2 id="water-status">${e(t(status))}</h2><p>${e(t(status + "Note"))}</p><div class="notice-date">${icon("clock")} ${e(t("asOf"))}: <time>${e(formatDate(bundle.data_as_of, language))}</time></div></div>${waterArt(status)}</section>
    <div class="village-layout"><div class="village-primary"><section class="advice-section"><div class="section-heading"><h2>${e(t(active.length ? "advice" : "historyAdvice"))}</h2><p>${e(t("adviceIntro"))}</p></div>${active.map(caseAdvice).join("")}${archived.length ? `<details class="archived"><summary>${e(t("historyAdvice"))} (${archived.length})</summary>${archived.map(caseAdvice).join("")}</details>` : ""}${!cases.length ? `<p class="empty">${e(t("unknownNote"))}</p>` : ""}</section>
    ${cases.length ? `<section class="journey-section"><div class="section-heading"><h2>${e(t("journey"))}</h2><p>${e(t("journeyNote"))}</p></div>${cases.map(timeline).join("")}</section>` : ""}</div>
    <aside class="village-sidebar"><section class="join-panel"><span class="big-icon">${icon("send")}</span><h2>${e(t("updates"))}</h2><p>${e(t("updatesNote"))}</p>${link(bundle.links?.telegram_join, t("join"), "button primary", "send")}</section><section class="poster-card"><div class="mini-poster" aria-hidden="true"><span></span><span></span><span></span><i>▦</i></div><h2>${e(t("poster"))}</h2><p>${e(t("posterNote"))}</p><button class="button secondary" data-poster>${icon("print")}${e(t("poster"))}</button></section>${v.block_key ? `<a class="block-link" data-nav href="${routeURL("block", v.block_key, route.demo)}"><span>${e(t("block"))}<strong>${e(v.block)}</strong></span>${icon("arrow")}</a>` : ""}<p class="source-caption">${e(t("record"))}<br>${e(t("asOf"))}: ${e(formatDate(bundle.data_as_of, language))}</p></aside></div>`;
}

export function directoryPage(villages, route) {
  return `<section class="directory-heading"><div><h1>${e(t("findTitle"))}</h1><p>${e(t("findNote"))}</p></div>${waterArt("unknown")}</section><div class="directory-tools"><label class="search-field">${icon("search")}<input type="search" id="village-search" placeholder="${e(t("search"))}" aria-label="${e(t("search"))}"></label><select id="status-filter" aria-label="${e(t("all"))}">${["all", "unsafe", "provisional", "safe_again", "unknown"].map((s) => `<option value="${s}">${e(t(s))}</option>`).join("")}</select></div><div class="directory-top"><p id="result-count" role="status"></p><button class="button secondary" id="show-map">${icon("pin")}${e(t("showMap"))}</button></div><section id="map-section" hidden><div id="map" aria-label="${e(t("map"))}"></div><p class="muted">${e(t("mapNote"))}</p></section><div id="village-list" class="village-list"></div>`;
}

export function villageRows(villages, route) {
  if (!villages.length)
    return `<div class="empty">${icon("search")}<p>${e(t("empty"))}</p></div>`;
  return villages
    .map(
      (v) =>
        `<a class="village-row" data-nav href="${routeURL("village", v.key, route.demo)}"><span class="row-location">${icon("pin")}</span><span class="row-name"><strong>${e(v.name)}</strong><small>${e([v.block, v.district, v.state].filter(Boolean).join(", "))}</small></span>${badge(v.status || "unknown")}<span class="row-count">${e(v.open_cases ?? 0)} ${e(t("open"))}</span>${icon("arrow")}</a>`,
    )
    .join("");
}

export function blockPage(data, route) {
  const cases = sortCases(data.cases || []);
  const open = cases.filter((c) => c.status !== "CLOSED");
  const name = cases[0]?.block || route.key;
  return `<div class="breadcrumb"><a data-nav href="${routeURL("directory", "", route.demo)}">${e(t("villages"))}</a>${icon("arrow")}<span>${e(t("block"))}</span></div><section class="block-heading"><div><p class="location">${e(t("block"))}</p><h1>${e(name)}</h1><p>${e(t("blockNote"))}</p></div>${link(data.links?.engineer_join, t("engineer"), "button primary", "send")}</section><div class="block-stats"><div><strong>${new Set(cases.map((c) => c.village_key)).size}</strong><span>${e(t("total"))}</span></div><div><strong>${open.length}</strong><span>${e(t("open"))}</span></div><div><strong>${cases.length - open.length}</strong><span>${e(t("closed"))}</span></div></div><div class="section-heading"><h2>${e(t("priority"))}</h2></div><div class="block-cases">${cases.map((c) => `<article class="block-case"><div>${badge(c.status === "CLOSED" ? "safe_again" : c.status === "PROVISIONALLY_SAFE" ? "provisional" : "unsafe")}<h3>${e(c.village)}</h3><p>${e(local(c.parameter_name) || c.parameter)}</p></div><div><strong>${e(c.value ?? "—")} ${e(c.unit)}</strong><p>${e(t("labDate"))}: ${e(formatDate(c.lab_approval, language))}</p>${c.status !== "CLOSED" && Number.isFinite(Date.parse(c.opened_at)) ? `<small>${Math.max(0, Math.floor((Date.now() - Date.parse(c.opened_at)) / 86400000))} ${e(t("days"))}</small>` : ""}</div><a class="button secondary" data-nav href="${routeURL("village", c.village_key, route.demo)}">${e(t("viewVillage"))}${icon("arrow")}</a></article>`).join("") || `<p class="empty">${e(t("noData"))}</p>`}</div>`;
}

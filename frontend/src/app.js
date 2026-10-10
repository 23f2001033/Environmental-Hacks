import "@fontsource/noto-sans-devanagari/400.css";
import "@fontsource/noto-sans-devanagari/600.css";
import "@fontsource/noto-sans-devanagari/700.css";
import "@fontsource/dm-sans/400.css";
import "@fontsource/dm-sans/600.css";
import "@fontsource/dm-sans/700.css";
import "./styles.css";
import "./about.css";
import { get } from "./api.js";
import { t, language, setLanguage } from "./i18n.js";
import "@fontsource/fraunces/600.css";
import "@fontsource/fraunces/700.css";
import "@fontsource/tiro-devanagari-hindi/400.css";
import { routeFrom, routeURL, escapeHTML as e } from "./model.js";
import { aboutPage } from "./about.js";
import {
  shell,
  villagePage,
  directoryPage,
  villageRows,
  blockPage,
  icon,
} from "./components.js";

let route = routeFrom(location.search);
let data = null;
let request = null;
let map = null;
let failed = false;
let lastError = null;
const main = document.querySelector("#main");
try {
  setLanguage(
    localStorage.getItem("jalsaathi-language") ||
      ((navigator.language || "").toLowerCase().startsWith("hi") ? "hi" : "en"),
  );
} catch {}

function announce(message) {
  document.querySelector("#announcement").textContent = message;
}
function navigate(url) {
  history.pushState({}, "", url);
  load(true);
}

function renderError(error) {
  main.innerHTML = `<section class="error-state">${icon("alert")}<h1>${e(t("error"))}</h1><p>${e(t(error?.status === 404 ? "notFound" : "errorNote"))}</p><div><button class="button primary" data-refresh>${e(t("retry"))}</button><a data-nav class="button secondary" href="/?demo=1&v=412558">${e(t("demoLink"))}</a></div></section>`;
}

function render() {
  map?.remove();
  map = null;
  shell(route, route.view === "village" ? data : null);
  if (failed) {
    renderError(lastError);
    return;
  }
  if (!data) return;
  main.innerHTML =
    route.view === "about"
      ? aboutPage(data.stats, data.villages, data.overview)
      : route.view === "village"
        ? villagePage(data, route)
        : route.view === "block"
          ? blockPage(data, route)
          : directoryPage(data.villages, route);
  document.title =
    route.view === "about"
      ? `${t("brand")} | ${language === "hi" ? "गांव के पीने के पानी की सूचना" : "Lab-confirmed water alerts for villages"}`
      : `${route.view === "village" ? data.village.name : t(route.view === "block" ? "block" : "villages")} | ${t("brand")}`;
  main.querySelectorAll("audio").forEach((audio) =>
    audio.addEventListener("error", () => {
      audio.hidden = true;
      audio.nextElementSibling.hidden = false;
    }),
  );
  if (route.view === "directory") wireDirectory();
}

function wireDirectory() {
  const search = document.querySelector("#village-search");
  const filter = document.querySelector("#status-filter");
  const update = () => {
    const query = search.value.trim().toLocaleLowerCase();
    const rank = { unsafe: 0, provisional: 1, unknown: 2, safe_again: 3 };
    const villages = data.villages
      .filter(
        (v) =>
          `${v.name} ${v.block} ${v.district} ${v.state}`
            .toLocaleLowerCase()
            .includes(query) &&
          (filter.value === "all" || v.status === filter.value),
      )
      .sort((a, b) => (rank[a.status] ?? 2) - (rank[b.status] ?? 2));
    document.querySelector("#village-list").innerHTML = villageRows(
      villages,
      route,
    );
    document.querySelector("#result-count").textContent =
      `${villages.length} ${t("results")}`;
  };
  if (route.q) search.value = route.q;
  search.addEventListener("input", update);
  filter.addEventListener("change", update);
  update();
  document.querySelector("#show-map").onclick = async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    const section = document.querySelector("#map-section");
    section.hidden = false;
    const container = document.querySelector("#map");
    container.textContent = t("loading");
    const currentRequest = request;
    try {
      const config = await get("/config", {
        demo: route.demo,
        signal: currentRequest.signal,
      });
      if (!container.isConnected) return;
      if (!config.map?.style_url) {
        container.textContent = t(route.demo ? "mapDemo" : "mapMissing");
        return;
      }
      const { mountMap } = await import("./map.js");
      if (!container.isConnected) return;
      container.textContent = "";
      map = await mountMap(container, data.villages, config.map, (key) =>
        navigate(routeURL("village", key, route.demo)),
      );
    } catch {
      if (container.isConnected) container.textContent = t("mapMissing");
    }
  };
}

async function load(focus = false) {
  request?.abort();
  map?.remove();
  map = null;
  request = new AbortController();
  const thisRequest = request;
  route = routeFrom(location.search);
  data = null;
  failed = false;
  shell(route, null);
  main.setAttribute("aria-busy", "true");
  main.innerHTML = `<div class="loading-state" role="status"><span class="spinner"></span><p>${e(t("loading"))}</p><div class="skeleton"></div><div class="skeleton short"></div></div>`;
  try {
    if (route.view === "about") {
      const [stats, villages, overview] = await Promise.all([
        get("/stats", { demo: route.demo, signal: thisRequest.signal }).catch(() => null),
        get("/villages", { demo: route.demo, signal: thisRequest.signal }),
        get("/overview", { demo: route.demo, signal: thisRequest.signal }).catch(() => null),
      ]);
      if (thisRequest !== request) return;
      if (!Array.isArray(villages?.villages)) throw new Error("Invalid response");
      data = { stats, villages: villages.villages, overview };
      render();
      return;
    }
    const path =
      route.view === "village"
        ? `/villages/${encodeURIComponent(route.key)}`
        : route.view === "block"
          ? `/blocks/${encodeURIComponent(route.key)}/cases`
          : "/villages";
    const result = await get(path, {
      demo: route.demo,
      signal: thisRequest.signal,
    });
    if (thisRequest !== request) return;
    if (
      (route.view === "village" &&
        (!result.village || !Array.isArray(result.cases))) ||
      (route.view === "directory" && !Array.isArray(result.villages)) ||
      (route.view === "block" && !Array.isArray(result.cases))
    )
      throw new Error("Invalid response");
    data = result;
    render();
  } catch (error) {
    if (thisRequest !== request) return;
    failed = true;
    lastError = error;
    renderError(error);
  } finally {
    if (thisRequest === request) {
      main.setAttribute("aria-busy", "false");
      if (focus) {
        main.focus({ preventScroll: true });
        window.scrollTo({ top: 0 });
      }
    }
  }
}

document.addEventListener("click", async (event) => {
  const nav = event.target.closest("a[data-nav]");
  if (
    nav &&
    !event.ctrlKey &&
    !event.metaKey &&
    !event.shiftKey &&
    event.button === 0
  ) {
    event.preventDefault();
    navigate(nav.href);
    return;
  }
  const lang = event.target.closest("[data-lang]");
  if (lang) {
    setLanguage(lang.dataset.lang);
    try {
      localStorage.setItem("jalsaathi-language", language);
    } catch {}
    if (!data && !failed) {
      load();
      return;
    }
    render();
    document.querySelector(`[data-lang="${language}"]`)?.focus();
  }
  if (event.target.closest("[data-refresh]")) load();
  if (event.target.closest("[data-poster]") && data?.village) {
    const { showPoster } = await import("./poster.js");
    showPoster(data, route.demo);
  }
  const share = event.target.closest("[data-share]");
  if (share) {
    try {
      const url = new URL(
        routeURL("village", data.village.key, route.demo),
        location.origin,
      ).href;
      if (navigator.share)
        await navigator.share({ title: data.village.name, url });
      else {
        await navigator.clipboard.writeText(url);
        share.textContent = t("copied");
        announce(t("copied"));
      }
    } catch (error) {
      if (error.name !== "AbortError") {
        share.textContent = t("copyFailed");
        announce(t("copyFailed"));
      }
    }
  }
});
window.addEventListener("popstate", () => load(true));
load();

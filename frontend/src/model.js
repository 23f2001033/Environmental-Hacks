export function escapeHTML(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
}

export function safeURL(value) {
  if (!value) return "";
  try {
    const url = new URL(value, "https://jalsaathi.invalid");
    return ["http:", "https:"].includes(url.protocol) ? value : "";
  } catch {
    return "";
  }
}

export function routeFrom(search) {
  const p = new URLSearchParams(search);
  return {
    demo: p.get("demo") === "1",
    view: p.has("b") ? "block" : p.has("v") ? "village" : p.has("find") ? "directory" : "about",
    key: p.get("b") ?? p.get("v") ?? "",
    q: p.get("q") ?? "",
  };
}

export function routeURL(view, key, demo = false) {
  const p = new URLSearchParams();
  if (demo) p.set("demo", "1");
  if (view === "block" || view === "village") p.set(view === "block" ? "b" : "v", key);
  const query = p.size ? String(p) : "";
  if (view === "directory") return `/?find${query ? "&" + query : ""}`;
  return `/${query ? "?" + query : ""}`;
}

export function formatDate(value, lang = "hi", time = false) {
  if (!value || Number.isNaN(Date.parse(value))) return "—";
  return new Intl.DateTimeFormat(lang === "hi" ? "hi-IN" : "en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Kolkata",
    ...(time ? { hour: "numeric", minute: "2-digit" } : {}),
  }).format(new Date(value));
}

export function sortCases(cases) {
  const rank = { red: 0, amber: 1, yellow: 2, review: 3 };
  return [...cases].sort(
    (a, b) =>
      (a.status === "CLOSED") - (b.status === "CLOSED") ||
      (rank[a.severity] ?? 4) - (rank[b.severity] ?? 4) ||
      String(a.opened_at ?? "").localeCompare(b.opened_at ?? ""),
  );
}

export function caseProgress(c) {
  // Current workflow state governs the progression, including a reopened case.
  const stage =
    {
      DETECTED: 0,
      WARNED: 1,
      AWAITING_FIX: 2,
      ESCALATED: 2,
      AWAITING_RETEST: 3,
      PROVISIONALLY_SAFE: 4,
      CLOSED: 6,
    }[c.status] ?? 0;
  return Array.from({ length: 6 }, (_, i) =>
    i < stage ? "complete" : i === stage ? "current" : "pending",
  );
}

export function villageStatus(cases) {
  if (!cases.length) return "unknown";
  const open = cases.filter((c) => c.status !== "CLOSED");
  return !open.length
    ? "safe_again"
    : open.every((c) => c.status === "PROVISIONALLY_SAFE")
      ? "provisional"
      : "unsafe";
}

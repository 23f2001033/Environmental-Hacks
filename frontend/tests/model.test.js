import test from "node:test";
import assert from "node:assert/strict";
import {
  routeFrom,
  routeURL,
  caseProgress,
  villageStatus,
  sortCases,
  safeURL,
  escapeHTML,
  formatDate,
  haversineDistanceKm,
} from "../src/model.js";
import {
  villagePage,
  blockPage,
  directoryPage,
  villageRows,
} from "../src/components.js";
import { setLanguage, words, pair, t, local } from "../src/i18n.js";

test("routes preserve explicit preview mode and encoded village keys", () => {
  assert.deepEqual(routeFrom("?v=a%26b&demo=1"), {
    view: "village",
    key: "a&b",
    demo: true,
    q: "",
  });
  assert.equal(routeURL("village", "a&b", true), "/?demo=1&v=a%26b");
  assert.deepEqual(routeFrom("?b=5037"), {
    view: "block",
    key: "5037",
    demo: false,
    q: "",
  });
  assert.equal(routeFrom("").demo, false);
  assert.equal(routeFrom("").view, "about");
  assert.equal(routeFrom("?find&q=Jaipur").view, "directory");
  assert.equal(routeFrom("?find&q=Jaipur").q, "Jaipur");
  assert.equal(routeURL("directory", ""), "/?find");
  assert.equal(routeURL("directory", "", true), "/?find&demo=1");
  assert.equal(routeURL("about", ""), "/");
});
test("unknown and provisional records are never classified as safe", () => {
  assert.equal(villageStatus([]), "unknown");
  assert.equal(
    villageStatus([{ status: "PROVISIONALLY_SAFE" }]),
    "provisional",
  );
  assert.equal(
    villageStatus([
      { status: "PROVISIONALLY_SAFE" },
      { status: "AWAITING_FIX" },
    ]),
    "unsafe",
  );
  assert.equal(villageStatus([{ status: "CLOSED" }]), "safe_again");
});
test("reopened cases reset progress; provisional does not complete lab or closure", () => {
  assert.deepEqual(
    caseProgress({
      status: "AWAITING_FIX",
      timeline: [{ kind: "lab_result" }],
    }),
    ["complete", "complete", "current", "pending", "pending", "pending"],
  );
  assert.deepEqual(caseProgress({ status: "PROVISIONALLY_SAFE" }), [
    "complete",
    "complete",
    "complete",
    "complete",
    "current",
    "pending",
  ]);
  assert.ok(caseProgress({ status: "CLOSED" }).every((s) => s === "complete"));
});
test("official queue ranks severity then age and puts closed cases last", () => {
  const cases = [
    { case_id: "closed", status: "CLOSED", severity: "red" },
    { case_id: "amber", severity: "amber" },
    { case_id: "new", severity: "red", opened_at: "2026-10-10" },
    { case_id: "old", severity: "red", opened_at: "2026-10-01" },
  ];
  assert.deepEqual(
    sortCases(cases).map((c) => c.case_id),
    ["old", "new", "amber", "closed"],
  );
});
test("unsafe URL schemes and markup are not rendered", () => {
  assert.equal(safeURL("javascript:alert(1)"), "");
  assert.equal(safeURL("data:text/html,test"), "");
  assert.equal(safeURL("/media/a.mp3"), "/media/a.mp3");
  assert.equal(
    escapeHTML('<img onerror="x">'),
    "&lt;img onerror=&quot;x&quot;&gt;",
  );
});
test("bad or missing dates have a stable fallback", () => {
  assert.equal(formatDate(null), "—");
  assert.equal(formatDate("garbage"), "—");
});
const c = {
  case_id: "a",
  code: "nitrate",
  parameter_name: { hi: "नाइट्रेट", en: "nitrate" },
  status: "AWAITING_FIX",
  severity: "red",
  value: 60,
  unit: "mg/L",
  acceptable_limit: 45,
  advice: { hi: ["उबालें नहीं।"], en: ["Do not boil this water."] },
  actions: ["no_boil"],
  timeline: [
    {
      kind: "policy",
      actor: "tg:123456789",
      decision: "deny",
      at: "2026-10-09",
    },
  ],
};
const bundle = {
  village: { key: "a", name: "Village", block: "Block", block_key: "b" },
  status: "unsafe",
  cases: [c],
  data_as_of: "2026-10-09",
  links: {},
};
test("village view renders authoritative chemical advice and hides private actor identifiers", () => {
  setLanguage("en");
  const html = villagePage(bundle, { demo: false });
  assert.ok(html.includes("Do not boil this water."));
  assert.ok(!html.includes("tg:123456789"));
  assert.ok(!html.includes("<audio"));
  assert.ok(html.includes("Lab confirmation"));
});
test("closed cases show historical advice without active red urgency or audio", () => {
  const html = villagePage(
    { ...bundle, status: "safe_again", cases: [{ ...c, status: "CLOSED" }] },
    { demo: false },
  );
  assert.ok(html.includes("Previous test and advice"));
  assert.ok(!html.includes("Act today"));
  assert.ok(!html.includes("<audio"));
});
test("block links remain in preview and do not render private actions", () => {
  const html = blockPage(
    {
      cases: [{ ...c, village_key: "a", village: "Village", block: "Block" }],
      links: {},
    },
    { key: "b", demo: true },
  );
  assert.ok(html.includes("/?demo=1&v=a"));
  assert.ok(!html.includes("/admin/"));
});
test("haversineDistanceKm computes great-circle distance accurately and handles invalid coordinates", () => {
  assert.equal(haversineDistanceKm(null, 79.77, 27.23, 79.77), null);
  assert.equal(haversineDistanceKm(27.23, undefined, 27.23, 79.77), null);
  assert.equal(haversineDistanceKm(27.237, 79.779, 27.237, 79.779), 0);
  // Behta Lakhi (27.23725, 79.77993) to Basi (27.32363, 79.82606)
  const dist = haversineDistanceKm(27.23725, 79.77993, 27.32363, 79.82606);
  assert.ok(dist >= 10 && dist <= 11);
});
test("directoryPage renders search input, status filter, and Near Me button with proper accessibility", () => {
  setLanguage("en");
  const html = directoryPage([], { demo: false });
  assert.ok(html.includes('id="village-search"'));
  assert.ok(html.includes('id="status-filter"'));
  assert.ok(html.includes('id="near-me-btn"'));
  assert.ok(html.includes('id="near-me-text"'));
  assert.ok(html.includes("Near me"));
  assert.ok(html.includes('id="result-count"'));
});
test("villageRows renders distance pill when distanceText is present and omits it when null", () => {
  const withDistance = [
    {
      key: "v1",
      name: "Behta Lakhi",
      block: "Harpalpur",
      district: "Hardoi",
      state: "Uttar Pradesh",
      status: "unsafe",
      open_cases: 1,
      distanceText: "11 km",
    },
  ];
  const withoutDistance = [
    {
      key: "v2",
      name: "Basi",
      block: "Harpalpur",
      district: "Hardoi",
      state: "Uttar Pradesh",
      status: "unsafe",
      open_cases: 1,
      distanceText: null,
    },
  ];

  const htmlDist = villageRows(withDistance, { demo: false });
  assert.ok(htmlDist.includes('class="distance-pill"'));
  assert.ok(htmlDist.includes("11 km"));
  assert.ok(htmlDist.includes("Behta Lakhi"));

  const htmlNoDist = villageRows(withoutDistance, { demo: false });
  assert.ok(!htmlNoDist.includes('class="distance-pill"'));
  assert.ok(htmlNoDist.includes("Basi"));
});
test("villageRows renders empty state when no villages match", () => {
  setLanguage("en");
  const html = villageRows([], { demo: false });
  assert.ok(html.includes('class="empty"'));
  assert.ok(html.includes("No villages found"));
});
test("i18n dictionary completeness: all words have valid Hindi and English translations", () => {
  for (const [key, val] of Object.entries(words)) {
    if (key === "stages") {
      assert.ok(Array.isArray(val) && val.length === 6);
      for (const stage of val) {
        assert.ok(Array.isArray(stage) && stage.length === 2);
        assert.ok(typeof stage[0] === "string" && stage[0].length > 0);
        assert.ok(typeof stage[1] === "string" && stage[1].length > 0);
      }
      continue;
    }
    assert.ok(
      Array.isArray(val) && val.length === 2,
      `Word "${key}" must be a 2-element array [hi, en]`,
    );
    assert.ok(
      typeof val[0] === "string" && val[0].trim().length > 0,
      `Word "${key}" missing valid Hindi translation`,
    );
    assert.ok(
      typeof val[1] === "string" && val[1].trim().length > 0,
      `Word "${key}" missing valid English translation`,
    );
  }
});
test("i18n pair, t, and local fallbacks handle language switches and edge cases", () => {
  setLanguage("en");
  assert.equal(t("brand"), "JalSaathi");
  assert.equal(pair(["हिंदी", "English"]), "English");
  assert.equal(t("unknown_key_xyz"), "unknown_key_xyz");
  assert.equal(local({ en: "Water", hi: "पानी" }), "Water");
  assert.equal(local(null), "");
  assert.equal(local(undefined), "");

  setLanguage("hi");
  assert.equal(t("brand"), "जलसाथी");
  assert.equal(pair(["हिंदी", "English"]), "हिंदी");
  assert.equal(local({ en: "Water", hi: "पानी" }), "पानी");
});
test("formatDate handles timestamps with Kolkata timeZone and time flag", () => {
  const ts = "2026-10-09T18:33:04+05:30";
  const formattedDate = formatDate(ts, "en", false);
  assert.ok(formattedDate.includes("2026"));

  const formattedWithTime = formatDate(ts, "en", true);
  assert.ok(formattedWithTime.includes(":"));

  assert.equal(formatDate(""), "—");
  assert.equal(formatDate(null), "—");
  assert.equal(formatDate("invalid-date"), "—");
});
test("safeURL sanitization handles various protocol edge cases", () => {
  assert.equal(
    safeURL("https://ejalshakti.gov.in/WQMIS"),
    "https://ejalshakti.gov.in/WQMIS",
  );
  assert.equal(safeURL("http://localhost:4173"), "http://localhost:4173");
  assert.equal(safeURL("javascript:void(0)"), "");
  assert.equal(safeURL("vbscript:execute"), "");
  assert.equal(safeURL("data:application/json;base64,123"), "");
  assert.equal(safeURL(""), "");
  assert.equal(safeURL(null), "");
});
test("escapeHTML properly escapes HTML injection tokens", () => {
  assert.equal(
    escapeHTML('"><script>alert(1)</script>'),
    "&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;",
  );
  assert.equal(escapeHTML("& ' < > \""), "&amp; &#39; &lt; &gt; &quot;");
  assert.equal(escapeHTML(null), "");
  assert.equal(escapeHTML(undefined), "");
  assert.equal(escapeHTML(123), "123");
});


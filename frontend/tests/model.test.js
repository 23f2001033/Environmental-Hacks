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
} from "../src/model.js";
import { villagePage, blockPage } from "../src/components.js";
import { setLanguage } from "../src/i18n.js";

test("routes preserve explicit preview mode and encoded village keys", () => {
  assert.deepEqual(routeFrom("?v=a%26b&demo=1"), {
    view: "village",
    key: "a&b",
    demo: true,
  });
  assert.equal(routeURL("village", "a&b", true), "/?demo=1&v=a%26b");
  assert.deepEqual(routeFrom("?b=5037"), {
    view: "block",
    key: "5037",
    demo: false,
  });
  assert.equal(routeFrom("").demo, false);
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

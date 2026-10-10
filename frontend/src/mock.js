import fixtures from "../../data/fixtures/wqmis_demo_records.json";
import library from "../../content/advice.json";
import { villageStatus, sortCases } from "./model.js";

// Real fixture measurements; explicitly simulated workflow events. No fabricated audio.
const bundles = new Map();
for (const record of fixtures.records) {
  const key = String(record.village_id ?? record.village);
  const code =
    record.parameter === "Ecoil" ? "ecoli" : record.parameter.toLowerCase();
  const entry = library.parameters[code];
  if (!entry) continue;
  if (!bundles.has(key))
    bundles.set(key, {
      village: {
        key,
        name: record.village,
        gram_panchayat: record.gram_panchayat,
        block: record.block,
        block_key: String(record.block_id),
        district: record.district,
        state: record.state,
        lat: record.lat ?? null,
        lon: record.lon ?? null,
        geo_precision: record.lat ? "village" : null,
      },
      status: "unsafe",
      status_text: { hi: "पानी असुरक्षित", en: "Unsafe water" },
      samples: [],
      cases: [],
      data_as_of: "2026-10-09",
      source: "JJM-WQMIS • preview fixtures",
      links: {
        page: `/?demo=1&v=${encodeURIComponent(key)}`,
        telegram_join: `https://t.me/Srott_bot?start=v_${key}`,
        engineer_join: `https://t.me/Srott_bot?start=e_${record.block_id}`,
      },
    });
  const bundle = bundles.get(key);
  bundle.samples.push(record);
  if (bundle.cases.some((c) => c.code === code)) continue;
  bundle.cases.push({
    ...record,
    code,
    case_id: `preview-${key}-${code}`,
    village_key: key,
    block_key: String(record.block_id),
    parameter_name: entry.name,
    class: entry.class,
    severity: "red",
    status: "AWAITING_FIX",
    opened_at: "2026-10-09T16:20:00Z",
    closed_at: null,
    audio_url: null,
    advice: {
      hi: entry.do_now.map((a) => a.hi),
      en: entry.do_now.map((a) => a.en),
    },
    actions: entry.do_now.map((a) => a.action),
    timeline: [
      {
        at: "2026-10-09T16:20:00Z",
        kind: "detected",
        actor: "system",
        note: "SIMULATED preview event",
      },
      {
        at: "2026-10-09T16:20:05Z",
        kind: "warned",
        actor: "system",
        note: "SIMULATED preview event",
      },
      {
        at: "2026-10-09T16:20:06Z",
        kind: "awaiting_fix",
        actor: "system",
        note: "SIMULATED preview event",
      },
    ],
  });
}

export function mockGet(path) {
  const list = [...bundles.values()];
  if (path === "/villages")
    return {
      villages: list.map((b) => ({
        ...b.village,
        source: "fixtures",
        status: villageStatus(b.cases),
        worst_severity: "red",
        open_cases: b.cases.length,
        parameters: b.cases.map((c) => c.code),
      })),
    };
  if (path.startsWith("/villages/")) {
    const b = bundles.get(decodeURIComponent(path.split("/")[2]));
    if (b) return structuredClone(b);
  }
  if (path.startsWith("/blocks/")) {
    const key = decodeURIComponent(path.split("/")[2]);
    return {
      block_key: key,
      cases: sortCases(
        list.flatMap((b) => b.cases).filter((c) => c.block_key === key),
      ),
      links: { engineer_join: `https://t.me/Srott_bot?start=e_${key}` },
    };
  }
  if (path === "/config") return { map: { style_url: null } };
  throw Object.assign(new Error("Not found"), { status: 404 });
}

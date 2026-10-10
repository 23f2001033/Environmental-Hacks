import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useApi } from "../components.jsx";
import { useLang } from "../i18n.jsx";
import VillageMap from "../VillageMap.jsx";

const CHEMICAL = new Set(["nitrate", "fluoride", "arsenic"]);
// The 13 demo villages can be acted on by anyone with the public demo link (real villages need a signed link).
const DEMO_VILLAGE = "412558"; // Behta Lakhi, Harpalpur, Hardoi: E. coli and coliform
const DEMO_BLOCK = "5037"; // Harpalpur block

export function chemicalShare(stats) {
  const byCode = (stats && stats.open_by_code) || {};
  const total = Object.values(byCode).reduce((a, b) => a + b, 0);
  const chem = Object.entries(byCode).reduce((a, [k, v]) => a + (CHEMICAL.has(k) ? v : 0), 0);
  return total ? Math.round((chem / total) * 100) : null;
}

function VillageSearch({ villages }) {
  const { t } = useLang();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const query = q.trim().toLowerCase();
  const matches = query.length < 2 ? [] : (villages || []).filter((v) =>
    `${v.name} ${v.block} ${v.district}`.toLowerCase().includes(query)).slice(0, 8);
  return (
    <div className="hero-search">
      <label htmlFor="village-search">{t("search_label")}</label>
      <input id="village-search" className="search big" value={q} onChange={(e) => setQ(e.target.value)}
             placeholder={t("search")} autoComplete="off" />
      {query.length >= 2 && (
        <div className="results">
          {matches.length ? matches.map((v) => (
            <a key={v.key} href={`/village/${v.key}`} onClick={(e) => { e.preventDefault(); navigate(`/village/${v.key}`); }}>
              <span className={`dot ${v.status}`} /> <b>{v.name}</b> <span className="small muted">{v.block}, {v.district}</span>
            </a>
          )) : <div className="small muted" style={{ padding: 10 }}>{t("no_match")}</div>}
        </div>
      )}
      <div className="small" style={{ color: "#bcd6e0", marginTop: 8 }}>
        {t("search_try")} <Link to={`/village/${DEMO_VILLAGE}`} style={{ color: "#fff" }}>Behta Lakhi</Link>
        {" · "}<Link to="/village/651384" style={{ color: "#fff" }}>Dhabla Kalayanpura</Link>
      </div>
    </div>
  );
}

const ROLES = [
  { icon: "🏠", key: "villager", to: `/village/${DEMO_VILLAGE}` },
  { icon: "🧪", key: "relay", to: `/relay/${DEMO_VILLAGE}?k=demo` },
  { icon: "🛠️", key: "engineer", to: `/engineer/${DEMO_BLOCK}?k=demo` },
  { icon: "🏛️", key: "official", to: "/officials" },
];

const LOOP = [
  { key: "loop_1", to: `/village/${DEMO_VILLAGE}` },
  { key: "loop_2", to: `/engineer/${DEMO_BLOCK}?k=demo` },
  { key: "loop_3", to: `/engineer/${DEMO_BLOCK}?k=demo` },
  { key: "loop_4", to: `/relay/${DEMO_VILLAGE}?k=demo` },
  { key: "loop_5", to: "/officials" },
];

export default function Home() {
  const { t } = useLang();
  const stats = useApi("/stats", { poll: 30000 });
  const villages = useApi("/villages");
  const s = stats.data;
  const repeat = s && s.repeat_failures && s.repeat_failures.totals;
  const list = villages.data && villages.data.villages;
  return (
    <div className="page">
      <section className="hero">
        <div className="wrap hero-grid">
          <div>
            <div className="kicker">{t("hero_kicker")}</div>
            <h1 className="display">{t("hero_title")}</h1>
            <p>{t("hero_body")}</p>
          </div>
          <VillageSearch villages={list} />
        </div>
        <svg className="waves" viewBox="0 0 1440 80" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 40 C 240 80 480 0 720 40 C 960 80 1200 0 1440 40 L1440 80 L0 80 Z" fill="#f3f7f8" />
        </svg>
      </section>

      <div className="wrap">
        <div className="stats">
          <div className="stat"><b>{s ? s.villages : "…"}</b><span>{t("stat_villages")}</span></div>
          <div className="stat warn"><b>{s ? s.open_cases : "…"}</b><span>{t("stat_open")}</span></div>
          <div className="stat"><b>{s ? `${chemicalShare(s)}%` : "…"}</b><span>{t("stat_chemical")}</span></div>
          <div className="stat"><b>{repeat ? repeat.both : "…"}</b><span>{t("stat_repeat")}</span></div>
        </div>

        <section className="block">
          <h2 className="section-title display">{t("use_title")}</h2>
          <p className="muted" style={{ marginTop: 0 }}>{t("use_body")}</p>
          <div className="grid-4">
            {ROLES.map((r) => (
              <Link key={r.key} to={r.to} className="card role">
                <span className="role-icon">{r.icon}</span>
                <h3>{t(`role_${r.key}`)}</h3>
                <p>{t(`role_${r.key}_does`)}</p>
                <span className="role-go">{t(`role_${r.key}_go`)} →</span>
              </Link>
            ))}
          </div>
        </section>

        <section className="block" style={{ paddingTop: 0 }}>
          <div className="card loop">
            <h2 className="section-title display" style={{ fontSize: 24 }}>{t("loop_title")}</h2>
            <p className="muted" style={{ marginTop: 0 }}>{t("loop_body")}</p>
            <ol className="loop-steps">
              {LOOP.map((step, i) => (
                <li key={step.key}>
                  <span className="num">{i + 1}</span>
                  <span>{t(step.key)}</span>
                  <Link className="btn btn-line" to={step.to}>{t("loop_open")}</Link>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="block" id="map" style={{ paddingTop: 0 }}>
          <div className="row" style={{ marginBottom: 12 }}>
            <h2 className="section-title display">{t("map_title")}</h2>
            <span className="spacer" />
            <span className="small muted">{t("live_from")}</span>
          </div>
          <VillageMap villages={list} />
        </section>

        <section className="block">
          <h2 className="section-title display" style={{ marginBottom: 16 }}>{t("how_title")}</h2>
          <div className="grid-4">
            {[1, 2, 3, 4].map((n) => (
              <div className="card step" key={n}>
                <span className="num">{n}</span>
                <h3>{t(`how_${n}_t`)}</h3>
                <p>{t(`how_${n}_b`)}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="block" style={{ paddingTop: 0 }}>
          <div className="callout">
            <b className="big">{s ? `${chemicalShare(s)}%` : "…"}</b>
            <div>
              <h3 style={{ fontSize: 20, color: "#fff", marginBottom: 6 }}>{t("why_title")}</h3>
              <div>{t("why_body")}</div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

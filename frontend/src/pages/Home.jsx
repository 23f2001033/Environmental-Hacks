import { Link } from "react-router-dom";
import { useApi } from "../components.jsx";
import { useLang } from "../i18n.jsx";
import VillageMap from "../VillageMap.jsx";

const CHEMICAL = new Set(["nitrate", "fluoride", "arsenic"]);

export function chemicalShare(stats) {
  const byCode = (stats && stats.open_by_code) || {};
  const total = Object.values(byCode).reduce((a, b) => a + b, 0);
  const chem = Object.entries(byCode).reduce((a, [k, v]) => a + (CHEMICAL.has(k) ? v : 0), 0);
  return total ? Math.round((chem / total) * 100) : null;
}

export default function Home() {
  const { t } = useLang();
  const stats = useApi("/stats", { poll: 30000 });
  const villages = useApi("/villages");
  const s = stats.data;
  const repeat = s && s.repeat_failures && s.repeat_failures.totals;
  return (
    <div className="page">
      <section className="hero">
        <div className="wrap">
          <div className="kicker">{t("hero_kicker")}</div>
          <h1 className="display">{t("hero_title")}</h1>
          <p>{t("hero_body")}</p>
          <div className="row">
            <a className="btn btn-primary" href="#map">{t("hero_cta_map")}</a>
            <Link className="btn btn-ghost" to="/impact">{t("hero_cta_impact")}</Link>
          </div>
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

        <section className="block" id="map">
          <div className="row" style={{ marginBottom: 12 }}>
            <h2 className="section-title display">{t("nav_map")}</h2>
            <span className="spacer" />
            <span className="small muted">{t("live_from")}</span>
          </div>
          <VillageMap villages={villages.data && villages.data.villages} />
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

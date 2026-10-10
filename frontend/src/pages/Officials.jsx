import { Fragment, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ErrorBox, Loading, useApi, when } from "../components.jsx";
import { useLang } from "../i18n.jsx";

function Bar({ value, max, kind = "" }) {
  return <div className={`minibar ${kind}`}><span style={{ width: `${max ? Math.round((value / max) * 100) : 0}%` }} /></div>;
}

function Feed() {
  const { t, lang } = useLang();
  const { data } = useApi("/activity?limit=40", { poll: 8000 });
  if (!data) return <div className="skeleton" style={{ height: 300 }} />;
  return (
    <ul className="feed">
      {data.events.map((e, i) => (
        <li key={`${e.at}-${i}`} className={e.decision === "deny" ? "deny" : ""}>
          <div className="meta">{when(e.at, lang)} · {e.district} · {e.actor && e.actor !== "system" ? e.actor : "system"}</div>
          <div>
            <b>{t(`act_${e.kind}`)}</b>
            {e.decision && <span className={`cedar ${e.decision}`}>Cedar: {e.decision}{e.action ? ` ${e.action}` : ""}</span>}
            {" · "}<Link to={`/village/${e.village_key}`}>{e.village}</Link> <span className="muted small">({e.code})</span>
          </div>
          {(e.note || e.reason) && <div className="small muted">{e.note || e.reason}</div>}
        </li>
      ))}
    </ul>
  );
}

export default function Officials() {
  const { t } = useLang();
  const navigate = useNavigate();
  const { data, error, loading, reload } = useApi("/overview", { poll: 20000 });
  const [open, setOpen] = useState({});
  if (loading && !data) return <div className="wrap" style={{ padding: "24px 16px" }}><Loading /></div>;
  if (error && !data) return <div className="wrap" style={{ padding: "24px 16px" }}><ErrorBox error={error} onRetry={reload} /></div>;
  const max = Math.max(1, ...data.districts.map((d) => d.open));
  return (
    <div className="page wrap stack" style={{ padding: "24px 16px" }}>
      <div>
        <h1 className="section-title display">{t("off_title")}</h1>
        <p className="muted" style={{ margin: 0 }}>{t("off_body")}</p>
      </div>
      <div className="stats" style={{ marginTop: 0 }}>
        <div className="stat warn"><b>{data.totals.open}</b><span>{t("off_open")}</span></div>
        <div className="stat warn"><b>{data.totals.escalated}</b><span>{t("off_overdue")}</span></div>
        <div className="stat"><b>{data.totals.villages}</b><span>{t("off_villages")}</span></div>
        <div className="stat"><b>{data.districts.length}</b><span>{t("off_district")}</span></div>
      </div>
      <div className="grid-2" style={{ gridTemplateColumns: "minmax(0, 3fr) minmax(0, 2fr)", alignItems: "start" }}>
        <div className="card scroll-x">
          <table className="data">
            <thead><tr><th>{t("off_district")}</th><th>{t("off_open")}</th><th>{t("off_overdue")}</th><th>{t("off_chemical")}</th></tr></thead>
            <tbody>
              {data.districts.map((d) => {
                const id = `${d.state}-${d.district}`;
                return (
                  <Fragment key={id}>
                    <tr className="click" onClick={() => setOpen((o) => ({ ...o, [id]: !o[id] }))}>
                      <td><b>{d.district}</b><div className="small muted">{d.state} · {d.villages} {t("off_villages").toLowerCase()}</div></td>
                      <td>{d.open}<Bar value={d.open} max={max} /></td>
                      <td style={{ color: d.escalated ? "var(--red)" : undefined }}>{d.escalated}<Bar value={d.escalated} max={Math.max(1, d.open)} kind="red" /></td>
                      <td>{Math.round(d.chemical_share * 100)}%<Bar value={d.chemical_share} max={1} kind="chem" /></td>
                    </tr>
                    {open[id] && d.blocks.map((b) => (
                      <tr key={b.block_key} className="click" onClick={() => navigate(`/engineer/${b.block_key}`)}>
                        <td style={{ paddingLeft: 24 }}>↳ {b.block} <span className="small muted">({b.villages})</span></td>
                        <td>{b.open}</td>
                        <td style={{ color: b.escalated ? "var(--red)" : undefined }}>{b.escalated}</td>
                        <td className="small"><Link to={`/engineer/${b.block_key}`}>{t("off_view_block")} →</Link></td>
                      </tr>
                    ))}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="card">
          <div className="row" style={{ marginBottom: 10 }}><h3>{t("off_activity")}</h3><span className="spacer" /><span className="pill green">● live</span></div>
          <Feed />
        </div>
      </div>
    </div>
  );
}

import { useParams } from "react-router-dom";
import { ClassPill, dateOnly, Deadline, ErrorBox, Loading, PushButton, QR, SeverityPill, StatusPill, Timeline, useApi } from "../components.jsx";
import { useLang } from "../i18n.jsx";

export function Meter({ c }) {
  const { t } = useLang();
  const limit = c.acceptable_limit;
  const value = c.value;
  const zeroLimit = !limit;
  const scaleMax = zeroLimit ? Math.max(value || 1, 1) : Math.max(value, limit) * 1.15;
  const pct = Math.min(100, ((value || 0) / scaleMax) * 100);
  const limitPct = zeroLimit ? 0 : (limit / scaleMax) * 100;
  return (
    <div className="meter">
      <div className="row">
        <span className="value">{value} <span className="small muted">{(c.unit || "").replace("/ ", "/")}</span></span>
        <span className="small muted">{zeroLimit ? t("village_any") : `${(value / limit).toFixed(1)}${t("village_times")}`}</span>
      </div>
      <div className="bar"><span className="fill" style={{ width: `${pct}%` }} />{!zeroLimit && <span className="limit" style={{ left: `${limitPct}%` }} />}</div>
      <div className="labels"><span>0</span><span>{t("village_limit")}: {limit ?? "?"}</span></div>
    </div>
  );
}

export function CaseCard({ c, children, showTimeline = true }) {
  const { t, lang } = useLang();
  const audio = (c.audio && c.audio[lang]) || c.audio_url;
  return (
    <article className="card stack">
      <div className="case-head">
        <h3>{c.parameter_name[lang]}</h3>
        <ClassPill cls={c.class} name={t(`class_${c.class}`)} />
        <SeverityPill severity={c.severity} />
        <StatusPill status={c.status} />
        <span className="spacer" />
        <Deadline caseView={c} />
      </div>
      <Meter c={c} />
      {c.status !== "CLOSED" && (
        <div>
          <h4 style={{ margin: "4px 0 0" }}>{t("village_what_to_do")}</h4>
          <ol className="advice">
            {c.advice[lang].map((line, i) => <li key={i} className={c.actions[i]}>{line}</li>)}
          </ol>
          {audio && (
            <div className="audio-row"><span className="small muted">🔊 {t("village_listen")}</span><audio controls preload="metadata" src={audio} /></div>
          )}
        </div>
      )}
      <div className="facts">
        <div><span>{t("village_lab")}</span>{dateOnly(c.lab_approval, lang)}</div>
        {c.lab && <div><span>Lab</span>{c.lab}</div>}
        {c.sample_id && <div><span>{t("village_sample")}</span>{c.sample_id}</div>}
        {c.source_type && <div><span>{t("village_source")}</span>{c.source_type}</div>}
        {c.scheme_name && <div><span>{t("village_scheme")}</span>{c.scheme_name}</div>}
      </div>
      {children}
      {showTimeline && c.timeline && c.timeline.length > 0 && (
        <details>
          <summary style={{ cursor: "pointer", fontWeight: 600 }}>{t("village_timeline")} ({c.timeline.length})</summary>
          <div style={{ marginTop: 12 }}><Timeline rows={c.timeline} /></div>
        </details>
      )}
    </article>
  );
}

function Poster({ b, lang }) {
  const c = b.cases.find((x) => x.status !== "CLOSED");
  return (
    <div className="poster">
      <h1>⚠️ {b.village.name}: {b.status_text.hi}</h1>
      {c && (
        <>
          <p style={{ fontSize: "18pt" }}>{c.parameter_name.hi}: {c.value} {c.unit} (सीमा {c.acceptable_limit})</p>
          <ol>{c.advice.hi.map((a, i) => <li key={i}>{a}</li>)}</ol>
        </>
      )}
      <div className="row" style={{ marginTop: "8mm" }}>
        <QR text={b.links.telegram_join} size={180} />
        <div style={{ fontSize: "14pt" }}>Telegram पर सूचना पाने के लिए स्कैन करें<br /><small>JJM-WQMIS · {dateOnly(b.data_as_of, lang)}</small></div>
      </div>
    </div>
  );
}

export default function Village() {
  const { key } = useParams();
  const { t, lang } = useLang();
  const { data: b, error, loading, reload } = useApi(`/villages/${encodeURIComponent(key)}`, { poll: 20000 });
  if (loading && !b) return <div className="wrap" style={{ padding: "24px 16px" }}><Loading /></div>;
  if (error && !b) {
    return <div className="wrap" style={{ padding: "24px 16px" }}>{error.status === 404 ? <div className="notice">{t("village_not_found")}</div> : <ErrorBox error={error} onRetry={reload} />}</div>;
  }
  const open = b.cases.filter((c) => c.status !== "CLOSED");
  const closed = b.cases.filter((c) => c.status === "CLOSED");
  return (
    <>
      <div className="page wrap stack" style={{ padding: "20px 16px" }}>
        <div className={`banner ${b.status}`}>
          <h1 className="display">{b.village.name}</h1>
          <div className="where">{[b.village.gram_panchayat, b.village.block, b.village.district, b.village.state].filter(Boolean).join(" · ")}</div>
          <div className="status">{b.status_text[lang]}</div>
        </div>

        {b.cases.length === 0 && <div className="notice">{t("village_no_cases")}</div>}
        {open.map((c) => <CaseCard key={c.case_id} c={c} />)}
        {closed.map((c) => <CaseCard key={c.case_id} c={c} />)}

        <section className="card">
          <h3 style={{ marginBottom: 12 }}>{t("village_join")}</h3>
          <div className="row" style={{ alignItems: "flex-start", gap: 20 }}>
            <QR text={b.links.telegram_join} size={128} />
            <div className="stack" style={{ gap: 10 }}>
              <a className="btn btn-line" href={b.links.telegram_join} target="_blank" rel="noopener">✈️ {t("village_telegram")}</a>
              <div><div className="small muted" style={{ marginBottom: 6 }}>{t("village_app_alerts")}</div><PushButton scope="village" keyName={b.village.key} /></div>
              <button className="btn btn-line" onClick={() => window.print()}>🖨️ {t("village_print")}</button>
            </div>
          </div>
          <p className="small muted" style={{ marginBottom: 0 }}>{t("village_data")}: {b.source}, {dateOnly(b.data_as_of, lang)}</p>
        </section>
      </div>
      <Poster b={b} lang={lang} />
    </>
  );
}

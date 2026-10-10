import { useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { linkToken, post } from "../api.js";
import { ErrorBox, Loading, PushButton, useApi } from "../components.jsx";
import { useLang } from "../i18n.jsx";
import { CaseCard } from "./Village.jsx";

const FIXES = ["chlorination", "repair", "source_changed", "need_help"];
const OPEN = new Set(["DETECTED", "WARNED", "AWAITING_FIX", "ESCALATED", "AWAITING_RETEST", "PROVISIONALLY_SAFE"]);

function urgency(c) {
  const overdue = c.status === "ESCALATED" || (c.escalations || 0) > 0 ? 0 : 1;
  const sev = { red: 0, amber: 1, yellow: 2 }[c.severity] ?? 3;
  return [OPEN.has(c.status) ? 0 : 1, overdue, sev, c.deadline_at || "9"];
}

function compare(a, b) {
  const x = urgency(a), y = urgency(b);
  for (let i = 0; i < x.length; i++) { if (x[i] < y[i]) return -1; if (x[i] > y[i]) return 1; }
  return 0;
}

function Denied({ result, onClose }) {
  const { t } = useLang();
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <div className="shield">⛔</div>
        <h3 style={{ marginBottom: 8 }}>{t("eng_denied_title")}</h3>
        <p className="muted">{t("eng_denied_body")}</p>
        <div className="notice" style={{ fontFamily: "ui-monospace, monospace", fontSize: 13 }}>
          decision: deny · action: close_case · evidence: engineer_says_fixed<br />{result.reason}
        </div>
        <div className="row" style={{ marginTop: 16 }}><span className="spacer" /><button className="btn btn-dark" onClick={onClose}>OK</button></div>
      </div>
    </div>
  );
}

export default function Engineer() {
  const { block } = useParams();
  const { search } = useLocation();
  const { t, lang } = useLang();
  const k = linkToken("e", block, search);
  const access = useApi(k ? `/access?role=e&key=${encodeURIComponent(block)}&k=${encodeURIComponent(k)}` : null);
  const { data, error, loading, reload } = useApi(`/blocks/${encodeURIComponent(block)}/cases`, { poll: 15000 });
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState({});
  const [denied, setDenied] = useState(null);
  const canAct = !!(access.data && access.data.valid);

  const act = async (c, kind, action) => {
    setBusy(`${c.case_id}:${kind}:${action || ""}`);
    try {
      const res = await post(`/engineer/${encodeURIComponent(block)}/${kind}`, { case_id: c.case_id, action, k });
      if (kind === "close") { if (!res.allowed) setDenied(res); }
      else setMsg((m) => ({ ...m, [c.case_id]: { ok: true, text: t("eng_logged") } }));
      reload();
    } catch (e) {
      setMsg((m) => ({ ...m, [c.case_id]: { ok: false, text: e.status === 409 ? t("eng_not_waiting") : e.message } }));
    } finally { setBusy(""); }
  };

  if (loading && !data) return <div className="wrap" style={{ padding: "24px 16px" }}><Loading /></div>;
  if (error && !data) return <div className="wrap" style={{ padding: "24px 16px" }}><ErrorBox error={error} onRetry={reload} /></div>;
  const cases = [...data.cases].sort(compare);
  const open = cases.filter((c) => OPEN.has(c.status));
  const overdue = open.filter((c) => c.status === "ESCALATED" || (c.escalations || 0) > 0);

  return (
    <div className="page wrap stack" style={{ padding: "20px 16px" }}>
      <div className="banner unsafe" style={{ background: "linear-gradient(135deg, var(--ink), var(--ink-3))" }}>
        <div className="small" style={{ opacity: 0.85 }}>{t("eng_title")}</div>
        <h1 className="display">{data.block || block}</h1>
        <div className="status">{open.length} {t("eng_open")} · {overdue.length} {t("eng_overdue")}</div>
      </div>
      <div className="row">
        {canAct ? <span className="pill green">✓ {t("eng_link_ok")}</span> : <span className="notice" style={{ flex: 1 }}>{t("eng_readonly")}</span>}
        <span className="spacer" />
        <PushButton scope="block" keyName={block} />
      </div>
      <h2 className="section-title display">{t("eng_cases")}</h2>
      {cases.map((c) => (
        <CaseCard key={c.case_id} c={c}>
          <div className="row"><Link to={`/village/${c.village_key}`}><b>{c.village}</b></Link><span className="small muted">{c.district}</span></div>
          {c.engineer_fix && OPEN.has(c.status) && (
            <div className="notice"><b>{t("eng_suggested")}:</b> {c.engineer_fix[lang]}</div>
          )}
          {canAct && OPEN.has(c.status) && (
            <div>
              <div className="small muted">{t("eng_log")}</div>
              <div className="actions">
                {FIXES.map((f) => (
                  <button key={f} className={f === "chlorination" ? "primary" : ""} disabled={!!busy}
                    onClick={() => act(c, "fix", f)}>{t(`fix_${f}`)}</button>
                ))}
                <button className="danger" disabled={!!busy} onClick={() => act(c, "close")}>✅ {t("eng_close")}</button>
              </div>
            </div>
          )}
          {msg[c.case_id] && <div className={`notice ${msg[c.case_id].ok ? "ok" : "err"}`}>{msg[c.case_id].text}</div>}
        </CaseCard>
      ))}
      {denied && <Denied result={denied} onClose={() => setDenied(null)} />}
    </div>
  );
}

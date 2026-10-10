import { useEffect, useRef, useState } from "react";
import { get } from "./api.js";
import { useLang } from "./i18n.jsx";
import { isSubscribed, pushSupported, subscribe } from "./push.js";

// Fetch JSON from the API, with optional polling. Returns { data, error, loading, reload }.
export function useApi(path, { poll = 0 } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!path) return undefined;
    let alive = true;
    const load = () => get(path)
      .then((data) => alive && setState({ data, error: null, loading: false }))
      .catch((error) => alive && setState((s) => ({ data: s.data, error, loading: false })));
    load();
    const id = poll ? setInterval(load, poll) : null;
    return () => { alive = false; if (id) clearInterval(id); };
  }, [path, poll, tick]);
  return { ...state, reload: () => setTick((n) => n + 1) };
}

export function Loading() {
  return <div className="stack"><div className="skeleton" style={{ height: 90 }} /><div className="skeleton" style={{ height: 200 }} /></div>;
}

export function ErrorBox({ error, onRetry }) {
  const { t } = useLang();
  return (
    <div className="notice err">
      {t("error")}: {error.message} {onRetry && <button className="btn btn-line" onClick={onRetry}>{t("retry")}</button>}
    </div>
  );
}

export function StatusPill({ status }) {
  const { t } = useLang();
  return <span className={`pill ${status}`}>{t(`status_${status}`)}</span>;
}

export function SeverityPill({ severity }) {
  const { t } = useLang();
  return <span className={`pill ${severity}`}>{t(`severity_${severity}`)}</span>;
}

export function ClassPill({ cls, name }) {
  return <span className={`pill ${cls === "chemical" ? "chem" : "micro"}`}>{name}</span>;
}

export function when(iso, lang) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function dateOnly(iso, lang) {
  if (!iso) return "?";
  return new Date(iso).toLocaleDateString(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function useNow(ms = 1000) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), ms); return () => clearInterval(id); }, [ms]);
  return now;
}

export function Deadline({ caseView }) {
  const { t } = useLang();
  const now = useNow();
  if (caseView.status === "CLOSED") return null;
  if (!caseView.deadline_at) {
    return caseView.escalations ? <span className="small muted">{t("no_deadline")}</span> : null;
  }
  const left = (new Date(caseView.deadline_at).getTime() - now) / 1000;
  if (left <= 0) return <span className="deadline late">{t("deadline_passed")}</span>;
  const d = Math.floor(left / 86400), h = Math.floor((left % 86400) / 3600), m = Math.floor((left % 3600) / 60), s = Math.floor(left % 60);
  const text = d ? `${d}d ${h}h` : h ? `${h}h ${m}m` : `${m}m ${String(s).padStart(2, "0")}s`;
  return <span className={`deadline ${left < 3600 ? "late" : ""}`}>{t("deadline_in")} {text}</span>;
}

export function Timeline({ rows }) {
  const { t, lang } = useLang();
  if (!rows || !rows.length) return null;
  return (
    <ul className="timeline">
      {rows.map((e, i) => (
        <li key={i} className={e.decision || ""}>
          <div className="when">{when(e.at, lang)}{e.actor && e.actor !== "system" ? ` · ${e.actor}` : ""}</div>
          <div>
            <span className="what">{t(`act_${e.kind}`)}</span>
            {e.decision && <span className={`cedar ${e.decision}`}>Cedar: {e.decision}</span>}
            {e.action && e.decision && <span className="small muted"> {e.action}</span>}
          </div>
          {(e.note || e.reason) && <div className="small muted">{e.note || e.reason}{e.result ? ` → ${e.result}` : ""}</div>}
        </li>
      ))}
    </ul>
  );
}

export function PushButton({ scope, keyName }) {
  const { t, lang } = useLang();
  const [state, setState] = useState(isSubscribed(scope, keyName) ? "on" : "off");
  const [msg, setMsg] = useState("");
  if (!pushSupported()) return <span className="small muted">{t("push_unsupported")}</span>;
  const turnOn = async () => {
    setState("busy");
    try { await subscribe(scope, keyName, lang); setState("on"); setMsg(""); }
    catch (e) { setState("off"); setMsg(e.message === "denied" ? t("push_denied") : `${t("error")}: ${e.message}`); }
  };
  return (
    <span className="row">
      <button className={`btn ${state === "on" ? "btn-line" : "btn-dark"}`} disabled={state !== "off"} onClick={turnOn}>
        🔔 {state === "on" ? t("push_on") : t("push_enable")}
      </button>
      {msg && <span className="small" style={{ color: "var(--red)" }}>{msg}</span>}
    </span>
  );
}

export function QR({ text, size = 140 }) {
  const ref = useRef(null);
  useEffect(() => {
    let alive = true;
    import("qrcode").then((QRCode) => {
      if (alive && ref.current) QRCode.toCanvas(ref.current, text, { width: size, margin: 1 });
    });
    return () => { alive = false; };
  }, [text, size]);
  return <canvas ref={ref} width={size} height={size} aria-label="QR code" />;
}

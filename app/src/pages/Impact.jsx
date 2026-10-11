import { ErrorBox, Loading, useApi } from "../components.jsx";
import { useLang } from "../i18n.jsx";
import { chemicalShare } from "./Home.jsx";

const PARAM = { Ecoil: "E. coli", Coliform: "Coliform", Nitrate: "Nitrate", Fluoride: "Fluoride", "Total arsenic": "Arsenic" };

function secs(s) {
  if (s == null) return "–";
  return s < 120 ? `${Math.round(s)} s` : s < 7200 ? `${Math.round(s / 60)} min` : `${(s / 3600).toFixed(1)} h`;
}

function Box({ x, y, w = 236, h = 60, title, sub, tone = "aws" }) {
  const fill = { aws: "#fff7ec", data: "#eef7fb", people: "#eef8f1", policy: "#fbeeee" }[tone];
  const stroke = { aws: "#e08a00", data: "#1d5a78", people: "#23804f", policy: "#c2412d" }[tone];
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx="10" fill={fill} stroke={stroke} strokeWidth="1.5" />
      <text x={x + w / 2} y={y + (sub ? h / 2 - 4 : h / 2 + 5)} textAnchor="middle" fontSize="14" fontWeight="700" fill="#0b2a3c">{title}</text>
      {sub && <text x={x + w / 2} y={y + h / 2 + 14} textAnchor="middle" fontSize="11.5" fill="#587080">{sub}</text>}
    </g>
  );
}

// Four lanes, read left to right, top to bottom: the same order as the story on the About page.
const COLS = [24, 296, 568, 840];
const LANES = [
  { title: "1 · A FAILED LAB TEST BECOMES A CASE", boxes: [
    { title: "JJM-WQMIS portal", sub: "government lab results", tone: "data" },
    { title: "Ingest Lambda", sub: "EventBridge Scheduler · parse · guard" },
    { title: "Step Functions Distributed Map", sub: "560 cases opened, 0 failed" },
    { title: "Step Functions, one per case", sub: "task tokens · deadlines · escalation" }] },
  { title: "2 · THE VILLAGE IS WARNED", boxes: [
    { title: "Case-step Lambda", sub: "advice for this contaminant" },
    { title: "Amazon Polly", sub: "Kajal voice, Hindi + English" },
    { title: "Telegram bot + Web Push", sub: "Lambda function URL · app alerts" },
    { title: "Health worker, villagers", sub: "Hindi or English, text and voice", tone: "people" }] },
  { title: "3 · THEY ASK BY VOICE (ASK SROT)", boxes: [
    { title: "Amazon Transcribe", sub: "streaming, Hindi voice notes" },
    { title: "Amazon Translate", sub: "Hindi ⇄ English" },
    { title: "Strands agent · Bedrock", sub: "Nova Pro, reads only this village" },
    { title: "Bedrock Guardrails", sub: "grounded, or the official advice", tone: "policy" }] },
  { title: "4 · SOMEONE MUST FIX IT", boxes: [
    { title: "Block engineer", sub: "logs the fix: web link or Telegram", tone: "people" },
    { title: "Bedrock · Nova Pro vision", sub: "reads the field-kit vial (advice only)" },
    { title: "Amazon Verified Permissions", sub: "Cedar: only a lab pass closes", tone: "policy" },
    { title: "Amazon SES", sub: "overdue cases → district official" }] },
];
const FOUNDATION = ["Amazon DynamoDB", "Amazon S3", "Amazon CloudFront", "Amazon API Gateway", "AWS Lambda",
  "Amazon Location Service", "Amazon EventBridge Scheduler", "AWS Systems Manager Parameter Store", "AWS X-Ray",
  "Amazon CloudWatch dashboard + metrics", "AWS CDK"];

export function Architecture() {
  const laneY = (i) => 34 + i * 104;
  let cx = 24, cy = 482;
  const chips = FOUNDATION.map((name) => {
    const w = Math.round(18 + name.length * 6.7);
    if (cx + w > 1076) { cx = 24; cy += 40; }
    const chip = { name, x: cx, y: cy, w };
    cx += w + 10;
    return chip;
  });
  const H = cy + 74;
  return (
    <div className="arch-scroll">
      <svg className="arch" viewBox={`0 0 1100 ${H}`} role="img" aria-label="Srot architecture on AWS">
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0 0 L10 5 L0 10 z" fill="#587080" />
          </marker>
        </defs>
        {LANES.map((lane, i) => (
          <g key={lane.title}>
            <text x="24" y={laneY(i)} fontSize="12.5" fontWeight="700" letterSpacing="0.06em" fill="#587080">{lane.title}</text>
            {lane.boxes.map((b, j) => <Box key={b.title} x={COLS[j]} y={laneY(i) + 12} {...b} />)}
            {[0, 1, 2].map((j) => (
              <path key={j} d={`M${COLS[j] + 238} ${laneY(i) + 42} L${COLS[j + 1] - 3} ${laneY(i) + 42}`}
                fill="none" stroke="#587080" strokeWidth="1.6" markerEnd="url(#arrow)" />
            ))}
          </g>
        ))}
        <text x="24" y="470" fontSize="12.5" fontWeight="700" letterSpacing="0.06em" fill="#587080">UNDER ALL OF IT</text>
        {chips.map((c) => (
          <g key={c.name}>
            <rect x={c.x} y={c.y} width={c.w} height="28" rx="14" fill="#f4f7f8" stroke="#c9d6dc" />
            <text x={c.x + c.w / 2} y={c.y + 18.5} textAnchor="middle" fontSize="12" fill="#0b2a3c">{c.name}</text>
          </g>
        ))}
        <text x="24" y={H - 16} fontSize="12" fill="#587080">One stack, deployed with AWS CDK (Python) to ap-south-1 (Mumbai). Every Lambda and workflow is traced in X-Ray.</text>
      </svg>
    </div>
  );
}

export default function Impact() {
  const { t } = useLang();
  const { data: s, error, loading, reload } = useApi("/stats");
  if (loading && !s) return <div className="wrap" style={{ padding: "24px 16px" }}><Loading /></div>;
  if (error && !s) return <div className="wrap" style={{ padding: "24px 16px" }}><ErrorBox error={error} onRetry={reload} /></div>;
  const rep = s.repeat_failures;
  const scale = s.scale_run;
  const cost = (scale && scale.cost_estimate) || (s.last_run && s.last_run.cost_estimate); // the scale run, the number quoted elsewhere
  const located = s.villages_on_map;
  const maxBar = rep ? Math.max(...rep.by_state_and_parameter.map((r) => r.failed_last_year)) : 1;
  return (
    <div className="page wrap stack" style={{ padding: "24px 16px" }}>
      <div>
        <h1 className="section-title display">{t("impact_title")}</h1>
        <p className="muted" style={{ margin: 0 }}>{t("impact_body")}</p>
      </div>

      <div className="kpi">
        <div className="card"><b>{s.cases}</b>cases from real government lab failures ({s.villages} villages, UP and Rajasthan)</div>
        <div className="card"><b>{chemicalShare(s)}%</b>are nitrate, fluoride or arsenic, where boiling does not help</div>
        {rep && <div className="card"><b>{rep.totals.both}</b>villages failed the same test again the next year ({Math.round(rep.totals.share_of_last_year_failing_again * 1000) / 10}% of last year's, with half a year still to come)</div>}
        {scale && scale.items && <div className="card"><b>{scale.items.succeeded}/{scale.items.total}</b>case workflows started in one paced run, {scale.items.failed} failed, {secs(scale.seconds)}</div>}
        {s.alert_latency && <div className="card"><b>{secs(s.alert_latency.median_s)}</b>median from failed test found to village warned (p95 {secs(s.alert_latency.p95_s)})</div>}
        {cost && <div className="card"><b>${cost.usd_total}</b>estimated AWS cost of {scale && scale.cost_estimate ? "the scale run" : "the last ingest"} ({cost.usd_per_case ? `$${cost.usd_per_case} per case` : "–"}); voice notes are made only when someone listens</div>}
        <div className="card weak"><b>{s.villages - located}</b>villages without a trustworthy map pin; most pins are block or district centres, drawn hollow</div>
        <div className="card weak"><b>Simulated</b>lab re-tests in the demo. Real closure needs the lab's re-test result; the field kit only marks a case provisionally safe</div>
      </div>

      {rep && (
        <section className="card">
          <h3 style={{ marginBottom: 4 }}>Failed last year, and again this year</h3>
          <p className="small muted" style={{ marginTop: 0 }}>{rep.source}. Grey: villages that failed in FY 2025-26. Red: of those, failed again for the same parameter in FY 2026-27.</p>
          <div className="bars">
            {rep.by_state_and_parameter.filter((r) => r.failed_last_year).map((r) => (
              <div className="bar-row" key={`${r.state}-${r.parameter}`}>
                <span>{PARAM[r.parameter] || r.parameter}, {r.state === "Uttar Pradesh" ? "UP" : "Rajasthan"}</span>
                <div className="track">
                  <span style={{ width: `${(r.failed_last_year / maxBar) * 100}%` }} />
                  <span className="both" style={{ width: `${(r.failed_both_years / maxBar) * 100}%` }} />
                </div>
                <span className="small"><b>{r.failed_both_years}</b> / {r.failed_last_year}</span>
              </div>
            ))}
          </div>
          <ul className="small muted">{rep.caveats.map((c, i) => <li key={i}>{c}</li>)}</ul>
        </section>
      )}

      <section className="stack">
        <h2 className="section-title display">Architecture</h2>
        <Architecture />
      </section>
    </div>
  );
}

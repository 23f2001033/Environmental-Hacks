import { ErrorBox, Loading, useApi } from "../components.jsx";
import { useLang } from "../i18n.jsx";
import { chemicalShare } from "./Home.jsx";

const PARAM = { Ecoil: "E. coli", Coliform: "Coliform", Nitrate: "Nitrate", Fluoride: "Fluoride", "Total arsenic": "Arsenic" };

function secs(s) {
  if (s == null) return "–";
  return s < 120 ? `${Math.round(s)} s` : s < 7200 ? `${Math.round(s / 60)} min` : `${(s / 3600).toFixed(1)} h`;
}

function Box({ x, y, w, h, title, sub, tone = "aws" }) {
  const fill = { aws: "#fff7ec", data: "#eef7fb", people: "#eef8f1", policy: "#fbeeee" }[tone];
  const stroke = { aws: "#e08a00", data: "#1d5a78", people: "#23804f", policy: "#c2412d" }[tone];
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx="10" fill={fill} stroke={stroke} strokeWidth="1.5" />
      <text x={x + w / 2} y={y + (sub ? h / 2 - 3 : h / 2 + 5)} textAnchor="middle" fontSize="14" fontWeight="700" fill="#0b2a3c">{title}</text>
      {sub && <text x={x + w / 2} y={y + h / 2 + 15} textAnchor="middle" fontSize="11.5" fill="#587080">{sub}</text>}
    </g>
  );
}

function Arrow({ d, label, lx, ly }) {
  return (
    <g>
      <path d={d} fill="none" stroke="#587080" strokeWidth="1.6" markerEnd="url(#arrow)" />
      {label && <text x={lx} y={ly} fontSize="11" fill="#587080" textAnchor="middle">{label}</text>}
    </g>
  );
}

export function Architecture() {
  return (
    <svg className="arch" viewBox="0 0 1100 560" role="img" aria-label="JalSaathi architecture on AWS">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" fill="#587080" />
        </marker>
      </defs>
      <text x="24" y="34" fontSize="13" fontWeight="700" fill="#587080">DATA</text>
      <Box x={24} y={48} w={190} h={64} title="JJM-WQMIS portal" sub="government lab results" tone="data" />
      <Box x={24} y={140} w={190} h={64} title="EventBridge" sub="daily schedule" />
      <Box x={260} y={92} w={190} h={64} title="Ingest Lambda" sub="parse · guard · plan cases" />
      <Box x={260} y={186} w={190} h={64} title="Amazon Location" sub="geocode, checked by name" />
      <Box x={500} y={48} w={200} h={64} title="DynamoDB" sub="villages · cases · timeline" />
      <Box x={500} y={140} w={200} h={64} title="S3" sub="snapshot · voice notes · photos" />

      <text x="24" y="292" fontSize="13" fontWeight="700" fill="#587080">ONE WORKFLOW PER CASE</text>
      <Box x={24} y={306} w={210} h={64} title="Step Functions ScaleRun" sub="Distributed Map, ~1 case/s" />
      <Box x={280} y={306} w={210} h={64} title="Step Functions case" sub="task tokens · deadlines" />
      <Box x={540} y={306} w={170} h={64} title="Cedar policy" sub="close needs lab pass" tone="policy" />
      <Box x={280} y={400} w={210} h={64} title="Case-step Lambda" sub="alert · escalate · close" />
      <Box x={540} y={400} w={170} h={64} title="Amazon Polly" sub="Kajal: Hindi + English" />

      <text x="760" y="34" fontSize="13" fontWeight="700" fill="#587080">PEOPLE</text>
      <Box x={760} y={48} w={300} h={64} title="Web app (this site)" sub="S3 + CloudFront · Web Push" tone="people" />
      <Box x={760} y={140} w={300} h={64} title="API Gateway + API Lambda" sub="village, engineer, relay, officials" />
      <Box x={760} y={232} w={300} h={64} title="Telegram bot" sub="Lambda function URL webhook" tone="people" />
      <Box x={760} y={324} w={300} h={64} title="Amazon Bedrock · Nova Pro" sub="reads the field-kit photo (advice only)" />
      <Box x={760} y={416} w={300} h={64} title="Villagers · relays · engineers" sub="Hindi or English, phone first" tone="people" />

      <Arrow d="M214 80 L258 112" />
      <Arrow d="M214 172 L258 132" />
      <Arrow d="M355 156 L355 184" />
      <Arrow d="M450 112 L498 86" />
      <Arrow d="M450 128 L498 166" />
      <Arrow d="M355 250 C 355 280 130 280 130 304" label="many cases" lx="240" ly="276" />
      <Arrow d="M234 338 L278 338" />
      <Arrow d="M385 370 L385 398" />
      <Arrow d="M490 338 L538 338" label="every action" lx="514" ly="330" />
      <Arrow d="M490 432 L538 432" />
      <Arrow d="M600 112 C 650 112 700 172 758 172" />
      <Arrow d="M490 418 C 640 418 680 264 758 264" label="alerts" lx="680" ly="300" />
      <Arrow d="M910 112 L910 138" />
      <Arrow d="M910 204 L910 230" />
      <Arrow d="M910 296 L910 322" />
      <Arrow d="M910 388 L910 414" />
      <text x="24" y="530" fontSize="12" fill="#587080">AWS CDK (Python) deploys everything in one stack · ap-south-1 (Mumbai) · CloudWatch alarm on ingest failures</text>
    </svg>
  );
}

export default function Impact() {
  const { t } = useLang();
  const { data: s, error, loading, reload } = useApi("/stats");
  if (loading && !s) return <div className="wrap" style={{ padding: "24px 16px" }}><Loading /></div>;
  if (error && !s) return <div className="wrap" style={{ padding: "24px 16px" }}><ErrorBox error={error} onRetry={reload} /></div>;
  const rep = s.repeat_failures;
  const scale = s.scale_run;
  const cost = s.last_run && s.last_run.cost_estimate;
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
        {cost && <div className="card"><b>${cost.usd_total}</b>estimated AWS cost of the last ingest ({cost.usd_per_case ? `$${cost.usd_per_case} per case` : "–"}); voice notes are made only when someone listens</div>}
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

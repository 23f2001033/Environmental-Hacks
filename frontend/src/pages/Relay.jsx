import { useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { linkToken, post, toJpeg } from "../api.js";
import { ErrorBox, Loading, PushButton, useApi } from "../components.jsx";
import { useLang } from "../i18n.jsx";
import { CaseCard } from "./Village.jsx";

function KitTest({ c, village, k, onDone }) {
  const { t, lang } = useLang();
  const [stage, setStage] = useState("photo");
  const [preview, setPreview] = useState(null);
  const [photoKey, setPhotoKey] = useState(null);
  const [hint, setHint] = useState(null);
  const [err, setErr] = useState("");

  const onFile = async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    setErr("");
    try {
      setStage("uploading");
      const jpeg = await toJpeg(file);
      setPreview(URL.createObjectURL(jpeg));
      const up = await post(`/relay/${encodeURIComponent(village)}/upload`, { case_id: c.case_id, k });
      const put = await fetch(up.upload_url, { method: "PUT", headers: { "content-type": "image/jpeg" }, body: jpeg });
      if (!put.ok) throw new Error(`upload failed (${put.status})`);
      setPhotoKey(up.photo_key);
      setStage("reading");
      const h = await post(`/relay/${encodeURIComponent(village)}/hint`, { case_id: c.case_id, k, photo_key: up.photo_key, lang });
      setHint(h);
      setStage("choose");
    } catch (ex) { setErr(ex.message); setStage(photoKey ? "choose" : "photo"); }
  };

  const choose = async (result) => {
    setStage("saving");
    try {
      await post(`/relay/${encodeURIComponent(village)}/kit`, { case_id: c.case_id, k, result, photo_key: photoKey });
      setStage("done");
      onDone();
    } catch (ex) { setErr(ex.message); setStage("choose"); }
  };

  if (stage === "done") return <div className="notice ok">{t("relay_done")}</div>;
  return (
    <div className="stack" style={{ gap: 12 }}>
      <div><b>{t("relay_step_photo")}</b></div>
      <label className="btn btn-dark" style={{ width: "fit-content" }}>
        📷 {t("relay_take_photo")}
        <input type="file" accept="image/*" capture="environment" onChange={onFile} hidden />
      </label>
      {preview && <img className="photo-preview" src={preview} alt="" />}
      {stage === "uploading" && <div className="small muted">{t("relay_uploading")}</div>}
      {stage === "reading" && <div className="small muted">{t("relay_reading")}</div>}
      {hint && hint.hint && (
        <div className="hint">
          <b>{t("relay_step_hint")}</b>
          <div style={{ marginTop: 6 }}>🤖 <b>{t("relay_ai")}</b>: <span dangerouslySetInnerHTML={{ __html: hint.message }} /></div>
          <div className="small muted">{t("relay_ai_note")} ({hint.hint.confidence})</div>
        </div>
      )}
      {(stage === "choose" || stage === "saving") && (
        <div>
          <b>{t("relay_step_result")}</b>
          <div className="kit-choice">
            <button className="black" disabled={stage === "saving"} onClick={() => choose("contaminated")}><i className="vial black" />{t("relay_black")}</button>
            <button className="yellow" disabled={stage === "saving"} onClick={() => choose("clean")}><i className="vial yellow" />{t("relay_yellow")}</button>
          </div>
        </div>
      )}
      {err && <div className="notice err">{err}</div>}
    </div>
  );
}

export default function Relay() {
  const { village } = useParams();
  const { search } = useLocation();
  const { t, lang } = useLang();
  const k = linkToken("v", village, search);
  const access = useApi(k ? `/access?role=v&key=${encodeURIComponent(village)}&k=${encodeURIComponent(k)}` : null);
  const { data: b, error, loading, reload } = useApi(`/villages/${encodeURIComponent(village)}`, { poll: 15000 });
  const canAct = !!(access.data && access.data.valid);

  if (loading && !b) return <div className="wrap" style={{ padding: "24px 16px" }}><Loading /></div>;
  if (error && !b) return <div className="wrap" style={{ padding: "24px 16px" }}><ErrorBox error={error} onRetry={reload} /></div>;
  const waiting = b.cases.filter((c) => c.status === "AWAITING_RETEST");
  return (
    <div className="page wrap stack" style={{ padding: "20px 16px" }}>
      <div className={`banner ${b.status}`}>
        <div className="small" style={{ opacity: 0.85 }}>{t("relay_title")}</div>
        <h1 className="display">{b.village.name}</h1>
        <div className="status">{b.status_text[lang]}</div>
      </div>
      <div className="row">
        {canAct ? <span className="pill green">✓ {t("relay_link_ok")}</span> : <span className="notice" style={{ flex: 1 }}>{t("relay_readonly")}</span>}
        <span className="spacer" />
        <PushButton scope="village" keyName={b.village.key} />
      </div>
      {canAct && waiting.length === 0 && <div className="notice">{t("relay_nothing")}</div>}
      {b.cases.filter((c) => c.status !== "CLOSED").map((c) => (
        <CaseCard key={c.case_id} c={c}>
          {canAct && c.status === "AWAITING_RETEST" && <KitTest c={c} village={village} k={k} onDone={reload} />}
        </CaseCard>
      ))}
    </div>
  );
}

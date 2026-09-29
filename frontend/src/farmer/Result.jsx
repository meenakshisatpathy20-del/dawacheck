import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, fileUrl, reminders } from "../api.js";
import { useStore } from "../store.jsx";
import { t } from "../strings.js";
import { speak, speakVerdict, stopSpeaking, verdictTone } from "../voice.js";
import { GearIcons, MeasuringCap, RuleList, Shell, VerdictBanner } from "./common.jsx";
import { useScan } from "./ScanPacket.jsx";

// One decision per screen (playbook section 12):
// confirm product -> verdict -> (red label: confirm gear) -> dose + safety -> saved
export default function Result() {
  const s = useStore();
  const loc = useLocation();
  const r = loc.state || JSON.parse(sessionStorage.getItem("dc.last") || "null");
  // Confirm whenever the product was read from the pack (QR or photo) or the match is uncertain;
  // not when the farmer picked it from the list or has just confirmed it.
  const needsConfirm = r && !r.confirmed && (r.identified?.needs_confirmation || (!r.product && r.candidates?.length)
    || /qr|ocr/.test(r.identified?.method || ""));
  const first = r?.start_step || (needsConfirm ? "confirm" : "verdict");
  const [step, setStep] = useState(first);
  useEffect(() => setStep(first), [r]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!r) return <Shell><div className="card">—</div></Shell>;
  const steps = ["confirm", "verdict", "dose"];
  const dots = <div className="steps">{steps.map((x) => <i key={x} className={steps.indexOf(x) <= steps.indexOf(step === "redconfirm" ? "verdict" : step === "saved" ? "dose" : step) ? "on" : ""} />)}</div>;
  return (
    <Shell>
      {dots}
      {r.offline && <div className="banner">📴 {t(s.lang, "offline")} ({r.cached_at?.slice(0, 10)})</div>}
      {step === "confirm" && <Confirm r={r} onYes={() => setStep("verdict")} />}
      {step === "verdict" && <Verdict r={r} onNext={() => setStep(r.safety?.toxicity_colour === "red" ? "redconfirm" : "dose")} />}
      {step === "redconfirm" && <RedConfirm r={r} onOk={() => setStep("dose")} />}
      {(step === "dose" || step === "saved") && <Dose r={r} saved={step === "saved"} onSaved={() => setStep("saved")} />}
    </Shell>
  );
}

function Confirm({ r, onYes }) {
  const s = useStore();
  const nav = useNavigate();
  const scan = useScan();
  const [edits, setEdits] = useState({});
  const photo = r.local_photo || fileUrl(r.image_url);
  const checks = Object.entries(r.field_checks || {});
  const low = new Set([...(r.check_fields || []), ...(r.mismatch || [])]);

  useEffect(() => {
    if (r.product) speak(`${r.product.brand}. ${r.product.active_ingredient} ${r.product.strength_pct}% ${r.product.form_type}. ${t(s.lang, "correct")}`, r.tts_locale);
    return stopSpeaking;
  }, [r, s.lang]);

  const yes = async () => {
    if (Object.keys(edits).length) {
      await scan({ product_id: r.product.id, fields: { ...r.extracted, ...edits }, read_from_pack: true });
    } else onYes();
  };

  return (
    <>
      <h2 style={{ margin: "4px 0 10px" }}>{t(s.lang, "confirm")}</h2>
      {photo && <img className="pack-photo" src={photo} alt="pack" />}
      {r.product && (
        <div className="card">
          <div style={{ fontSize: "1.4rem", fontWeight: 800 }}>{r.product.brand}</div>
          <div className="muted">{r.product.formulation} · {r.product.company}</div>
          {r.mismatch?.length > 0 && <div className="banner">⚠️ {t(s.lang, "checkField")}: {r.mismatch.join(", ")}</div>}
        </div>
      )}
      {checks.length > 0 && (
        <div className="card">
          {checks.map(([k, fc]) => (
            <div key={k} className={`crop-row ${low.has(k) ? "low" : ""}`}>
              {fc.crop_url ? <img src={fileUrl(fc.crop_url)} alt={k} /> : <span />}
              <label className="small">{k.replace("_", " ")}{low.has(k) && <> · <b style={{ color: "var(--yellow)" }}>{t(s.lang, "checkField")}</b></>}
                <input className="lang" style={{ width: "100%" }} defaultValue={fc.value}
                  onChange={(e) => setEdits({ ...edits, [k]: e.target.value })} /></label>
            </div>
          ))}
        </div>
      )}
      {r.product && (
        <div className="row">
          <button className="btn" style={{ flex: 1 }} onClick={yes}>✓ {t(s.lang, "yes")}</button>
          <button className="btn secondary" style={{ flex: 1 }} onClick={() => nav("/scan")}>✕ {t(s.lang, "no")}</button>
        </div>
      )}
      {r.candidates?.filter((c) => c.id !== r.product?.id).length > 0 && (
        <div className="card">
          <h3>{t(s.lang, "orPick")}</h3>
          {r.candidates.filter((c) => c.id !== r.product?.id).map((c) => (
            <div className="row" key={c.id} style={{ padding: "6px 0" }}>
              <div className="spacer"><strong>{c.brand}</strong><div className="muted small">{c.formulation}</div></div>
              <button className="btn secondary" onClick={() => scan({ product_id: c.id, fields: r.extracted, read_from_pack: true })}>✓</button>
            </div>
          ))}
        </div>
      )}
      {!r.product && <AddProduct r={r} />}
    </>
  );
}

function Verdict({ r, onNext }) {
  const s = useStore();
  const scan = useScan();
  const [why, setWhy] = useState(null);
  const [showBetter, setShowBetter] = useState(false);
  const rest = useMemo(() => r.fired.filter((f) => f.verdict !== "info").map((f) => f.message).join(" "), [r]);

  useEffect(() => {
    verdictTone(r.verdict);
    speakVerdict({ verdict: r.verdict, lang: s.lang, locale: r.tts_locale, rest, headline: r.headline });
    return stopSpeaking;
  }, [r, s.lang, rest]);

  const reason = r.fired.find((f) => f.verdict === r.verdict) || r.fired[0];
  return (
    <>
      <VerdictBanner verdict={r.verdict} headline={r.headline}
        sub={r.product ? `${r.product.brand} · ${r.product.formulation}` : r.identified?.formulation} />
      {reason && <div className="card" style={{ fontSize: "1.15rem", fontWeight: 600 }}>{reason.message}</div>}
      <div className="row">
        <button className="btn secondary" onClick={() => speakVerdict({ verdict: r.verdict, lang: s.lang, locale: r.tts_locale, rest, headline: r.headline })}>🔊 {t(s.lang, "listen")}</button>
        <button className="btn secondary" onClick={async () =>
          setWhy(await api.explain(r.fired, s.lang, { product_id: r.product?.id, crop: s.crop, pest: s.pest }).catch(() => ({ text: "" })))}>❓ {t(s.lang, "why")}</button>
        {r.suggestions?.length > 0 && <button className="btn secondary" onClick={() => setShowBetter(!showBetter)}>💡 {t(s.lang, "better")}</button>}
      </div>
      {why && (
        <div className="card">
          {why.text && <p style={{ marginTop: 0 }}>{why.text}</p>}
          <RuleList fired={r.fired} showSource />
          {r.claim && (
            <div className="rule green">
              <div><span className="pill green">✓</span> {r.product?.formulation}: {r.claim.crop} · {r.claim.pest} ·{" "}
                {r.claim.dose_form_ha.filter((x) => x != null).join("–")} {r.claim.unit}/ha · PHI {r.claim.phi_days ?? "—"} d</div>
              <div className="src">Label claim · source: {r.claim.source_file}{r.claim.page ? `, page ${r.claim.page}` : ""}</div>
            </div>
          )}
        </div>
      )}
      {showBetter && (
        <div className="card">
          <ul className="list">
            {r.suggestions.slice(0, 4).map((o) => (
              <li key={o.formulation_id}>
                <div className="spacer"><strong>{o.formulation}</strong>
                  <div className="small muted">{o.products.map((p) => p.brand).join(", ")} · PHI {o.claim.phi_days ?? "—"} d · {o.moa_scheme} {o.moa_group}</div></div>
                {o.products[0] && <button className="btn secondary" onClick={() => scan({ product_id: o.products[0].id })}>›</button>}
              </li>
            ))}
          </ul>
        </div>
      )}
      {r.export_flags?.length > 0 && <div className="banner">🌍 {r.export_flags.map((e) => `${e.market}: ${e.note}`).join(" · ")}</div>}
      {!r.product && <AddProduct r={r} />}
      {r.product && r.verdict !== "red" && <button className="btn block" style={{ marginTop: 12 }} onClick={onNext}>{t(s.lang, "next")} →</button>}
      {r.data_note && <p className="small muted">ⓘ {t(s.lang, "sampleData")}: {r.data_note}</p>}
      <Report r={r} />
    </>
  );
}

function RedConfirm({ r, onOk }) {
  const s = useStore();
  useEffect(() => { speak(r.safety.red_confirm, r.tts_locale); return stopSpeaking; }, [r]);
  return (
    <div className="verdict v-red" style={{ textAlign: "left" }}>
      <div className="ico" style={{ textAlign: "center" }}>🔺</div>
      <h1 style={{ textAlign: "center" }}>{r.safety.colour_meaning}</h1>
      <p style={{ color: "var(--ink)" }}>{r.safety.red_confirm}</p>
      <GearIcons colour="red" />
      <p style={{ color: "var(--ink)" }}>{r.safety.gear}</p>
      <button className="btn danger block" onClick={onOk}>✓ {t(s.lang, "wearGear")}</button>
    </div>
  );
}

function Dose({ r, saved, onSaved }) {
  const s = useStore();
  const scan = useScan();
  const [weather, setWeather] = useState(null);
  const [res, setRes] = useState(null);

  useEffect(() => {
    api.weather({ lat: s.gps?.lat, lon: s.gps?.lon, lang: s.lang }).then(setWeather).catch(() => {});
    speak([r.dose?.text, r.safety?.gear].filter(Boolean).join(" "), r.tts_locale);
    return stopSpeaking;
  }, [r, s.gps, s.lang]);

  const save = async () => {
    const out = await api.sprayLog({ plot_id: s.plot, crop: s.crop, state: s.state, pest: s.pest, product_id: r.product.id,
      spray_date: new Date().toISOString().slice(0, 10), area_acre: s.area, tanks: r.dose?.tanks, user_id: s.userId, lang: s.lang });
    setRes(out);
    if (out.plot_safe_harvest_date) {
      s.set({ lastSafe: out.plot_safe_harvest_date });
      reminders.add({ plot: s.plot, crop: s.crop, date: out.plot_safe_harvest_date });
    }
    speak(out.text, r.tts_locale);
    onSaved();
  };

  return (
    <>
      {r.dose?.ok && (
        <div className="card">
          <h3>🥛 {t(s.lang, "dose")}</h3>
          <div className="row" style={{ alignItems: "center" }}>
            {r.dose.mode === "tank" && <MeasuringCap amount={r.dose.per_tank} unit={r.dose.unit} />}
            <div className="spacer" style={{ fontSize: "1.3rem", fontWeight: 800 }}>{r.dose.text}</div>
          </div>
          {r.dose.mode === "tank" && <div className="small muted">{r.dose.per_tank_range.join("–")} {r.dose.unit} · {r.dose.water_l} L · {r.dose.note}</div>}
          <div className="row" style={{ marginTop: 8 }}>
            <label className="field" style={{ flex: 1 }}>{t(s.lang, "area")}
              <input type="number" min="0.1" step="0.1" value={s.area} onChange={(e) => s.set({ area: Number(e.target.value) })} /></label>
            <label className="field" style={{ flex: 1 }}>{t(s.lang, "pump")}
              <input type="number" min="5" step="1" value={s.pump} onChange={(e) => s.set({ pump: Number(e.target.value) })} /></label>
            <button className="btn secondary" onClick={() => scan({ product_id: r.product.id, start_step: "dose" })}>↻</button>
          </div>
        </div>
      )}
      {r.safety && (
        <div className="card">
          <div className="row"><span className="tri" style={{ color: `var(--${r.safety.toxicity_colour === "blue" ? "blue" : r.safety.toxicity_colour})` }} />
            <strong>{r.safety.colour_meaning}</strong></div>
          <GearIcons colour={r.safety.toxicity_colour} />
          <p>{r.safety.gear}</p>
          {r.safety.antidote_from_label && <p className="small muted">Label: {r.safety.antidote_from_label}</p>}
        </div>
      )}
      {weather?.status === "ok" && <div className="card">🌦️ <strong>{t(s.lang, "weather")}:</strong> {weather.text}</div>}
      {r.phi && !saved && <div className="card">📅 {r.phi.text}</div>}
      {!saved && <button className="btn block" onClick={save}>💾 {t(s.lang, "save")}</button>}
      {saved && res && (
        <div className="card">
          <strong>✅ {t(s.lang, "saved")}</strong>
          <RuleList fired={res.fired} />
          {res.plot_safe_harvest_date && (
            <>
              <p>{t(s.lang, "safeFrom")}: <strong>{res.plot_safe_harvest_date}</strong> · 🔔 {t(s.lang, "reminderSet")}</p>
              <a className="btn secondary block" style={{ display: "block", textAlign: "center", textDecoration: "none" }}
                href={api.reminderUrl(s.plot)}>📅 {t(s.lang, "addCalendar")}</a>
            </>
          )}
          {res.rotation?.status === "change" && <div className="banner">{res.rotation.text}</div>}
        </div>
      )}
    </>
  );
}

function AddProduct({ r }) {
  const s = useStore();
  const ex = r.extracted || {};
  const [f, setF] = useState({ brand: ex.brand || "", active_ingredient: ex.active_ingredient || "",
    strength_pct: ex.strength_pct || "", formulation: ex.formulation || "", reg_no: ex.reg_no || "" });
  const [photo, setPhoto] = useState(null);
  const [done, setDone] = useState(false);
  if (done) return <div className="card">✅ {t(s.lang, "submitted")}</div>;
  const fields = [["brand", "brand"], ["active_ingredient", "chemical"], ["strength_pct", "strength"], ["formulation", "form"], ["reg_no", "Reg. No."]];
  return (
    <div className="card">
      <h3>➕ {t(s.lang, "addThis")}</h3>
      {fields.map(([k, label]) => (
        <div className="field" key={k}><label>{t(s.lang, label)}</label>
          <input value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></div>
      ))}
      <div className="field"><label>{t(s.lang, "photo")}</label>
        <input type="file" accept="image/*" capture="environment" onChange={(e) => setPhoto(e.target.files?.[0] || null)} /></div>
      <button className="btn block" disabled={!f.brand}
        onClick={async () => { await api.submitProduct({ ...f, user_id: s.userId, photo }); setDone(true); }}>{t(s.lang, "send")}</button>
    </div>
  );
}

function Report({ r }) {
  const s = useStore();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [photo, setPhoto] = useState(null);
  const [done, setDone] = useState(false);
  if (!r.scan_id) return null;
  if (done) return <p className="muted">{t(s.lang, "reported")}</p>;
  if (!open) return <button className="btn secondary block" style={{ marginTop: 12 }} onClick={() => setOpen(true)}>🚩 {t(s.lang, "report")}</button>;
  return (
    <div className="card">
      <div className="field"><label>{t(s.lang, "reason")}</label><input value={reason} onChange={(e) => setReason(e.target.value)} /></div>
      <div className="field"><label>{t(s.lang, "photo")}</label>
        <input type="file" accept="image/*" capture="environment" onChange={(e) => setPhoto(e.target.files?.[0] || null)} /></div>
      <button className="btn block" disabled={!reason}
        onClick={async () => { await api.report({ scan_id: r.scan_id, reason, photo }); setDone(true); }}>{t(s.lang, "send")}</button>
    </div>
  );
}

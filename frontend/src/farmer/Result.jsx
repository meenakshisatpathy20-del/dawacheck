import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useStore } from "../store.jsx";
import { t } from "../strings.js";
import { speak, stopSpeaking, verdictTone } from "../voice.js";
import { RuleList, Shell, VerdictBanner } from "./common.jsx";
import { useScan } from "./ScanPacket.jsx";

export default function Result() {
  const s = useStore();
  const loc = useLocation();
  const nav = useNavigate();
  const scan = useScan();
  const r = loc.state || JSON.parse(sessionStorage.getItem("dc.last") || "null");
  const [why, setWhy] = useState(null);
  const [gearOk, setGearOk] = useState(false);
  const [saved, setSaved] = useState(null);
  const [weather, setWeather] = useState(null);
  const [reported, setReported] = useState(false);

  const confirming = r && (r.identified?.needs_confirmation || (!r.product && r.candidates?.length));

  useEffect(() => {
    if (!r || confirming) return;
    verdictTone(r.verdict);
    speak([r.speech, r.dose?.text].filter(Boolean).join(" "), r.tts_locale);
    return stopSpeaking;
  }, [r, confirming]);

  useEffect(() => {
    if (!r?.product || r.verdict === "red") return;
    api.weather({ lat: s.gps?.lat, lon: s.gps?.lon, lang: s.lang }).then(setWeather).catch(() => {});
  }, [r, s.gps, s.lang]);

  if (!r) return <Shell><div className="card">—</div></Shell>;

  if (confirming) {
    return (
      <Shell title={t(s.lang, "confirm")}>
        {r.candidates.map((c) => (
          <div className="card row" key={c.id}>
            <div className="spacer"><strong>{c.brand}</strong><div className="muted small">{c.formulation}</div></div>
            <button className="btn" onClick={() => scan({ product_id: c.id, fields: r.extracted })}>{t(s.lang, "yes")}</button>
          </div>
        ))}
        <button className="btn secondary block" onClick={() => nav("/scan")}>{t(s.lang, "no")}</button>
      </Shell>
    );
  }

  const red = r.verdict === "red";
  const redLabel = r.safety?.toxicity_colour === "red";
  const save = async () => {
    const res = await api.sprayLog({ plot_id: s.plot, crop: s.crop, state: s.state, pest: s.pest, product_id: r.product.id,
      spray_date: new Date().toISOString().slice(0, 10), area_acre: s.area, tanks: r.dose?.tanks, user_id: s.userId, lang: s.lang });
    setSaved(res);
    if (res.plot_safe_harvest_date) s.set({ lastSafe: res.plot_safe_harvest_date });
    speak(res.text, r.tts_locale);
  };

  return (
    <Shell>
      {r.offline && <div className="banner">📴 {t(s.lang, "offline")} ({r.cached_at?.slice(0, 10)})</div>}
      <VerdictBanner verdict={r.verdict} headline={r.headline}
        sub={r.product ? `${r.product.brand} · ${r.product.formulation}` : r.identified?.formulation} />
      <RuleList fired={r.fired} showSource={!!why} />
      <div className="row">
        <button className="btn secondary" onClick={() => speak([r.speech, r.dose?.text].filter(Boolean).join(" "), r.tts_locale)}>🔊 {t(s.lang, "listen")}</button>
        {r.fired.length > 0 && <button className="btn secondary" onClick={async () => setWhy(await api.explain(r.fired, s.lang).catch(() => ({ text: "" })))}>❓ {t(s.lang, "why")}</button>}
      </div>
      {why?.text && <div className="card small">{why.text}</div>}

      {r.suggestions?.length > 0 && (
        <div className="card">
          <h3>💡 {t(s.lang, "better")}</h3>
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

      {!red && r.dose?.ok && (
        <div className="card">
          <h3>🥛 {t(s.lang, "dose")}</h3>
          <div style={{ fontSize: "1.4rem", fontWeight: 800 }}>{r.dose.text}</div>
          {r.dose.mode === "tank" && <div className="small muted">{r.dose.per_tank_range.join("–")} {r.dose.unit} · {r.dose.water_l} L · {r.dose.note}</div>}
          <div className="row" style={{ marginTop: 8 }}>
            <label className="field" style={{ flex: 1 }}>{t(s.lang, "area")}
              <input type="number" min="0.1" step="0.1" value={s.area} onChange={(e) => s.set({ area: Number(e.target.value) })} /></label>
            <label className="field" style={{ flex: 1 }}>{t(s.lang, "pump")}
              <input type="number" min="5" step="1" value={s.pump} onChange={(e) => s.set({ pump: Number(e.target.value) })} /></label>
            <button className="btn secondary" onClick={() => scan({ product_id: r.product.id })}>↻</button>
          </div>
        </div>
      )}
      {!red && r.phi && <div className="card">📅 {r.phi.text}</div>}
      {r.safety && (
        <div className="card">
          <div className="row"><span className="tri" style={{ color: `var(--${r.safety.toxicity_colour === "blue" ? "blue" : r.safety.toxicity_colour})` }} />
            <strong>{r.safety.colour_meaning}</strong></div>
          <p>🧤 {r.safety.gear}</p>
          {r.safety.antidote_from_label && <p className="small muted">Label: {r.safety.antidote_from_label}</p>}
        </div>
      )}
      {weather?.status === "ok" && <div className={`card`}>🌦️ <strong>{t(s.lang, "weather")}:</strong> {weather.text}</div>}
      {r.export_flags?.length > 0 && <div className="banner">🌍 {r.export_flags.map((e) => `${e.market}: ${e.note}`).join(" · ")}</div>}
      {r.data_note && <div className="small muted">ⓘ {t(s.lang, "sampleData")}: {r.data_note}</div>}

      {r.product && !red && !saved && (
        <div className="card">
          {redLabel && <label className="row"><input type="checkbox" checked={gearOk} onChange={(e) => setGearOk(e.target.checked)} /> {r.safety.red_confirm}</label>}
          <button className="btn block" disabled={redLabel && !gearOk} onClick={save}>💾 {t(s.lang, "save")}</button>
        </div>
      )}
      {saved && (
        <div className={`card`}>
          <strong>✅ {t(s.lang, "saved")}</strong>
          <RuleList fired={saved.fired} />
          {saved.plot_safe_harvest_date && <p>{t(s.lang, "safeFrom")}: <strong>{saved.plot_safe_harvest_date}</strong></p>}
          {saved.rotation?.status === "change" && <div className="banner">{saved.rotation.text}</div>}
        </div>
      )}
      {r.scan_id && (
        <button className="btn secondary block" disabled={reported}
          onClick={async () => { await api.report({ scan_id: r.scan_id, reason: "Farmer report from app" }); setReported(true); }}>
          {reported ? t(s.lang, "reported") : `🚩 ${t(s.lang, "report")}`}
        </button>
      )}
    </Shell>
  );
}

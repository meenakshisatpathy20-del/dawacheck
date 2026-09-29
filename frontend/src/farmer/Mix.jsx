import { useState } from "react";
import { api } from "../api.js";
import { useStore } from "../store.jsx";
import { t } from "../strings.js";
import { speak, verdictTone } from "../voice.js";
import { ProductPicker, RuleList, Shell, VerdictBanner } from "./common.jsx";

function Tank({ items, remove }) {
  return (
    <svg viewBox="0 0 200 150" width="100%" style={{ maxHeight: 180 }} role="img" aria-label="tank">
      <rect x="40" y="20" width="120" height="120" rx="18" fill="var(--grey-bg)" stroke="var(--line)" strokeWidth="3" />
      {items.map((it, i) => {
        const bad = remove.some((r) => r.product_id === it.product_id);
        return (
          <g key={it.product_id}>
            <rect x="52" y={120 - (i + 1) * 26} width="96" height="22" rx="6"
              fill={bad ? "var(--red-bg)" : "var(--green-bg)"} stroke={bad ? "var(--red)" : "var(--green)"} />
            <text x="100" y={135 - (i + 1) * 26} textAnchor="middle" fontSize="10" fill="var(--ink)">
              {bad ? "✕ " : ""}{it.label.slice(0, 18)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export default function Mix() {
  const { lang } = useStore();
  const [picked, setPicked] = useState([]);
  const [res, setRes] = useState(null);
  const [err, setErr] = useState(null);

  const check = async () => {
    setErr(null);
    try {
      const r = await api.mix(picked.map((p) => p.id), lang);
      setRes(r);
      verdictTone(r.verdict);
      speak(r.speech, r.tts_locale);
    } catch (e) { setErr(e.message); }
  };

  return (
    <Shell title={t(lang, "mixCheck")}>
      {res ? (
        <>
          <VerdictBanner verdict={res.verdict} headline={`${res.risk_level.toUpperCase()} · ${res.items.length} 🧪`} />
          <Tank items={res.items} remove={res.remove} />
          <RuleList fired={res.fired} />
          {res.remove.length > 0 && <div className="card">🗑️ {t(lang, "remove")}: <strong>{res.remove.map((r) => r.label).join(", ")}</strong></div>}
          {res.gear && <div className="card">🧤 {res.gear}</div>}
          <p className="small muted">{res.limit_note}</p>
          <button className="btn secondary block" onClick={() => { setRes(null); setPicked([]); }}>↻</button>
        </>
      ) : (
        <>
          <div className="card">
            <ul className="list">
              {picked.map((p) => (
                <li key={p.id}><span className="spacer"><strong>{p.brand}</strong> <span className="muted small">{p.formulation}</span></span>
                  <button className="btn secondary" onClick={() => setPicked(picked.filter((x) => x.id !== p.id))}>✕</button></li>
              ))}
            </ul>
            <button className="btn block" disabled={picked.length < 2} onClick={check}>{t(lang, "check")} ({picked.length}/4)</button>
            {err && <div className="error">{err}</div>}
          </div>
          {picked.length < 4 && <ProductPicker exclude={picked.map((p) => p.id)} onPick={(p) => setPicked([...picked, p])} />}
        </>
      )}
    </Shell>
  );
}

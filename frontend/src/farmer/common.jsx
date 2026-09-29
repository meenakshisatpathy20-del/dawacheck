import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useStore } from "../store.jsx";
import { LANGS, t } from "../strings.js";

export function Shell({ children, title, back = true }) {
  const { lang, set } = useStore();
  const nav = useNavigate();
  return (
    <div className="phone">
      <div className="topbar">
        {back ? <button className="btn secondary" onClick={() => (window.history.length > 1 ? nav(-1) : nav("/"))} aria-label={t(lang, "back")}>←</button>
          : <Link to="/" className="brand"><img src="/app/icon.svg" alt="" />DawaCheck</Link>}
        {title && <strong style={{ fontSize: "1.1rem" }}>{title}</strong>}
        <select className="lang" value={lang} onChange={(e) => set({ lang: e.target.value })} aria-label="Language">
          {Object.entries(LANGS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      {children}
      <button className="sos-fab" onClick={() => nav("/sos")} aria-label="SOS">SOS</button>
    </div>
  );
}

const ICON = { green: "✅", yellow: "⚠️", red: "⛔", grey: "❔" };

export function VerdictBanner({ verdict, headline, sub }) {
  return (
    <div className={`verdict v-${verdict}`} role="status">
      <div className="ico" aria-hidden>{ICON[verdict] || "❔"}</div>
      <h1>{headline}</h1>
      {sub && <div>{sub}</div>}
    </div>
  );
}

export function RuleList({ fired, showSource }) {
  if (!fired?.length) return null;
  return (
    <div>
      {fired.map((r, i) => (
        <div key={i} className={`rule ${r.verdict}`}>
          <div><span className={`pill ${r.verdict}`}>{r.id}</span> {r.message}</div>
          {showSource && (
            <div className="src">
              {r.name}
              {r.source?.file && <> · source: {r.source.file}{r.source.page ? `, page ${r.source.page}` : ""}</>}
              {r.source?.url && <> · <a href={r.source.url} target="_blank" rel="noreferrer">{r.source.url}</a></>}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export function ProductPicker({ onPick, exclude = [] }) {
  const { lang } = useStore();
  const [products, setProducts] = useState([]);
  const [q, setQ] = useState("");
  const [err, setErr] = useState(null);
  useEffect(() => { api.products().then(setProducts).catch((e) => setErr(e.message)); }, []);
  const shown = products.filter((p) => !exclude.includes(p.id))
    .filter((p) => !q || `${p.brand} ${p.formulation}`.toLowerCase().includes(q.toLowerCase())).slice(0, 12);
  return (
    <div className="card">
      <h3>{t(lang, "orPick")}</h3>
      <div className="field"><input placeholder="🔍 Kavach, imidacloprid…" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      {err && <div className="error">{err}</div>}
      <ul className="list">
        {shown.map((p) => (
          <li key={p.id}>
            <span className={`tri`} style={{ color: `var(--${p.toxicity_colour === "blue" ? "blue" : p.toxicity_colour || "grey"})` }} />
            <div style={{ flex: 1 }}><strong>{p.brand}</strong><div className="small muted">{p.formulation}</div></div>
            <button className="btn secondary" onClick={() => onPick(p)}>✓</button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Loading({ text }) {
  const { lang } = useStore();
  return <div className="card" aria-busy="true">⏳ {text || t(lang, "checking")}</div>;
}

// Crop / pest picture: real photo from public/img when present, emoji otherwise.
export function Pic({ kind, name, emoji }) {
  const [ok, setOk] = useState(true);
  const src = `/app/img/${kind}/${encodeURIComponent(name.replace(/ /g, "-"))}.jpg`;
  return ok ? <img src={src} alt="" onError={() => setOk(false)} /> : <span className="ico">{emoji}</span>;
}

// Protective gear for a label colour, as icons (playbook screen 6).
const GEAR = {
  red: ["gloves", "mask", "goggles", "sleeves", "boots"], yellow: ["gloves", "mask", "sleeves", "boots"],
  blue: ["gloves", "mask", "sleeves"], green: ["gloves", "mask"],
};
const GEAR_ICON = { gloves: "🧤", mask: "😷", goggles: "🥽", sleeves: "👕", boots: "🥾" };
export function GearIcons({ colour }) {
  const { lang } = useStore();
  return (
    <div className="gear-row">
      {(GEAR[colour] || GEAR.green).map((g) => <span key={g}><b aria-hidden>{GEAR_ICON[g]}</b>{t(lang, g)}</span>)}
    </div>
  );
}

// Measuring cap drawing for the dose card, filled to the per-tank amount.
export function MeasuringCap({ amount, unit }) {
  const fill = Math.max(0.08, Math.min(1, (Number(amount) || 0) / 50)); // cap graduated to 50 ml / g
  const top = 30 + (1 - fill) * 90;
  return (
    <svg viewBox="0 0 120 150" width="96" height="120" role="img" aria-label={`${amount} ${unit}`}>
      <path d="M20 30 L100 30 L92 130 Q60 142 28 130 Z" fill="var(--grey-bg)" stroke="var(--ink)" strokeWidth="3" />
      <clipPath id="cap"><path d="M20 30 L100 30 L92 130 Q60 142 28 130 Z" /></clipPath>
      <rect x="0" y={top} width="120" height="150" fill="#6fb7e8" clipPath="url(#cap)" />
      {[10, 20, 30, 40].map((m) => (
        <g key={m}><line x1="24" x2="40" y1={120 - m * 1.8} y2={120 - m * 1.8} stroke="var(--ink)" strokeWidth="1.5" />
          <text x="44" y={124 - m * 1.8} fontSize="10" fill="var(--ink)">{m}</text></g>
      ))}
      <text x="60" y="22" textAnchor="middle" fontSize="16" fontWeight="700" fill="var(--ink)">{amount} {unit}</text>
    </svg>
  );
}

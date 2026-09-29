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
        {back ? <button className="btn secondary" onClick={() => nav(-1)} aria-label={t(lang, "back")}>←</button>
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

export function Loading() {
  const { lang } = useStore();
  return <div className="card" aria-busy="true">{t(lang, "checking")}</div>;
}

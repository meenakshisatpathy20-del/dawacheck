import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";

// Public read-only page behind the MRL Passport QR (for a trader or exporter).
export default function Passport() {
  const { plotId } = useParams();
  const [p, setP] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { api.passport(plotId, true).then(setP).catch((e) => setErr(e.message)); }, [plotId]);

  if (err) return <div className="phone"><div className="error">{err}</div></div>;
  if (!p) return <div className="phone"><div className="card">Loading…</div></div>;
  const risk = p.residue_risk === "high" ? "red" : p.residue_risk === "medium" ? "yellow" : "green";
  return (
    <div className="phone" style={{ maxWidth: 640 }}>
      <div className="topbar"><span className="brand"><img src="/app/icon.svg" alt="" />DawaCheck · MRL Passport</span></div>
      <div className={`verdict v-${risk}`}>
        <div className="ico">{p.safe_now ? "✅" : "⏳"}</div>
        <h1>Safe to harvest from {p.safe_harvest_date || "—"}</h1>
        <div>Plot {p.plot_id} · {p.crop}{p.state ? ` · ${p.state}` : ""} · residue risk <b>{p.residue_risk}</b></div>
      </div>
      <div className="card table-wrap">
        <h3>Spray record</h3>
        <table>
          <thead><tr><th>Date</th><th>Product</th><th>Active ingredient</th><th>Safe from</th><th>Flags</th></tr></thead>
          <tbody>{p.sprays.map((s, i) => (
            <tr key={i}><td>{s.date}</td><td>{s.product}<div className="small muted">{s.formulation}</div></td>
              <td>{s.active_ingredient}</td><td>{s.safe_harvest_date || "unknown"}</td>
              <td className="small">{s.flags.map((f, j) => <div key={j}>⚑ {f.text}</div>)}</td></tr>
          ))}</tbody>
        </table>
      </div>
      <p className="small muted">{p.note}</p>
    </div>
  );
}

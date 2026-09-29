import "leaflet/dist/leaflet.css";
import { useEffect, useState } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";
import { Link, NavLink, Route, Routes, useNavigate, useSearchParams } from "react-router-dom";
import { Bar, BarChart, Legend, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from "recharts";
import { api, fpoPlots } from "../api.js";

const SIGNAL = {
  date_conflict: "Same batch, different dates", cloned_qr: "QR seen far apart", not_in_registry: "Not in registry",
  farmer_report: "Farmer reports",
};

function useRadar(district) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    const load = () => api.radar(district).then(setD).catch((e) => setErr(e.message));
    load();
    const id = setInterval(load, 5000); // live: a new scan on stage shows up within seconds
    return () => clearInterval(id);
  }, [district]);
  return [d, err];
}

function MapView() {
  const [params, setParams] = useSearchParams();
  const district = params.get("district") || "";
  const [d, err] = useRadar(district);
  if (err) return <div className="error">{err}</div>;
  if (!d) return <div className="card">Loading…</div>;
  const chart = d.clusters.map((c) => ({ district: c.district, scans: c.scans, red: c.red, flagged: c.flagged }));
  return (
    <>
      <div className="kpis">
        <div className="kpi"><span className="muted">Scans (90 days)</span><b>{d.totals.scans}</b></div>
        <div className="kpi"><span className="muted">Red verdicts</span><b style={{ color: "var(--red)" }}>{d.totals.red}</b></div>
        <div className="kpi"><span className="muted">Yellow verdicts</span><b style={{ color: "var(--yellow)" }}>{d.totals.yellow}</b></div>
        <div className="kpi"><span className="muted">Suspicious batches</span><b>{d.totals.flagged_batches}</b></div>
      </div>
      <div className="dash-grid" style={{ marginTop: 16 }}>
        <div className="card" style={{ padding: 0 }}>
          <MapContainer center={[23.5, 78.5]} zoom={5} className="map" scrollWheelZoom>
            <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            {d.clusters.map((c) => (
              <CircleMarker key={c.district} center={[c.lat, c.lon]} radius={8 + Math.sqrt(c.scans) * 4}
                pathOptions={{ color: c.risk === "red" ? "#b3261e" : "#1f7a3a", fillOpacity: 0.45 }}
                eventHandlers={{ click: () => setParams({ district: c.district }) }}>
                <Tooltip>{c.district}: {c.scans} scans, {c.red} red, {c.flagged} on flagged batches</Tooltip>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
        <div className="card">
          <div className="row"><h3 className="spacer">By district</h3>
            {district && <button className="btn secondary" onClick={() => setParams({})}>All districts</button>}</div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chart}>
              <XAxis dataKey="district" fontSize={11} interval={0} angle={-30} textAnchor="end" height={60} />
              <YAxis allowDecimals={false} fontSize={11} />
              <RTooltip />
              <Legend />
              <Bar dataKey="scans" fill="#8aa596" />
              <Bar dataKey="red" fill="#b3261e" />
              <Bar dataKey="flagged" fill="#a86a00" />
            </BarChart>
          </ResponsiveContainer>
          <p className="small muted">{d.note}</p>
        </div>
      </div>
      <Batches rows={d.batches.slice(0, 8)} />
    </>
  );
}

function Batches({ rows }) {
  const nav = useNavigate();
  return (
    <div className="card table-wrap">
      <h3>Suspicious batches</h3>
      <table>
        <thead><tr><th>Product</th><th>Batch</th><th>Signal</th><th>Districts</th><th>Scans</th><th>Score</th><th>First seen</th></tr></thead>
        <tbody>
          {rows.map((b) => (
            <tr key={b.id} className="clickable"
              onClick={() => nav(`/officer/batch?batch=${encodeURIComponent(b.batch || "")}${b.product_id ? `&product_id=${b.product_id}` : ""}`)}>
              <td>{b.product}</td><td><code>{b.batch || "—"}</code></td>
              <td><span className={`pill ${b.score >= 1 ? "red" : "yellow"}`}>{SIGNAL[b.signal_type] || b.signal_type}</span></td>
              <td>{b.districts.join(", ")}</td><td>{b.count}</td><td>{b.score}</td><td>{b.first_seen.slice(0, 10)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BatchList() {
  const [d, err] = useRadar("");
  if (err) return <div className="error">{err}</div>;
  return d ? <Batches rows={d.batches} /> : <div className="card">Loading…</div>;
}

function BatchDetail() {
  const [params] = useSearchParams();
  const [d, setD] = useState(null);
  useEffect(() => { api.batch(params.get("batch"), params.get("product_id")).then(setD); }, [params]);
  if (!d) return <div className="card">Loading…</div>;
  return (
    <>
      <div className="card"><h2>{d.product} · batch <code>{d.batch}</code></h2>
        <p><b>Dates seen (mfg / exp):</b> {d.dates_seen.join(" · ") || "—"}</p>
        <p><b>Shops (shared by farmers):</b> {d.shops.join(" · ") || "—"}</p></div>
      <div className="card table-wrap"><h3>Timeline</h3>
        <table><thead><tr><th>When</th><th>District</th><th>Shop</th><th>Mfg</th><th>Exp</th><th>Verdict</th></tr></thead>
          <tbody>{d.timeline.map((x, i) => (
            <tr key={i}><td>{x.at.slice(0, 16).replace("T", " ")}</td><td>{x.district || "—"}</td><td>{x.shop || "—"}</td>
              <td>{x.mfg_date || "—"}</td><td>{x.exp_date || "—"}</td><td>{x.verdict ? <span className={`pill ${x.verdict}`}>{x.verdict}</span> : "—"}</td></tr>
          ))}</tbody></table></div>
      <div className="card"><h3>Farmer reports</h3>
        {d.reports.length === 0 ? <p className="muted">None</p> : <ul>{d.reports.map((r, i) => <li key={i}>{r.at.slice(0, 10)}: {r.reason} ({r.status})</li>)}</ul>}</div>
      <Link to="/officer/batches">← All batches</Link>
    </>
  );
}

function ExportView() {
  const [plots, setPlots] = useState(null);
  useEffect(() => { fpoPlots().then(setPlots); }, []);
  if (!plots) return <div className="card">Loading…</div>;
  return (
    <div className="card table-wrap">
      <h3>Member plots: spray records and residue flags</h3>
      {plots.length === 0 && <p className="muted">No sprays logged yet.</p>}
      <table>
        <thead><tr><th>Plot</th><th>Crop</th><th>Sprays</th><th>Flags</th><th>Residue risk</th><th>Earliest safe harvest</th><th /></tr></thead>
        <tbody>{plots.map((p) => (
          <tr key={p.plot_id}><td>{p.plot_id}</td><td>{p.crop}</td><td>{p.sprays.length}</td>
            <td className="small">{[...new Set(p.flags.map((f) => f.text))].join("; ") || "—"}</td>
            <td><span className={`pill ${p.residue_risk === "high" ? "red" : p.residue_risk === "medium" ? "yellow" : "green"}`}>{p.residue_risk}</span></td>
            <td>{p.safe_harvest_date || "—"}</td><td><Link to={`/passport/${encodeURIComponent(p.plot_id)}`}>Passport</Link></td></tr>
        ))}</tbody>
      </table>
      <p className="small muted">Self-declared records plus a risk estimate; not a lab certificate.</p>
    </div>
  );
}

export default function Officer() {
  return (
    <div className="dash">
      <div className="row">
        <Link to="/" className="brand"><img src="/app/icon.svg" alt="" />DawaCheck</Link>
        <span className="muted">Officer / FPO dashboard · Fake-Batch Radar</span>
      </div>
      <nav className="tabs">
        <NavLink end to="/officer">Map</NavLink>
        <NavLink to="/officer/batches">Suspicious batches</NavLink>
        <NavLink to="/officer/export">Export view (FPO)</NavLink>
      </nav>
      <Routes>
        <Route index element={<MapView />} />
        <Route path="batches" element={<BatchList />} />
        <Route path="batch" element={<BatchDetail />} />
        <Route path="export" element={<ExportView />} />
      </Routes>
    </div>
  );
}

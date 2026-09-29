import "leaflet/dist/leaflet.css";
import { useEffect, useState } from "react";
import L from "./leafletGlobal.js";
import "leaflet.heat";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";
import { Link, NavLink, Route, Routes, useNavigate, useSearchParams } from "react-router-dom";
import { Bar, BarChart, Legend, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from "recharts";
import { admin, api, fpoPlots } from "../api.js";

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

// District heat map (playbook officer screen 1): weight = red verdicts + scans on flagged batches.
function HeatLayer({ points }) {
  const map = useMap();
  useEffect(() => {
    const layer = L.heatLayer(points, { radius: 45, blur: 30, maxZoom: 8, max: 0.6, minOpacity: 0.35,
      gradient: { 0.2: "#1f7a3a", 0.5: "#a86a00", 0.8: "#b3261e" } });
    layer.addTo(map);
    return () => { map.removeLayer(layer); };
  }, [map, points]);
  return null;
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
            <HeatLayer points={d.clusters.map((c) => [c.lat, c.lon, Math.min(1, 0.15 + (c.red + c.flagged) / Math.max(4, c.scans))])} />
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
        {d.reports.length === 0 ? <p className="muted">None</p> : (
          <ul className="list">{d.reports.map((r, i) => (
            <li key={i}>{r.photo_url && <a href={r.photo_url} target="_blank" rel="noreferrer"><img src={r.photo_url} alt="report" style={{ width: 72, height: 72, objectFit: "cover", borderRadius: 8 }} /></a>}
              <span>{r.at.slice(0, 10)}: {r.reason} ({r.status})</span></li>
          ))}</ul>)}</div>
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

// Admin (playbook section 18): add a ban in minutes; review farmer-added products.
function Admin() {
  const [token, setToken] = useState(sessionStorage.getItem("dc.admin") || "");
  const [bans, setBans] = useState(null);
  const [subs, setSubs] = useState([]);
  const [err, setErr] = useState(null);
  const [msg, setMsg] = useState(null);
  const [nb, setNb] = useState({ state: "", crop: "", active_ingredient: "", effective_from: new Date().toISOString().slice(0, 10), source_url: "" });
  const [nat, setNat] = useState({ name: "", status: "banned", banned_from: "", ban_note: "", source_url: "" });

  const load = async () => {
    setErr(null);
    try { setBans(await admin.bans()); setSubs(await admin.submissions()); } catch (e) { setErr(e.message); setBans(null); }
  };
  useEffect(() => { if (token) load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const act = async (fn, ok) => { setErr(null); setMsg(null); try { await fn(); setMsg(ok); load(); } catch (e) { setErr(e.message); } };

  return (
    <>
      <div className="card row">
        <input className="lang" type="password" placeholder="Admin token" value={token} onChange={(e) => setToken(e.target.value)} />
        <button className="btn" onClick={() => { sessionStorage.setItem("dc.admin", token); load(); }}>Sign in</button>
        {msg && <span className="pill green">{msg}</span>}
      </div>
      {err && <div className="error">{err}</div>}
      {bans && (
        <div className="dash-grid">
          <div className="card">
            <h3>Add a state crop ban</h3>
            <p className="small muted">Takes effect on the effective date for every new scan and spray log. Cite the state order.</p>
            {["state", "crop", "active_ingredient", "source_url"].map((k) => (
              <div className="field" key={k}><label>{k.replace("_", " ")}</label>
                <input value={nb[k]} onChange={(e) => setNb({ ...nb, [k]: e.target.value })} /></div>
            ))}
            <div className="field"><label>effective from</label>
              <input type="date" value={nb.effective_from} onChange={(e) => setNb({ ...nb, effective_from: e.target.value })} /></div>
            <button className="btn" onClick={() => act(() => admin.addStateBan(nb), "Ban added")}>Add ban</button>
            <h3 style={{ marginTop: 20 }}>National ban / restriction</h3>
            <div className="field"><label>chemical</label><input value={nat.name} onChange={(e) => setNat({ ...nat, name: e.target.value })} /></div>
            <div className="field"><label>status</label>
              <select value={nat.status} onChange={(e) => setNat({ ...nat, status: e.target.value })}>
                <option value="banned">banned</option><option value="restricted">restricted</option><option value="none">not banned</option></select></div>
            <div className="field"><label>in force from</label><input type="date" value={nat.banned_from} onChange={(e) => setNat({ ...nat, banned_from: e.target.value })} /></div>
            <div className="field"><label>note</label><input value={nat.ban_note} onChange={(e) => setNat({ ...nat, ban_note: e.target.value })} /></div>
            <div className="field"><label>source url</label><input value={nat.source_url} onChange={(e) => setNat({ ...nat, source_url: e.target.value })} /></div>
            <button className="btn" onClick={() => act(() => admin.setNational(nat.name, {
              banned: nat.status === "banned", restricted: nat.status === "restricted", banned_from: nat.banned_from || null,
              ban_note: nat.ban_note || null, source_url: nat.source_url }), "Saved")}>Save</button>
          </div>
          <div className="card table-wrap">
            <h3>State crop bans</h3>
            <table><thead><tr><th>State</th><th>Crop</th><th>Chemical</th><th>From</th><th /></tr></thead>
              <tbody>{bans.state.map((b) => (
                <tr key={b.id}><td>{b.state}</td><td>{b.crop}</td><td>{b.active_ingredient}</td><td>{b.effective_from}</td>
                  <td><button className="btn secondary" onClick={() => act(() => admin.deleteStateBan(b.id), "Removed")}>✕</button></td></tr>
              ))}</tbody></table>
            <h3>National list</h3>
            <table><tbody>{bans.national.map((b) => (
              <tr key={b.name}><td>{b.name}</td><td><span className={`pill ${b.banned ? "red" : "yellow"}`}>{b.banned ? "banned" : "restricted"}</span></td>
                <td className="small">{b.banned_from || ""} {b.ban_note || ""}</td></tr>
            ))}</tbody></table>
          </div>
        </div>
      )}
      {bans && (
        <div className="card table-wrap">
          <h3>Farmer-added products awaiting review</h3>
          {subs.length === 0 && <p className="muted">None pending.</p>}
          <table><tbody>{subs.map((x) => (
            <tr key={x.id}>
              <td>{x.photo_url ? <a href={x.photo_url} target="_blank" rel="noreferrer"><img src={x.photo_url} alt="" style={{ width: 80, height: 80, objectFit: "cover", borderRadius: 8 }} /></a> : "no photo"}</td>
              <td><b>{x.brand}</b><div className="small">{x.active_ingredient} {x.strength_pct}% {x.formulation} · {x.reg_no || "no reg. no."}</div></td>
              <td><button className="btn" onClick={() => act(() => admin.approve(x.id, {}), "Approved")}>Approve</button>{" "}
                <button className="btn secondary" onClick={() => act(() => admin.reject(x.id, "rejected on review"), "Rejected")}>Reject</button></td>
            </tr>
          ))}</tbody></table>
        </div>
      )}
    </>
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
        <NavLink to="/officer/admin">Admin</NavLink>
      </nav>
      <Routes>
        <Route index element={<MapView />} />
        <Route path="batches" element={<BatchList />} />
        <Route path="batch" element={<BatchDetail />} />
        <Route path="export" element={<ExportView />} />
        <Route path="admin" element={<Admin />} />
      </Routes>
    </div>
  );
}

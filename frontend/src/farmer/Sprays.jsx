import QRCode from "qrcode";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useStore } from "../store.jsx";
import { t } from "../strings.js";
import { RuleList, Shell } from "./common.jsx";

export default function Sprays() {
  const s = useStore();
  const [p, setP] = useState(null);
  const [rot, setRot] = useState(null);
  const [qr, setQr] = useState(null);
  const [err, setErr] = useState(null);
  const url = `${window.location.origin}/app/passport/${encodeURIComponent(s.plot)}`;

  useEffect(() => {
    setErr(null);
    api.passport(s.plot).then(setP).catch((e) => { setP(null); setErr(e.message); });
    api.rotation(s.plot, s.lang).then(setRot).catch(() => {});
    QRCode.toDataURL(url, { margin: 1, width: 220 }).then(setQr);
  }, [s.plot, s.lang, url]);

  return (
    <Shell title={t(s.lang, "mySprays")}>
      <div className="field"><label>{t(s.lang, "plot")}</label>
        <input value={s.plot} onChange={(e) => s.set({ plot: e.target.value })} /></div>
      {err && <div className="card muted">{err}</div>}
      {p && (
        <>
          <div className={`card`}>
            <h3>📅 {t(s.lang, "safeFrom")}: {p.safe_harvest_date || "—"}</h3>
            <span className={`pill ${p.residue_risk === "high" ? "red" : p.residue_risk === "medium" ? "yellow" : "green"}`}>residue risk: {p.residue_risk}</span>
          </div>
          <div className="card">
            <ul className="list">{p.sprays.map((x, i) => (
              <li key={i}><span className="spacer"><strong>{x.date}</strong> · {x.product}<div className="small muted">{x.formulation} · safe {x.safe_harvest_date || "?"}</div>
                {x.flags.map((f, j) => <div key={j} className="small" style={{ color: "var(--red)" }}>⚑ {f.text}</div>)}</span></li>
            ))}</ul>
          </div>
          {rot?.status === "change" && (
            <div className="card">
              <RuleList fired={rot.fired} />
              <div className="small">💡 {rot.options.map((o) => `${o.formulation} (${o.moa_scheme} ${o.moa_group})`).join(", ")}</div>
            </div>
          )}
          <div className="card" style={{ textAlign: "center" }}>
            <h3>{t(s.lang, "passport")}</h3>
            {qr && <img src={qr} alt="MRL Passport QR" width="220" height="220" />}
            <div><Link to={`/passport/${encodeURIComponent(s.plot)}`}>{url}</Link></div>
            <p className="small muted">{p.note}</p>
          </div>
        </>
      )}
    </Shell>
  );
}

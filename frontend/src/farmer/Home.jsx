import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { reminders } from "../api.js";
import { useStore } from "../store.jsx";
import { CROP_ICON, CROP_NAME, pestName, t } from "../strings.js";
import { speak } from "../voice.js";
import { Shell } from "./common.jsx";

export default function Home() {
  const { lang, crop, pest, lastSafe } = useStore();
  const [due, setDue] = useState([]);
  const next = (to) => (crop ? to : `/crop?next=${encodeURIComponent(to)}`);

  // Harvest reminders saved with each spray: shown (and notified) once the date arrives.
  useEffect(() => {
    const d = reminders.due();
    setDue(d);
    for (const r of d) {
      const msg = `${t(lang, "harvestToday")}: ${CROP_NAME[lang][r.crop] || r.crop} (${r.plot})`;
      if ("Notification" in window && Notification.permission === "granted") {
        try { new Notification("DawaCheck", { body: msg, icon: "/app/icon.svg" }); } catch { /* ignore */ }
      }
      speak(msg);
    }
  }, [lang]);

  return (
    <Shell back={false}>
      {due.map((r) => (
        <div key={r.plot} className="banner row" style={{ background: "var(--green-bg)", color: "var(--green)" }}>
          <span className="spacer">🔔 {t(lang, "harvestToday")}: {CROP_NAME[lang][r.crop] || r.crop} · {r.plot}</span>
          <button className="btn secondary" onClick={() => { reminders.markShown(r.plot); setDue(due.filter((x) => x !== r)); }}>✓</button>
        </div>
      ))}
      <div className="big-grid">
        <Link className="big" to={next("/scan")}><span className="ico">📷</span>{t(lang, "scanPacket")}</Link>
        <Link className="big" to={next("/bill")}><span className="ico">🧾</span>{t(lang, "scanBill")}</Link>
        <Link className="big" to="/mix"><span className="ico">🧪</span>{t(lang, "mixCheck")}</Link>
        <Link className="big sos" to="/sos"><span className="ico">🆘</span>{t(lang, "sos")}</Link>
      </div>
      <Link to="/crop" className="card row" style={{ textDecoration: "none", color: "inherit" }}>
        <span style={{ fontSize: "2rem" }}>{CROP_ICON[crop] || "🌱"}</span>
        <div className="spacer">
          <strong>{crop ? (CROP_NAME[lang][crop] || crop) : t(lang, "pickCrop")}</strong>
          {pest && <div className="muted small">{pestName(lang, pest)}</div>}
        </div>
        <span>✎</span>
      </Link>
      <Link to="/sprays" className="card row" style={{ textDecoration: "none", color: "inherit" }}>
        <span style={{ fontSize: "2rem" }}>📅</span>
        <div className="spacer">
          <strong>{t(lang, "mySprays")}</strong>
          {lastSafe && <div className="muted small">{t(lang, "nextSafe")}: {lastSafe}</div>}
        </div>
        <span>›</span>
      </Link>
      <p className="small muted" style={{ textAlign: "center" }}>
        <Link to="/officer">Officer / FPO dashboard</Link>
      </p>
    </Shell>
  );
}

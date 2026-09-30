import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, reminders } from "../api.js";
import { useStore } from "../store.jsx";
import { CROP_ICON, CROP_NAME, pestName, t } from "../strings.js";
import { speak } from "../voice.js";
import { Loading, Shell } from "./common.jsx";
import { useScan } from "./ScanPacket.jsx";

const DEMO = [
  { key: "demoGreen", colour: "green", brand: "Emacure", crop: "cotton", pest: "bollworm", state: "maharashtra",
    scan: { qr_payload: "DC-QR-1012|EM25-777|0001", confirmed: true } },
  { key: "demoWrongCrop", colour: "yellow", brand: "Blastguard 75", crop: "cotton", pest: "jassid", state: "maharashtra",
    scan: { fields: JSON.stringify({ brand: "Blastguard 75" }), confirmed: true } },
  { key: "demoStateBan", colour: "red", brand: "Tricy Plus", crop: "basmati", pest: "blast", state: "punjab",
    scan: { fields: JSON.stringify({ brand: "Tricy Plus" }), confirmed: true } },
  { key: "demoBatch", colour: "red", brand: "Profex 50", crop: "cotton", pest: "bollworm", state: "maharashtra",
    scan: { qr_payload: "DC-QR-1007|PF24-117|0001", confirmed: true } },
];

export default function Home() {
  const { lang, crop, pest, lastSafe, set } = useStore();
  const [due, setDue] = useState([]);
  const scan = useScan();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [m, setM] = useState(null);
  useEffect(() => { api.metrics().then(setM).catch(() => {}); }, []);
  // One tap per verdict, for anyone trying the app without a pesticide pack in hand (sample data).
  const tryCase = async (c) => {
    set({ crop: c.crop, pest: c.pest, state: c.state });
    setBusy(true); setErr(null);
    try { await scan({ ...c.scan, crop: c.crop, pest: c.pest, state: c.state }); }
    catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  const next = (to) => (crop ? to : `/crop?next=${encodeURIComponent(to)}`);

  // Harvest reminders saved with each spray: shown (and notified) once the date arrives.
  useEffect(() => {
    const d = reminders.due();
    setDue(d);
    for (const r of d) {
      const msg = `${t(lang, "harvestToday")}: ${CROP_NAME[lang][r.crop] || r.crop} (${r.plot})`;
      if ("Notification" in window && Notification.permission === "granted") {
        try { new Notification("DawaCheck", { body: msg, icon: `${import.meta.env.BASE_URL}icon.svg` }); } catch { /* ignore */ }
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
      <div className="card demo">
        <strong>▶ {t(lang, "tryDemo")}</strong>
        <div className="muted small">{t(lang, "tryDemoHint")}</div>
        <div className="demo-grid">
          {DEMO.map((c) => (
            <button key={c.key} className={`demo-case ${c.colour}`} disabled={busy} onClick={() => tryCase(c)}>
              <b>{c.brand}</b><span>{t(lang, c.key)}</span>
            </button>
          ))}
        </div>
        {busy && <Loading text={t(lang, "checking")} />}
        {err && <div className="error">{err}</div>}
      </div>
      {m && m.scans > 0 && (
        <div className="impact small">
          <b>{m.scans}</b> {t(lang, "impScans")} · <b>{Math.round((m.red_share + m.yellow_share) * 100)}%</b> {t(lang, "impFlagged")}
          {m.money_saved_rs > 0 && <> · <b>₹{m.money_saved_rs.toLocaleString("en-IN")}</b> {t(lang, "impSaved")}</>}
          <div className="muted">{t(lang, "impNote")}</div>
        </div>
      )}
      <p className="small muted" style={{ textAlign: "center" }}>
        <Link to="/officer">Officer / FPO dashboard</Link>
      </p>
    </Shell>
  );
}

import { Link } from "react-router-dom";
import { useStore } from "../store.jsx";
import { CROP_ICON, CROP_NAME, t } from "../strings.js";
import { Shell } from "./common.jsx";

export default function Home() {
  const { lang, crop, pest, lastSafe } = useStore();
  const next = (to) => (crop ? to : `/crop?next=${encodeURIComponent(to)}`);
  return (
    <Shell back={false}>
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
          {pest && <div className="muted small">{pest}</div>}
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

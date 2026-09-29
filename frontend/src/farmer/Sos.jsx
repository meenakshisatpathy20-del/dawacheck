import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useStore } from "../store.jsx";
import { t } from "../strings.js";
import { speak } from "../voice.js";
import { Shell } from "./common.jsx";

const COLOUR_WORD = { red: "RED", yellow: "YELLOW", blue: "BLUE", green: "GREEN" };

export default function Sos() {
  const s = useStore();
  const [d, setD] = useState(null);
  const [card, setCard] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api.sos({ user_id: s.userId, lat: s.gps?.lat, lon: s.gps?.lon, lang: s.lang })
      .then((r) => { setD(r); speak(r.say.join(" "), r.tts_locale); })
      .catch((e) => setErr(e.message));
  }, [s.userId, s.gps, s.lang]);

  // Works even with no network: the helpline numbers are static.
  const npic = d?.helplines?.[0] || { phone: "1800 116 117", tel: "18001161117" };

  if (card && d) {
    return (
      <div className="doctor" onClick={() => setCard(false)}>
        <h1>🩺 DOCTOR CARD</h1>
        <p><b>Pesticide exposure (farm spraying).</b> Details below are copied from the product label.</p>
        {d.doctor_card.length === 0 && <p>No product recorded. Ask the patient for the container.</p>}
        {d.doctor_card.map((c, i) => (
          <div key={i} className="kv">
            <b>Product</b><span>{c.product}</span>
            <b>Active ingredient</b><span>{c.strength}</span>
            <b>Chemical class</b><span>{c.chem_class || "—"} {c.moa_group ? `(group ${c.moa_group})` : ""}</span>
            <b>Label colour</b><span><span className="tri" style={{ color: c.label_colour === "blue" ? "#1e5aa8" : c.label_colour }} /> {COLOUR_WORD[c.label_colour] || "—"}</span>
            <b>Antidote / treatment on label</b><span>{c.antidote_from_label || "See label"}</span>
            <b>Last spray</b><span>{c.last_spray || "—"}</span>
          </div>
        ))}
        <p><b>Poisons Information Centre (AIIMS):</b> {npic.phone}</p>
        <p style={{ fontSize: "1rem" }}>{d.disclaimer}</p>
      </div>
    );
  }

  return (
    <Shell title="SOS">
      <a className="btn danger block" style={{ display: "block", textAlign: "center", textDecoration: "none", fontSize: "1.3rem", marginBottom: 12 }}
        href={`tel:${npic.tel}`}>📞 {t(s.lang, "callNpic")}<br />{npic.phone}</a>
      <a className="btn secondary block" style={{ display: "block", textAlign: "center", textDecoration: "none" }} href="tel:108">🚑 {t(s.lang, "call108")}</a>
      <button className="btn block" style={{ marginTop: 12 }} onClick={() => setCard(true)} disabled={!d}>🩺 {t(s.lang, "showCard")}</button>
      {err && <div className="error" style={{ marginTop: 12 }}>{err}</div>}
      {d?.first_aid && <div className="card"><h3>{t(s.lang, "firstAid")}</h3><p>{d.first_aid}</p></div>}
      {d?.health_centres?.length > 0 && (
        <div className="card">
          <h3>🏥</h3>
          <ul className="list">{d.health_centres.map((h, i) => (
            <li key={i}><span className="spacer">{h.name} <span className="muted small">{h.km} km</span></span>
              <a href={`https://www.openstreetmap.org/?mlat=${h.lat}&mlon=${h.lon}#map=16/${h.lat}/${h.lon}`} target="_blank" rel="noreferrer">🗺️</a></li>
          ))}</ul>
        </div>
      )}
      {d && <p className="small muted">{d.disclaimer}</p>}
    </Shell>
  );
}

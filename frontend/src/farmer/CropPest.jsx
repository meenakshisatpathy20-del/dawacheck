import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import { useStore } from "../store.jsx";
import { CROP_ICON, CROP_NAME, PEST_ICON, TTS, pestName, t } from "../strings.js";
import { listen } from "../voice.js";
import { Pic, Shell } from "./common.jsx";

const STATES = ["", "andhra pradesh", "gujarat", "haryana", "karnataka", "madhya pradesh", "maharashtra", "punjab",
  "rajasthan", "tamil nadu", "telangana", "uttar pradesh", "west bengal"];

// "kapas sundi" -> crop + pest, using a few spoken words; the backend normalises the rest.
const SPOKEN = { kapas: "cotton", kapus: "cotton", narma: "cotton", dhan: "rice", paddy: "rice", jhona: "rice",
  basmati: "basmati", tamatar: "tomato", tomato: "tomato", cotton: "cotton", rice: "rice",
  patti: "cotton", pathi: "cotton", vari: "rice", tamata: "tomato",
  sundi: "bollworm", "kaya tolucha": "bollworm", "pacha doma": "jassid", "tella doma": "whitefly", aggi: "blast", "hara tela": "jassid", tela: "brown plant hopper", mahu: "aphid", "safed makhi": "whitefly",
  jhulsa: "blast", "fal chhedak": "fruit borer" };

export default function CropPest() {
  const s = useStore();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [crops, setCrops] = useState({});
  const [crop, setCrop] = useState(s.crop);
  useEffect(() => { api.crops().then(setCrops).catch(() => {}); }, []);

  const finish = (pest) => {
    s.set({ crop, pest });
    nav(params.get("next") || "/");
  };
  const voice = () => listen(TTS[s.lang], (text) => {
    const low = text.toLowerCase();
    const hits = Object.entries(SPOKEN).filter(([w]) => low.includes(w)).map(([, v]) => v);
    const c = hits.find((h) => crops[h]);
    const p = hits.find((h) => !crops[h]);
    if (c) setCrop(c);
    if (c && p) { s.set({ crop: c, pest: p }); nav(params.get("next") || "/"); }
  });

  return (
    <Shell title={crop ? t(s.lang, "pickPest") : t(s.lang, "pickCrop")}>
      <div className="row" style={{ marginBottom: 8 }}>
        <button className="btn secondary" onClick={voice}>🎤 {t(s.lang, "speak")}</button>
        <div className="spacer" />
        <label className="small muted">{t(s.lang, "state")}&nbsp;
          <select className="lang" value={s.state} onChange={(e) => s.set({ state: e.target.value })}>
            {STATES.map((x) => <option key={x} value={x}>{x || "—"}</option>)}
          </select>
        </label>
      </div>
      <div className="pick-grid">
        {Object.keys(crops).map((c) => (
          <button key={c} className={`pick ${crop === c ? "on" : ""}`} onClick={() => setCrop(c)}>
            <Pic kind="crops" name={c} emoji={CROP_ICON[c] || "🌱"} />{CROP_NAME[s.lang][c] || c}
          </button>
        ))}
      </div>
      {crop && crops[crop] && (
        <>
          <h3>{t(s.lang, "pickPest")}</h3>
          <div className="pick-grid">
            {crops[crop].map((p) => (
              <button key={p} className={`pick ${s.pest === p && s.crop === crop ? "on" : ""}`} onClick={() => finish(p)}>
                <Pic kind="pests" name={p} emoji={PEST_ICON[p] || "🐞"} />{pestName(s.lang, p)}
              </button>
            ))}
            <button className="pick" onClick={() => finish(null)}><span className="ico">❓</span>{t(s.lang, "anyPest")}</button>
          </div>
        </>
      )}
    </Shell>
  );
}

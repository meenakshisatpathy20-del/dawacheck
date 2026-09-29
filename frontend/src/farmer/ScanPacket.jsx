import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useStore } from "../store.jsx";
import { t } from "../strings.js";
import { Loading, ProductPicker, Shell } from "./common.jsx";

// Decode a QR on the phone when the browser supports it (Chrome on Android does);
// otherwise the photo goes to the server, which tries QR then OCR.
async function decodeOnDevice(file) {
  if (!("BarcodeDetector" in window)) return null;
  try {
    const det = new window.BarcodeDetector({ formats: ["qr_code"] });
    const codes = await det.detect(await createImageBitmap(file));
    return codes[0]?.rawValue || null;
  } catch { return null; }
}

export function useScan() {
  const s = useStore();
  const nav = useNavigate();
  return async (extra) => {
    const r = await api.scan({
      crop: s.crop, pest: s.pest, state: s.state, lang: s.lang, area_acre: s.area, tank_l: s.pump,
      user_id: s.userId, district: s.district, lat: s.gps?.lat, lon: s.gps?.lon, ...extra,
    });
    sessionStorage.setItem("dc.last", JSON.stringify(r));
    nav("/result", { state: r });
    return r;
  };
}

export default function ScanPacket() {
  const { lang } = useStore();
  const scan = useScan();
  const fileRef = useRef();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [code, setCode] = useState("");

  const run = async (extra) => {
    setBusy(true); setErr(null);
    try {
      const r = await scan(extra);
      if (r.status === "need_input") setErr(t(lang, "noOcr"));
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const qr = await decodeOnDevice(file);
    run(qr ? { qr_payload: qr, image: file } : { image: file });
  };

  return (
    <Shell title={t(lang, "scanPacket")}>
      <input ref={fileRef} type="file" accept="image/*" capture="environment" hidden onChange={onFile} />
      <button className="big" style={{ width: "100%" }} disabled={busy} onClick={() => fileRef.current.click()}>
        <span className="ico">📷</span>{t(lang, "takePhoto")}
      </button>
      {busy && <Loading />}
      {err && <div className="error" style={{ marginTop: 12 }}>{err}</div>}
      <div className="card">
        <div className="field">
          <label>{t(lang, "typeQr")}</label>
          <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="DC-QR-1001 / CIR-…" />
        </div>
        <button className="btn block" disabled={!code || busy}
          onClick={() => run(code.toUpperCase().startsWith("CIR") ? { fields: { reg_no: code } } : { qr_payload: code })}>
          {t(lang, "check")}
        </button>
      </div>
      <ProductPicker onPick={(p) => run({ product_id: p.id })} />
    </Shell>
  );
}

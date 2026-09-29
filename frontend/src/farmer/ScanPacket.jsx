import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useStore } from "../store.jsx";
import { t } from "../strings.js";
import Camera from "./Camera.jsx";
import { Loading, ProductPicker, Shell } from "./common.jsx";

export function useScan() {
  const s = useStore();
  const nav = useNavigate();
  return async (extra, { photo = false, onQueued } = {}) => {
    const params = {
      crop: s.crop, pest: s.pest, state: s.state, lang: s.lang, area_acre: s.area, tank_l: s.pump,
      user_id: s.userId, district: s.district, shop: s.shop, lat: s.gps?.lat, lon: s.gps?.lon, ...extra,
    };
    const r = photo ? await api.scanPhoto(params, onQueued) : await api.scan(params);
    if (r.status === "ok") {
      if (extra.image) r.local_photo = URL.createObjectURL(extra.image);
      if (extra.read_from_pack || extra.confirmed) r.confirmed = true;
      if (extra.start_step) r.start_step = extra.start_step;
      sessionStorage.setItem("dc.last", JSON.stringify({ ...r, local_photo: undefined }));
      nav("/result", { state: r });
    }
    return r;
  };
}

export default function ScanPacket() {
  const s = useStore();
  const scan = useScan();
  const [busy, setBusy] = useState(null);
  const [err, setErr] = useState(null);
  const [code, setCode] = useState("");

  const run = async (extra, opts) => {
    setBusy(t(s.lang, "checking")); setErr(null);
    try {
      const r = await scan(extra, { ...opts, onQueued: () => setBusy(t(s.lang, "queued")) });
      if (r.status === "need_input") setErr(t(s.lang, "noOcr"));
    } catch (e) { setErr(e.message); } finally { setBusy(null); }
  };

  return (
    <Shell title={t(s.lang, "scanPacket")}>
      <Camera busy={!!busy}
        onQr={(qr, frame) => run({ qr_payload: qr, image: frame || undefined })}
        onPhoto={(blob) => run({ image: blob }, { photo: true })} />
      {busy && <Loading text={busy} />}
      {err && <div className="error" style={{ marginTop: 12 }}>{err}</div>}
      <div className="field">
        <label>{t(s.lang, "shop")}</label>
        <input value={s.shop} onChange={(e) => s.set({ shop: e.target.value })} placeholder="Krishi Seva Kendra, Yavatmal" />
      </div>
      <div className="card">
        <div className="field">
          <label>{t(s.lang, "typeQr")}</label>
          <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="DC-QR-1001 / CIR-…" />
        </div>
        <button className="btn block" disabled={!code || !!busy}
          onClick={() => run(code.toUpperCase().startsWith("CIR") ? { fields: { reg_no: code } } : { qr_payload: code })}>
          {t(s.lang, "check")}
        </button>
      </div>
      <ProductPicker onPick={(p) => run({ product_id: p.id })} />
    </Shell>
  );
}

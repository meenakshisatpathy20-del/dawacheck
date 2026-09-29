import { useRef, useState } from "react";
import { api } from "../api.js";
import { useStore } from "../store.jsx";
import { t } from "../strings.js";
import { speak, verdictTone } from "../voice.js";
import { Loading, RuleList, Shell, VerdictBanner } from "./common.jsx";

const EMPTY = { product_name: "", pack_size: "", quantity: 1, price: "" };

export default function Bill() {
  const s = useStore();
  const fileRef = useRef();
  const [items, setItems] = useState([{ ...EMPTY }]);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const run = async (extra) => {
    setBusy(true); setErr(null);
    try {
      const r = await api.bill({ crop: s.crop, pest: s.pest, state: s.state, lang: s.lang, district: s.district,
        user_id: s.userId, ...extra });
      if (r.status === "need_input") { setErr(t(s.lang, "noOcr")); return; }
      setRes(r);
      verdictTone(r.verdict);
      speak(r.summary, r.tts_locale);
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  if (res) {
    return (
      <Shell title={t(s.lang, "scanBill")}>
        <VerdictBanner verdict={res.verdict} headline={res.summary} />
        {res.items.map((it, i) => (
          <div className="card" key={i}>
            <div className="row">
              <span className={`pill ${it.verdict}`}>{it.verdict}</span>
              <strong className="spacer">{it.product?.brand || it.input.product_name}</strong>
              <span>₹{it.input.price ?? "—"}</span>
            </div>
            {it.product && <div className="small muted">{it.product.formulation}</div>}
            <RuleList fired={it.fired} />
            {it.cheaper && <div className="banner">💰 {it.cheaper.text} ({it.cheaper.brand} {it.cheaper.pack_size}, {it.cheaper.seen})</div>}
            {it.suggestions?.length > 0 && <div className="small">💡 {it.suggestions.map((o) => o.formulation).join(", ")}</div>}
          </div>
        ))}
        <p className="small muted">{res.price_note}</p>
        <button className="btn secondary block" onClick={() => setRes(null)}>↻</button>
      </Shell>
    );
  }

  const upd = (i, k, v) => setItems(items.map((x, j) => (j === i ? { ...x, [k]: v } : x)));
  return (
    <Shell title={t(s.lang, "scanBill")}>
      <input ref={fileRef} type="file" accept="image/*" capture="environment" hidden
        onChange={(e) => e.target.files?.[0] && run({ image: e.target.files[0] })} />
      <button className="big" style={{ width: "100%" }} disabled={busy} onClick={() => fileRef.current.click()}>
        <span className="ico">🧾</span>{t(s.lang, "takePhoto")}
      </button>
      {busy && <Loading />}
      {err && <div className="error">{err}</div>}
      <div className="card">
        {items.map((it, i) => (
          <div key={i} className="row" style={{ marginBottom: 8 }}>
            <input style={{ flex: 2, minWidth: 120 }} className="lang" placeholder="Kavach Imida" value={it.product_name} onChange={(e) => upd(i, "product_name", e.target.value)} />
            <input style={{ width: 80 }} className="lang" placeholder="250 ml" value={it.pack_size} onChange={(e) => upd(i, "pack_size", e.target.value)} />
            <input style={{ width: 50 }} className="lang" type="number" min="1" value={it.quantity} onChange={(e) => upd(i, "quantity", Number(e.target.value))} />
            <input style={{ width: 80 }} className="lang" type="number" placeholder="₹" value={it.price} onChange={(e) => upd(i, "price", e.target.value)} />
          </div>
        ))}
        <div className="row">
          <button className="btn secondary" onClick={() => setItems([...items, { ...EMPTY }])}>+ {t(s.lang, "addProduct")}</button>
          <div className="spacer" />
          <button className="btn" disabled={busy || !items.some((x) => x.product_name)}
            onClick={() => run({ items: items.filter((x) => x.product_name).map((x) => ({ ...x, price: x.price === "" ? null : Number(x.price) })) })}>
            {t(s.lang, "check")}
          </button>
        </div>
      </div>
    </Shell>
  );
}

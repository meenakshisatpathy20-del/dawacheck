import { createContext, useContext, useEffect, useMemo, useState } from "react";

const Ctx = createContext(null);

function load(key, fallback) {
  try {
    const v = localStorage.getItem(key);
    return v == null ? fallback : JSON.parse(v);
  } catch { return fallback; }
}

function deviceId() {
  let id = load("dc.device", null);
  if (!id) {
    id = (crypto.randomUUID && crypto.randomUUID()) || String(Math.random()).slice(2);
    try { localStorage.setItem("dc.device", JSON.stringify(id)); } catch { /* ignore */ }
  }
  return id; // hashed with a salt on the server; never a phone number
}

export function StoreProvider({ children }) {
  const [s, setS] = useState(() => ({
    lang: load("dc.lang", (navigator.language || "en").slice(0, 2) in { hi: 1, mr: 1, pa: 1 } ? navigator.language.slice(0, 2) : "en"),
    crop: load("dc.crop", null), pest: load("dc.pest", null), state: load("dc.state", ""),
    area: load("dc.area", 1), pump: load("dc.pump", 15), plot: load("dc.plot", "my-plot-1"),
    district: load("dc.district", ""), lastSafe: load("dc.lastSafe", null), gps: null,
  }));
  const userId = useMemo(deviceId, []);

  useEffect(() => {
    for (const k of ["lang", "crop", "pest", "state", "area", "pump", "plot", "district", "lastSafe"]) {
      try { localStorage.setItem(`dc.${k}`, JSON.stringify(s[k])); } catch { /* ignore */ }
    }
  }, [s]);

  useEffect(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (p) => setS((o) => ({ ...o, gps: { lat: p.coords.latitude, lon: p.coords.longitude } })),
      () => {}, { maximumAge: 600000, timeout: 5000 });
  }, []);

  const set = (patch) => setS((o) => ({ ...o, ...patch }));
  return <Ctx.Provider value={{ ...s, set, userId }}>{children}</Ctx.Provider>;
}

export const useStore = () => useContext(Ctx);

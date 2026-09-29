// API client with an offline cache of verdicts for products already scanned
// (playbook: "works offline for scans already cached").
const BASE = import.meta.env.VITE_API_URL || "";
const CACHE_KEY = "dc.cache.v1";

function readCache() {
  try { return JSON.parse(localStorage.getItem(CACHE_KEY) || "{}"); } catch { return {}; }
}
function writeCache(c) {
  try { localStorage.setItem(CACHE_KEY, JSON.stringify(c)); } catch { /* storage full or blocked */ }
}

async function request(path, opts = {}) {
  const res = await fetch(BASE + path, opts);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
  return body;
}

const form = (obj) => {
  const f = new FormData();
  for (const [k, v] of Object.entries(obj)) {
    if (v === undefined || v === null || v === "") continue;
    f.append(k, v instanceof Blob ? v : typeof v === "object" ? JSON.stringify(v) : String(v));
  }
  return f;
};

const scanKey = (p) => ["scan", p.product_id, p.crop, p.pest, p.state, p.area_acre, p.lang].join("|");

export const api = {
  async scan(params) {
    try {
      const r = await request("/scan", { method: "POST", body: form(params) });
      if (r.status === "ok" && r.product) {
        const c = readCache();
        c[scanKey({ ...params, product_id: r.product.id })] = { ...r, cached_at: new Date().toISOString() };
        writeCache(c);
      }
      return r;
    } catch (e) {
      if (params.product_id) {
        const hit = readCache()[scanKey(params)];
        if (hit) return { ...hit, offline: true };
      }
      throw e;
    }
  },
  bill: (params) => request("/bill", { method: "POST", body: form(params) }),
  mix: (product_ids, lang) => request("/mix-check", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ product_ids, lang }),
  }),
  sprayLog: (body) => request("/spray-log", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  }),
  passport: (plot) => request(`/passport/${encodeURIComponent(plot)}`),
  rotation: (plot, lang) => request(`/rotation?plot_id=${encodeURIComponent(plot)}&lang=${lang}`),
  sos: (q) => request(`/sos?${new URLSearchParams(Object.entries(q).filter(([, v]) => v != null && v !== ""))}`),
  weather: (q) => request(`/weather-window?${new URLSearchParams(Object.entries(q).filter(([, v]) => v != null && v !== ""))}`),
  report: (params) => request("/report", { method: "POST", body: form(params) }),
  radar: (district) => request(`/radar${district ? `?district=${encodeURIComponent(district)}` : ""}`),
  batch: (batch, product_id) => request(`/radar/batch?batch=${encodeURIComponent(batch)}${product_id ? `&product_id=${product_id}` : ""}`),
  explain: (fired, lang) => request("/explain", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ fired, lang }),
  }),
  async products() {
    try {
      const p = await request("/products");
      try { localStorage.setItem("dc.products", JSON.stringify(p)); } catch { /* ignore */ }
      return p;
    } catch (e) {
      const cached = localStorage.getItem("dc.products");
      if (cached) return JSON.parse(cached);
      throw e;
    }
  },
  async crops() {
    try {
      const c = await request("/crops");
      try { localStorage.setItem("dc.crops", JSON.stringify(c)); } catch { /* ignore */ }
      return c;
    } catch (e) {
      const cached = localStorage.getItem("dc.crops");
      if (cached) return JSON.parse(cached);
      throw e;
    }
  },
};

export const fpoPlots = () => fetch((import.meta.env.VITE_API_URL || "") + "/fpo/plots").then((r) => r.json());

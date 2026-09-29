import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Two builds from one codebase:
//  * Vercel services (VERCEL=1 during the build): frontend service at "/", backend service at "/api".
//    Hash URLs (/#/officer) so reloading any screen never needs a server-side fallback.
//  * Docker / local: the backend serves this app under /app/ and the API at the site root.
const onVercel = !!process.env.VERCEL;
const apiBase = process.env.VITE_API_URL ?? (onVercel ? "/api" : "");
const hashRouter = process.env.VITE_HASH_ROUTER ? process.env.VITE_HASH_ROUTER === "1" : onVercel;

const API = process.env.API_URL || "http://localhost:8000";
const apiPaths = ["/scan", "/bill", "/mix-check", "/claims", "/dose", "/spray-log", "/passport", "/rotation",
  "/sos", "/weather-window", "/report", "/radar", "/health", "/products", "/crops", "/offline-pack", "/i18n",
  "/explain", "/uploads", "/fpo", "/jobs", "/reminder.ics", "/metrics", "/admin", "/api"];

export default defineConfig({
  base: process.env.VITE_BASE || (onVercel ? "/" : "/app/"),
  plugins: [react()],
  define: {
    __API_BASE__: JSON.stringify(apiBase.replace(/\/$/, "")),
    __HASH_ROUTER__: JSON.stringify(hashRouter),
  },
  server: {
    host: true,
    proxy: Object.fromEntries(apiPaths.map((p) => [p, { target: API, changeOrigin: true }])),
  },
});

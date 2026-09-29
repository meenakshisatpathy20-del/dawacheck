import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API = process.env.API_URL || "http://localhost:8000";
const apiPaths = ["/scan", "/bill", "/mix-check", "/claims", "/dose", "/spray-log", "/passport", "/rotation",
  "/sos", "/weather-window", "/report", "/radar", "/health", "/products", "/crops", "/offline-pack", "/i18n",
  "/explain", "/uploads", "/fpo"];

export default defineConfig({
  base: "/app/",
  plugins: [react()],
  server: {
    host: true,
    proxy: Object.fromEntries(apiPaths.map((p) => [p, { target: API, changeOrigin: true }])),
  },
});

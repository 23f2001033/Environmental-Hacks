import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Local development talks to the deployed API through the CloudFront domain (same-origin /api in production).
const API = process.env.JALSAATHI_API || "https://d2735023v3xj6.cloudfront.net";

// Served at /app/ next to the village site at / (frontend/). Role screens: engineer, relay, officials, impact.
export default defineConfig({
  base: "/app/",
  plugins: [react()],
  server: { proxy: { "/api": { target: API, changeOrigin: true }, "/media": { target: API, changeOrigin: true } } },
  preview: { proxy: { "/api": { target: API, changeOrigin: true }, "/media": { target: API, changeOrigin: true } } },
  build: { outDir: "dist", emptyOutDir: true, chunkSizeWarningLimit: 1200 },
});

import { defineConfig } from "vite";

export default defineConfig({
  // MapLibre resolves its worker relative to its module. Prebundling moves the
  // module into .vite/deps without its sibling worker, breaking maps in dev.
  optimizeDeps: { exclude: ["maplibre-gl"] },
  server: {
    proxy: process.env.JALSAATHI_API_ORIGIN
      ? {
          "/api": {
            target: process.env.JALSAATHI_API_ORIGIN,
            changeOrigin: true,
          },
          "/media": {
            target: process.env.JALSAATHI_API_ORIGIN,
            changeOrigin: true,
          },
        }
      : undefined,
  },
  build: { outDir: "dist", emptyOutDir: true },
});

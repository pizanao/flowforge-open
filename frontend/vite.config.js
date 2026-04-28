import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: process.env.VITE_BASE_PATH || "/",
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5106,
    proxy: {
      "/api": { target: "http://localhost:8006", changeOrigin: true },
      "/ws": { target: "ws://localhost:8006", ws: true, changeOrigin: true },
    },
  },
});

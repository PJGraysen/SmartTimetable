import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxy: the browser talks to the Vite dev server on its own
// origin, and Vite forwards /api/* to Django. This removes the cross-
// origin problem entirely and lets session cookies work as same-origin.
export default defineConfig({
    chunkSizeWarningLimit: 2000,
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
});

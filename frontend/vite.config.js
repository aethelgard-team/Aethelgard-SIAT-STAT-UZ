import { defineConfig } from 'vite';

// /api va /health so'rovlarini FastAPI backendga (8000-port) yo'naltiramiz.
// Backend boshqa portda bo'lsa, shu yerda o'zgartiring.
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
});

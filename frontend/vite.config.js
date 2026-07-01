import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const API_PORT = 20150;
const FRONTEND_PORT = 20156;

const apiProxy = {
  '/api': {
    target: `http://127.0.0.1:${API_PORT}`,
    changeOrigin: true,
  },
};

export default defineConfig({
  plugins: [react()],
  server: {
    port: FRONTEND_PORT,
    strictPort: true,
    proxy: apiProxy,
  },
  preview: {
    host: '0.0.0.0',
    port: FRONTEND_PORT,
    strictPort: true,
    proxy: apiProxy,
  },
});

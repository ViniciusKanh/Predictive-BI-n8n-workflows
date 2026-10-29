import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: { target: 'esnext', emptyOutDir: false, chunkSizeWarningLimit: 1000 },
  server: { host: '127.0.0.1', port: 5180, strictPort: true,
    proxy: { '/api': { target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:8101' }, '/workflow-api': { target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:8101' }, '/health': process.env.API_PROXY_TARGET || 'http://127.0.0.1:8101' } },
  preview: { host: '127.0.0.1', port: 5180, strictPort: true,
    proxy: { '/api': { target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:8101' }, '/workflow-api': { target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:8101' } } },
});

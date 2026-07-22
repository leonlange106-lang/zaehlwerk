import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base: './' – relative Asset-Pfade, damit die App auch hinter dem dynamischen
// Home-Assistant-Ingress-Basispfad lädt (kein festes /-Präfix).
// outDir: die von FastAPI ausgelieferte statische Oberfläche (ersetzt das alte
// Vue-Frontend in-place beim Docker-Build).
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    // Baut nach webapp/dist; der Docker-Build kopiert das nach /app/frontend
    // (ersetzt in-place das bisherige Vue-Frontend). Größere Vendor-Chunks
    // (ECharts/Mantine) werden abgesplittet.
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: {
          echarts: ['echarts', 'echarts-for-react'],
          mantine: ['@mantine/core', '@mantine/hooks', '@mantine/form', '@mantine/notifications'],
          react: ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  },
  server: {
    // Dev-Server proxyt API-Aufrufe an das laufende Backend.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
});

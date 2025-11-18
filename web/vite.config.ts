import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: true
  },
  resolve: {
    extensions: ['.ts', '.tsx', '.mts', '.cts', '.js', '.mjs', '.jsx', '.cjs', '.json']
  },
  preview: {
    host: true
  }
});

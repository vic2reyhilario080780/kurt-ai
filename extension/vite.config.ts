import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// MV3 popup build. No vite dev server workflow for this project — extension
// pages don't allow loading scripts from a remote dev server (CSP), so the
// only supported flow is `npm run build` then "Load unpacked" on dist/.
export default defineConfig({
  root: 'src/popup',
  plugins: [react()],
  build: {
    outDir: '../../dist/popup',
    emptyOutDir: true,
  },
});

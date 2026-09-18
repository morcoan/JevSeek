import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react(), {
    name: 'preview-dev-csp',
    apply: 'serve',
    // Vite's development-only refresh preamble is inline. Desktop only loads dist,
    // whose strict CSP is left intact. This server is an unprivileged browser preview.
    transformIndexHtml: html => html.replace(/\s*<meta http-equiv="Content-Security-Policy"[^>]*>/, ''),
  }],
  base: './',
  server: { host: '127.0.0.1', port: 5173, strictPort: true },
  build: { target: 'es2022' },
});

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Root .env (polymath/.env) is shared with the future backend, so envDir is the repo root.
// Lens configs live in polymath/lenses, so the dev server may read one level up.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  envDir: '..',
  server: { fs: { allow: ['..'] } },
})

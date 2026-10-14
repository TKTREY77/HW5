import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The dashboard runs on http://localhost:5173 and calls FastAPI directly at http://localhost:8000
// (backend CORS allows this origin). Override the API with VITE_API_BASE if needed.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
})

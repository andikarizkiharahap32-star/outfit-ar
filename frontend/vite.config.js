import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react()
  ],
  server: {
    host: true,      // Wajib true agar bisa diakses dari luar (HP via Cloudflare)
    port: 5173,
    allowedHosts: true, // Izinkan semua host termasuk *.trycloudflare.com

    // PROXY: Semua request /api dan /uploads dari HP diforward ke backend lokal
    // Ini menghilangkan CORS issue karena HP hanya berkomunikasi dengan 1 domain (Cloudflare)
    // Flow HP: Safari -> Cloudflare -> Vite Proxy -> localhost:8000
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        // Tambah header ngrok-skip agar tidak kena interstitial jika backend pakai ngrok
        headers: {
          'ngrok-skip-browser-warning': 'true',
          'Bypass-Tunnel-Reminder': 'true',
        }
      },
      '/uploads': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})
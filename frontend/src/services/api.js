//Sisi Frontend (Yang Mengirim Request) Front To Backend

// axios dipakai untuk HTTP request ke backend — lebih praktis dari fetch biasa
import axios from 'axios';

// BACKEND_URL:
// - Laptop: diakses via http://localhost:8000 langsung
// - HP via Cloudflare: diakses via Vite Proxy (/api -> localhost:8000)
//   Sehingga HP hanya perlu akses 1 domain (Cloudflare) tanpa CORS issue
export const BACKEND_URL = import.meta.env.VITE_API_URL || '';

//Sisi Frontend (Yang Mengirim Request) Front To Backend
// Gunakan baseURL dari BACKEND_URL, atau relatif (/api/v1) agar request HP lewat Vite proxy
const api = axios.create({
  baseURL: BACKEND_URL ? `${BACKEND_URL.replace(/\/+$/, '')}/api/v1` : `/api/v1`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'ngrok-skip-browser-warning': 'true',
    'Bypass-Tunnel-Reminder': 'true',
  },
});


// 1. Interceptor Request (Token & Security)
// Dijalankan sebelum setiap request dikirim — tempat nyuntik token JWT
api.interceptors.request.use(
  (config) => {
    // Ambil token dari localStorage kalau user sudah login
    const token = localStorage.getItem('outfit_ar_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Pastikan header ngrok selalu ada meskipun sudah di-set di default
    config.headers['ngrok-skip-browser-warning'] = 'true';
    config.headers['Bypass-Tunnel-Reminder'] = 'true';
    // Log setiap request biar gampang debug di DevTools
    console.log(`[API] Request: [${config.method.toUpperCase()}] ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// 2. Interceptor Response (Unwrapping & Error Monitoring)
// Dijalankan setelah respons diterima — langsung unwrap ke response.data
api.interceptors.response.use(
  (response) => {
    // Langsung kembalikan data-nya saja, bukan seluruh objek response axios
    return response.data;
  },
  (error) => {
    console.error("[API] DETAIL ERROR JARINGAN:");

    if (error.response) {
      // Server merespons tapi dengan status error (4xx / 5xx)
      console.error("Status:", error.response.status);
      const msg = error.response.data?.detail || "Terjadi kesalahan pada server";
      return Promise.reject(new Error(msg));
    } else if (error.request) {
      // Request dikirim tapi tidak ada respons — kemungkinan tunnel mati atau IP diblok
      console.error("Server Tidak Merespons / Tunnel Offline / Blocked by Interstitial.");
      return Promise.reject(new Error("Koneksi Backend Terputus (Pastikan Tunnel Aktif dan sudah verifikasi IP)"));
    } else {
      // Error terjadi sebelum request sempat dikirim
      console.error("Error Message:", error.message);
      return Promise.reject(error);
    }
  }
);

// --- ENDPOINT SERVICES ---

// --- UBAH URL ZALORA MENJADI TEXTURE 3D ---
// Fungsi helper untuk convert URL gambar produk jadi object URL blob
// Dipakai supaya gambar dari Zalora/Shopee bisa dipakai sebagai tekstur di Three.js
export const get3DTexture = async (imageUrl) => {
  if (!imageUrl) return null;
  try {
    // Menggunakan proxy gratis untuk menghindari blokir CORS dari Zalora/Shopee
    const res = await fetch(`https://api.allorigins.win/raw?url=${encodeURIComponent(imageUrl)}`);
    const blob = await res.blob();
    // Buat URL sementara dari blob — bisa langsung dipasang ke texture loader
    return URL.createObjectURL(blob);
  } catch (error) {
    console.error("Gagal mengubah gambar menjadi tekstur:", error);
    return null;
  }
};

// Endpoint autentikasi — register dan login user
export const authAPI = {
  register: (data) => api.post('/users/register', data),
  login: (data) => api.post('/users/login', data),
};

// Endpoint deteksi skin tone — kirim foto, dapat hasil analisis warna kulit
export const skinToneAPI = {
  detect: (imageFile) => {
    // Pakai FormData karena kita upload file, bukan JSON biasa
    const formData = new FormData();
    formData.append('image', imageFile);
    return api.post('/recommendations/detect-skin-tone', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'ngrok-skip-browser-warning': 'true',
        'Bypass-Tunnel-Reminder': 'true'
      },
    });
  },
};

// Endpoint rekomendasi outfit berdasarkan skin tone dan preferensi user
export const recommendationAPI = {
  getOutfit: (data) => api.post('/recommendations/outfit', data),
  // Kirim feedback apakah rekomendasi cocok atau tidak — untuk improve model
  feedback: (data) => api.post('/recommendations/feedback', data),
};

// Endpoint produk — list, detail, dan kategori
export const productAPI = {
  list: (params) => api.get('/products', { params }), // params bisa untuk filter/pagination
  detail: (id) => api.get(`/products/${id}`),
  categories: () => api.get('/products/categories'),
};

// Endpoint AR — tryon foto statis (bukan real-time)
export const arAPI = {
  tryonPhoto: (photoFile, productId) => {
    const formData = new FormData();
    formData.append('user_photo', photoFile);
    // productId dikirim lewat query param, bukan body
    return api.post(`/ar/tryon/photo?product_id=${productId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// Buat koneksi WebSocket untuk AR real-time
// Otomatis deteksi host dari window.location agar bekerja di laptop & HP
export const WS_URL = import.meta.env.VITE_WS_URL || '';

export function createARWebSocket(productId) {
  let wsUrl = '';
  if (WS_URL) {
    const base = WS_URL.replace(/\/+$/, '');
    wsUrl = `${base}/api/v1/ar/tryon/realtime/${productId}`;
  } else if (BACKEND_URL) {
    const base = BACKEND_URL.replace(/\/+$/, '');
    const proto = base.startsWith('https') ? 'wss:' : 'ws:';
    const host = base.replace(/^https?:\/\//, '');
    wsUrl = `${proto}//${host}/api/v1/ar/tryon/realtime/${productId}`;
  } else {
    const proto  = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    wsUrl = `${proto}//${window.location.host}/api/v1/ar/tryon/realtime/${productId}`;
  }
  
  console.log("[AR] Inisialisasi WebSocket AR:", wsUrl);
  return new WebSocket(wsUrl);
}

// Export default instance api — bisa dipakai langsung kalau perlu custom request
export default api;
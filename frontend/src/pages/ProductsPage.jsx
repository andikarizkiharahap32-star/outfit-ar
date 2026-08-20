import React, { useState, useEffect, useCallback, useRef, Component } from 'react'
import {
  MagnifyingGlass, Database, WarningCircle, ArrowsClockwise, CaretRight, X, Package,
  Tote, Heart, User as UserIcon, WifiSlash, TerminalWindow, Pulse
} from '@phosphor-icons/react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'

// Preload GLB di background saat ProductsPage dibuka
// Saat user klik AR, model sudah ada di browser cache → muncul instan
const GLB_PRELOAD_URLS = [
  '/models/PriaShort.glb',
  '/models/PriaPolo.glb',
  '/models/Wanita.glb',
  '/models/WanitaBerhijab.glb',
];
GLB_PRELOAD_URLS.forEach(url => {
  // Pakai link rel=prefetch agar browser cache file ini
  if (typeof document !== 'undefined') {
    const link = document.createElement('link');
    link.rel = 'prefetch';
    link.href = url;
    link.as = 'fetch';
    link.crossOrigin = 'anonymous';
    document.head.appendChild(link);
  }
  // Sekaligus fetch ke cache JS (untuk GLTFLoader.parse)
  fetch(url, { priority: 'low' }).catch(() => {});
});


// ============================================================
// ⚙️ [LAYER 1] KONFIGURASI GLOBAL
// ============================================================
// Gunakan URL relatif agar request lewat Vite proxy
// Laptop: Vite langsung forward ke localhost:8000
// HP: Cloudflare → Vite → localhost:8000 (tanpa CORS)
const NGROK_BACKEND_URL = '';

const NGROK_HEADERS = {
  "ngrok-skip-browser-warning": "69420",
  "Accept": "application/json",
}

// ============================================================
// 🛡️ [LAYER 2] REACT ERROR BOUNDARY
// ============================================================
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorInfo: null, errorMessage: "" };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, errorMessage: error.toString() };
  }
  componentDidCatch(error, errorInfo) {
    console.error("💥 REACT CRASH DETECTED:", error, errorInfo);
    this.setState({ errorInfo });
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#050505] flex flex-col items-center justify-center p-6 text-center">
          <div className="outer-shell max-w-2xl w-full">
            <div className="inner-core p-8 bg-black/60 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-red-500 animate-pulse" />
              <WarningCircle size={64} weight="light" className="text-red-500 mb-6 mx-auto" />
              <h1 className="text-xl font-medium text-white mb-2 tracking-wide">Sistem UI Mengalami Crash</h1>
              <p className="text-white/50 mb-6 text-sm font-light">Aplikasi dicegah mati total. Silakan periksa log merah di bawah ini untuk mengetahui penyebab pastinya:</p>

              <div className="bg-red-500/10 text-red-400 p-5 rounded-2xl text-left font-mono text-xs overflow-auto mb-8 border border-red-500/20 max-h-64 shadow-inner">
                <strong className="text-red-300">💥 PESAN ERROR:</strong>
                <div className="mt-1 mb-4 leading-relaxed">{this.state.errorMessage}</div>

                <strong className="text-red-300">📍 LOKASI KERUSAKAN:</strong>
                <pre className="mt-2 text-[10px] text-red-500/80 leading-relaxed whitespace-pre-wrap">{this.state.errorInfo?.componentStack}</pre>
              </div>

              <button onClick={() => window.location.reload()} className="btn-premium px-8 py-3.5 bg-white text-black font-semibold text-sm tracking-wide rounded-full transition-colors w-full sm:w-auto">
                Muat Ulang Aplikasi
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// ============================================================
// 🌐 [LAYER 3] NETWORK STATUS HOOK
// ============================================================
function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);
  return isOnline;
}

// ============================================================
// 🔗 [LAYER 4] OMNIDIRECTIONAL PATH HUNTER
// ============================================================
function generateFallbackUrls(rawPath, genderContext) {
  if (!rawPath) return [];
  // Gunakan path relatif /uploads/* agar lewat Vite proxy
  const urls = [];

  let clean = rawPath.replace(/\\/g, '/').replace(/\/+/g, '/').trim();
  if (clean.startsWith('http')) {
    try { clean = new URL(clean).pathname; } catch (e) { }
  }
  if (clean.startsWith('/')) clean = clean.substring(1);
  clean = clean.replace(/^(uploads\/|storage\/)/i, '');
  if (!clean.startsWith('products/')) clean = 'products/' + clean;

  const filename = clean.split('/').pop();

  if (genderContext) {
    let folder = '';
    const g = genderContext.toLowerCase();
    if (g === 'pria') folder = 'Pria';
    else if (g === 'wanita') folder = 'Wanita';
    else if (g === 'wanitahijab') folder = 'wanitahijab';
    if (folder) urls.push(`/uploads/products/${folder}/${filename}`);
  }

  urls.push(`/uploads/${clean}`);
  urls.push(`/uploads/products/wanitahijab/${filename}`);
  urls.push(`/uploads/products/Wanita/${filename}`);
  urls.push(`/uploads/products/Pria/${filename}`);
  urls.push(`/uploads/products/${filename}`);

  return [...new Set(urls)];
}


function storeSelectedARProduct(product) {
  if (!product) return;
  const normalized = {
    ...product,
    id: product.id ?? product.product_id ?? product.productId,
    image_url: product.image_url || product.image || product.thumbnail_url || product.photo_url || product.ar_image_url || ''
  };

  try {
    localStorage.setItem('outfitar_selected_product', JSON.stringify(normalized));
    localStorage.setItem('outfitar_active_product', JSON.stringify(normalized));
    sessionStorage.setItem('outfitar_selected_product', JSON.stringify(normalized));
    sessionStorage.setItem('outfitar_active_product', JSON.stringify(normalized));
    localStorage.setItem('outfitar_active_product_id', String(normalized.id || ''));
    sessionStorage.setItem('outfitar_active_product_id', String(normalized.id || ''));
  } catch (err) {
    console.warn('Tidak bisa menyimpan produk AR:', err);
  }
}

function openARProduct(product, navigate, setActiveProduct) {
  const productId = product?.id ?? product?.product_id ?? product?.productId;
  if (!productId) {
    alert('Gagal: ID baju tidak terbaca dari database.');
    return;
  }

  storeSelectedARProduct(product);

  if (typeof setActiveProduct === 'function') {
    try { setActiveProduct(productId); } catch (err) { console.warn('setActiveProduct gagal:', err); }
  }

  const targetPath = `/ar/${encodeURIComponent(String(productId))}`;
  const state = {
    selectedProduct: product,
    productId,
    cameraMode: 'wide',
    preferredZoom: 'min',
    garmentScale: 0.82,
    from: 'recommendation'
  };

  try {
    navigate(targetPath, { state });
  } catch (err) {
    console.warn('React navigate gagal, pakai fallback native:', err);
    window.location.assign(targetPath);
    return;
  }

  window.setTimeout(() => {
    if (!window.location.pathname.includes(`/ar/${String(productId)}`)) {
      window.location.assign(targetPath);
    }
  }, 160);
}

// ============================================================
// 🖼️ [LAYER 5] NON-BLOCKING SMART IMAGE QUEUE
// ============================================================
const imageCache = new Map();
const imageQueue = [];
let activeImageRequests = 0;
const MAX_CONCURRENT_IMAGES = 3;

const fetchWithFallback = (fallbackUrls, index, onSuccess, onFailure) => {
  const currentUrl = fallbackUrls[index];
  fetch(currentUrl, { headers: NGROK_HEADERS })
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.blob();
    })
    .then(blob => {
      const blobObjectUrl = URL.createObjectURL(blob);
      onSuccess(blobObjectUrl);
    })
    .catch(() => {
      if (index + 1 < fallbackUrls.length) {
        fetchWithFallback(fallbackUrls, index + 1, onSuccess, onFailure);
      } else {
        onFailure();
      }
    });
};

const processImageQueue = () => {
  if (activeImageRequests >= MAX_CONCURRENT_IMAGES || imageQueue.length === 0) return;
  const queueItem = imageQueue.shift();
  const { fallbackUrls, primaryCacheKey, onSuccess, onError } = queueItem;
  activeImageRequests++;

  fetchWithFallback(
    fallbackUrls, 0,
    (blobUrl) => {
      activeImageRequests--;
      imageCache.set(primaryCacheKey, blobUrl);
      onSuccess(blobUrl);
      processImageQueue();
    },
    () => {
      activeImageRequests--;
      onError();
      processImageQueue();
    }
  );
};

function useNgrokImage(rawPath, genderContext = null) {
  const [blobUrl, setBlobUrl] = useState(null)
  const [status, setStatus] = useState('idle')
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  useEffect(() => {
    if (!rawPath) { setStatus('error'); return }
    const fallbackUrls = generateFallbackUrls(rawPath, genderContext);
    if (fallbackUrls.length === 0) { setStatus('error'); return; }

    const primaryCacheKey = fallbackUrls[0];
    if (imageCache.has(primaryCacheKey)) {
      setBlobUrl(imageCache.get(primaryCacheKey)); setStatus('ok'); return;
    }

    setStatus('loading')
    imageQueue.push({
      fallbackUrls, primaryCacheKey,
      onSuccess: (url) => { if (mountedRef.current) { setBlobUrl(url); setStatus('ok'); } },
      onError: () => { if (mountedRef.current) setStatus('error'); }
    });
    processImageQueue();
  }, [rawPath, genderContext])

  return { blobUrl, status }
}

// ============================================================
// 📡 [LAYER 6] ROBUST API MATCHER
// ============================================================
const api = {
  async getProducts({ page = 1, per_page = 16, search = '', gender = '' } = {}) {
    const params = new URLSearchParams({ page, per_page })
    if (search) params.append('search', search)
    if (gender) params.append('gender', gender)

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

    try {
      // Gunakan path relatif agar lewat Vite proxy (bekerja di laptop & HP)
      const res = await fetch(`/api/v1/products/?${params}`, {
        headers: NGROK_HEADERS, signal: controller.signal
      })
      clearTimeout(timeoutId);

      const contentType = res.headers.get("content-type");
      if (contentType && contentType.includes("text/html")) throw new Error("NGROK_BLOCKED");
      if (!res.ok) throw new Error(`HTTP_${res.status}`);

      return await res.json()
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') throw new Error("TIMEOUT");
      if (err.message.includes("Unexpected token") || err.message === "NGROK_BLOCKED") throw new Error("NGROK_BLOCKED");
      throw err;
    }
  }
}


// ============================================================
// 🎨 [LAYER 7] UI COMPONENTS
// ============================================================
function ZaloraHeader({ search, setSearch, handleSearch }) {
  return (
    <header className="bg-[#050505] text-white border-b border-white/10 sticky top-0 z-50 shadow-sm backdrop-blur-xl">
      <div className="bg-white/5 text-white/60 text-[10px] sm:text-xs py-2 px-6 flex justify-between items-center overflow-x-auto whitespace-nowrap gap-4">
        <span>Gratis Pengembalian | S&K berlaku</span>
        <span className="font-bold text-violet-400"></span>
        <span>Download & dapatkan DISKON 25% + CASHBACK 5%</span>
      </div>
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between gap-6">
        <div className="text-2xl sm:text-3xl font-light tracking-[0.2em] cursor-pointer">OUTFITAR</div>
        <form onSubmit={handleSearch} className="flex-1 max-w-2xl hidden md:block">
          <div className="relative group">
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Cari produk, merek, atau tren terbaru..." className="w-full bg-white/5 border border-white/10 rounded-full py-2.5 pl-12 pr-12 text-sm outline-none focus:border-white/30 focus:bg-white/10 transition-all text-white placeholder-white/30" />
            <button type="submit" className="absolute left-4 top-1/2 -translate-y-1/2 text-white/40 group-hover:text-white transition-colors"><MagnifyingGlass size={18} /></button>
            {search && <button type="button" onClick={() => setSearch('')} className="absolute right-4 top-1/2 -translate-y-1/2 text-white/30 hover:text-red-400"><X size={14} /></button>}
          </div>
        </form>
        <div className="flex items-center gap-5 text-sm font-medium text-white/70">
          <button className="flex items-center gap-2 hover:text-white transition-colors"><UserIcon size={20} weight="light" /> <span className="hidden lg:inline">Masuk / Daftar</span></button>
          <button className="hover:text-red-400 transition-colors"><Heart size={20} weight="light" /></button>
          <button className="hover:text-white transition-colors"><Tote size={20} weight="light" /></button>
        </div>
      </div>
    </header>
  )
}

function HeroBanner() {
  return (
    <div className="py-16 md:py-24 border-b border-white/10 bg-[#0a0a0a] flex flex-col items-center justify-center relative overflow-hidden">
      <div className="absolute w-[500px] h-[500px] border border-white/5 rounded-full -z-0 opacity-50" />
      <div className="absolute w-[300px] h-[300px] border border-white/10 rounded-full -z-0 opacity-50" />

      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.8, ease: [0.32, 0.72, 0, 1] }}
        className="w-32 h-32 md:w-40 md:h-40 bg-white/5 backdrop-blur-xl border border-white/10 rounded-full flex flex-col items-center justify-center mb-8 shadow-2xl z-10 cursor-default hover:bg-white/10 transition-colors duration-500"
      >
        <span className="text-white font-black text-2xl md:text-3xl tracking-[0.2em] leading-none mb-1">AR</span>
        <span className="text-white/40 font-semibold text-[10px] md:text-xs tracking-widest uppercase">Try-On</span>
      </motion.div>

      <motion.h2
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.8, delay: 0.2, ease: [0.32, 0.72, 0, 1] }}
        className="text-2xl md:text-4xl font-medium text-white tracking-widest uppercase text-center z-10"
      >
        Katalog <span className="italic font-light">Premium</span>
      </motion.h2>

      <motion.p
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.8, delay: 0.3, ease: [0.32, 0.72, 0, 1] }}
        className="text-white/40 text-xs md:text-sm mt-4 tracking-[0.2em] font-light text-center max-w-lg px-6 z-10"
      >
        Jelajahi koleksi busana virtual dengan simulasi AR
      </motion.p>
    </div>
  )
}

function ProductCard({ product, onNavigateAR }) {
  const { blobUrl, status } = useNgrokImage(product.image_url, product.gender)
  const arClickLockRef = useRef(false);

  const handleProductAR = (event) => {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    if (arClickLockRef.current) return;
    arClickLockRef.current = true;
    onNavigateAR(product);
    window.setTimeout(() => { arClickLockRef.current = false; }, 900);
  };

  return (
    <motion.div layout initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }} transition={{ duration: 0.5, ease: [0.32, 0.72, 0, 1] }} className="outer-shell group cursor-pointer flex flex-col h-full" onDoubleClick={handleProductAR}>
      <div className="inner-core p-2 bg-black/60 flex flex-col h-full">
        <div className="relative aspect-[3/4] bg-black/40 mb-3 overflow-hidden rounded-2xl">
          {status === 'loading' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3"><div className="w-6 h-6 border-2 border-white/10 border-t-white rounded-full animate-spin" /></div>
          )}
          {status === 'ok' && <img src={blobUrl} alt={product.name} className="w-full h-full object-cover transition-transform duration-[1.5s] ease-[cubic-bezier(0.32,0.72,0,1)] group-hover:scale-105" />}
          {status === 'error' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-white/30 bg-black/60"><Package size={32} weight="light" className="mb-2 opacity-50" /><span className="text-[9px] uppercase tracking-wider font-semibold">Image Error</span></div>
          )}
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent flex items-end justify-center pb-6 opacity-0 group-hover:opacity-100 transition-opacity duration-500 z-10 px-4 pointer-events-auto">
            <button type="button" onClick={handleProductAR} onPointerUp={handleProductAR} onTouchEnd={handleProductAR} className="btn-premium w-full py-3 bg-white text-black text-xs font-semibold rounded-full flex items-center justify-center gap-2 hover:bg-gray-200 transition-colors shadow-xl touch-manipulation">
              Visualize AR <CaretRight size={14} weight="bold" />
            </button>
          </div>
        </div>
        <div className="flex-1 flex flex-col px-2 pb-2">
          <h3 className="text-[10px] font-semibold text-white/40 uppercase tracking-[0.2em] mb-1">{product.brand || 'Zalora Exclusive'}</h3>
          <h4 className="text-sm text-white/90 font-medium line-clamp-2 leading-relaxed mb-3 group-hover:text-white transition-colors">{product.name}</h4>
          <div className="mt-auto pt-3 border-t border-white/10 flex justify-between items-end">
            <div>
              {product.price && <p className="text-sm font-semibold text-white">Rp {Number(product.price).toLocaleString('id-ID')}</p>}
              <p className="text-[10px] text-white/40 mt-1 uppercase tracking-widest font-medium">{product.gender === 'wanitahijab' ? 'Wanita Hijab' : product.gender || 'Pakaian'}</p>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

function ProductSkeleton() {
  return (
    <div className="outer-shell flex flex-col h-full animate-pulse">
      <div className="inner-core p-2 bg-black/60">
        <div className="aspect-[3/4] bg-white/5 mb-3 rounded-2xl" />
        <div className="px-2 pb-2">
          <div className="h-2 bg-white/5 w-1/3 mb-3 rounded" />
          <div className="h-3 bg-white/10 w-full mb-2 rounded" />
          <div className="h-3 bg-white/10 w-2/3 mb-4 rounded" />
          <div className="h-4 bg-white/10 w-1/2 mt-auto rounded" />
        </div>
      </div>
    </div>
  )
}

// ============================================================
// 🛠️ COMPONENT MAIN PAGE
// ============================================================
function ProductsPageInternal() {
  const navigate = useNavigate()
  const isOnline = useNetworkStatus();

  const [products, setProducts] = useState([])
  const [meta, setMeta] = useState(null)
  const [loading, setLoading] = useState(true)
  const [errorData, setErrorData] = useState(null)
  const [search, setSearch] = useState('')
  const [activeSearch, setActiveSearch] = useState('')
  const [gender, setGender] = useState('wanita')
  const [page, setPage] = useState(1)
  const [showDebug, setShowDebug] = useState(false)

  const fetchProducts = useCallback(async (overrides = {}) => {
    setLoading(true)
    setErrorData(null)
    try {
      const apiGender = overrides.gender ?? gender;
      const apiSearch = overrides.search ?? activeSearch;
      const res = await api.getProducts({ page, per_page: 16, search: apiSearch, gender: apiGender })

      const items = res.data ?? res.items ?? []
      const metaInfo = res.meta ?? { total: res.total ?? items.length }
      setProducts(items)
      setMeta(metaInfo)
    } catch (err) {
      console.error('API Fetch Error:', err)
      if (err.message === "NGROK_BLOCKED") setErrorData({ type: "NGROK", message: "Koneksi diblokir oleh sistem keamanan Ngrok. Anda belum memberikan izin akses (Visit Site)." })
      else if (err.message === "TIMEOUT") setErrorData({ type: "TIMEOUT", message: "Server backend terlalu lama merespons (Timeout 15s)." })
      else if (!isOnline) setErrorData({ type: "OFFLINE", message: "Koneksi internet Anda terputus." })
      else setErrorData({ type: "SERVER", message: `Gagal terhubung ke Database/Backend. Detail: ${err.message}` })
    } finally {
      setLoading(false)
    }
  }, [page, activeSearch, gender, isOnline])

  useEffect(() => {
    if (isOnline) { fetchProducts(); } else { setErrorData({ type: "OFFLINE", message: "Menunggu koneksi internet..." }); setLoading(false); }
  }, [fetchProducts, isOnline])

  const handleSearchSubmit = (e) => { e.preventDefault(); setPage(1); setActiveSearch(search); }
  const handleGenderChange = (val) => { setGender(val); setPage(1); }

  const MAIN_CATEGORIES = [
    { value: 'pria', label: 'PRIA' }, { value: 'wanita', label: 'WANITA' }, { value: 'wanitahijab', label: 'WANITA BERHIJAB' },
  ]

  const renderErrorState = () => {
    if (!errorData) return null;
    if (errorData.type === "NGROK") {
      return (
        <div className="py-24 px-6 text-center max-w-2xl mx-auto flex flex-col items-center">
          <div className="w-20 h-20 bg-white/5 border border-white/10 text-white/50 rounded-full flex items-center justify-center mb-6"><WarningCircle size={32} weight="light" /></div>
          <h2 className="text-2xl font-medium tracking-wide mb-4 text-white">Akses Ngrok Tertunda</h2>
          <p className="text-white/60 mb-8 font-light leading-relaxed">Sistem mendeteksi bahwa browser Anda menolak mengambil data karena halaman peringatan Ngrok (Visit Site) belum disetujui.</p>
          <div className="outer-shell w-full mb-8 text-left">
            <div className="inner-core p-6 bg-black/40">
              <h3 className="font-semibold text-sm mb-4 text-white">Langkah Penyelesaian:</h3>
              <ol className="list-decimal pl-5 text-sm text-white/60 space-y-3 font-light">
                <li>Buka tab baru di browser Anda.</li>
                <li>Kunjungi link: <a href={NGROK_BACKEND_URL} target="_blank" rel="noreferrer" className="text-violet-400 font-semibold underline">{NGROK_BACKEND_URL}</a></li>
                <li>Klik tombol biru bertuliskan <strong>"Visit Site"</strong>.</li>
                <li>Tutup tab tersebut dan kembali ke halaman ini.</li>
              </ol>
            </div>
          </div>
          <button onClick={() => fetchProducts()} className="btn-premium px-10 py-4 bg-white text-black text-sm font-semibold rounded-full transition-colors">Saya Sudah Klik Visit Site</button>
        </div>
      )
    }
    return (
      <div className="py-32 text-center flex flex-col items-center">
        {errorData.type === "OFFLINE" ? <WifiSlash size={48} weight="light" className="text-white/20 mb-6" /> : <WarningCircle size={48} weight="light" className="text-red-400 mb-6" />}
        <h2 className="text-xl font-medium mb-3 text-white">{errorData.type === "TIMEOUT" ? "Waktu Habis" : "Koneksi Terputus"}</h2>
        <p className="text-white/50 mb-8 max-w-md font-light">{errorData.message}</p>
        <button onClick={() => fetchProducts()} className="btn-premium px-8 py-3 bg-white/5 hover:bg-white/10 border border-white/10 text-white text-sm font-semibold rounded-full transition-colors">Coba Muat Ulang</button>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#050505] font-sans text-white relative">
      <AnimatePresence>
        {!isOnline && (
          <motion.div initial={{ y: -50 }} animate={{ y: 0 }} exit={{ y: -50 }} className="fixed top-0 left-0 right-0 bg-red-500 text-white text-[10px] font-semibold tracking-widest uppercase py-3 text-center z-[100] shadow-md flex items-center justify-center gap-2">
            <WifiSlash size={14} weight="bold" /> Anda Sedang Offline
          </motion.div>
        )}
      </AnimatePresence>

      <ZaloraHeader search={search} setSearch={setSearch} handleSearch={handleSearchSubmit} />

      <div className="border-b border-white/5 sticky top-[72px] bg-[#050505]/80 backdrop-blur-xl z-40">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-center md:justify-start gap-8 overflow-x-auto no-scrollbar">
          {MAIN_CATEGORIES.map(cat => (
            <button key={cat.value} onClick={() => handleGenderChange(cat.value)} className={`py-4 text-[10px] font-semibold tracking-[0.2em] whitespace-nowrap transition-colors relative uppercase ${gender === cat.value ? 'text-white' : 'text-white/40 hover:text-white/80'}`}>
              {cat.label} {gender === cat.value && <motion.div layoutId="activeTab" className="absolute bottom-0 left-0 w-full h-[2px] bg-white rounded-t-full" />}
            </button>
          ))}
        </div>
      </div>

      <HeroBanner />

      <main className="max-w-7xl mx-auto px-6 py-16">
        <div className="flex justify-between items-end mb-10">
          <div>
            <h1 className="font-display text-3xl font-medium tracking-tight">Koleksi <span className="italic text-white/50">{gender}</span></h1>
            <p className="text-sm text-white/40 mt-2 font-light">{meta?.total ? `${meta.total} item tersedia` : 'Menyiapkan arsip...'} {activeSearch && <span> untuk "{activeSearch}"</span>}</p>
          </div>
        </div>

        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
              {[...Array(10)].map((_, i) => <ProductSkeleton key={i} />)}
            </motion.div>
          ) : errorData ? (
            <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>{renderErrorState()}</motion.div>
          ) : products.length === 0 ? (
            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="py-32 text-center flex flex-col items-center">
              <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center mb-6">
                <MagnifyingGlass size={32} weight="light" className="text-white/30" />
              </div>
              <h2 className="text-xl font-medium text-white mb-3">Produk Tidak Ditemukan</h2>
              <p className="font-light text-white/50 text-sm max-w-sm mb-8">Maaf, kami tidak menemukan pakaian yang cocok dengan pencarian Anda.</p>
              <button onClick={() => { setActiveSearch(''); setSearch(''); fetchProducts({ search: '' }); }} className="btn-premium px-8 py-3 bg-white/5 hover:bg-white/10 border border-white/10 text-white text-sm font-semibold rounded-full transition-colors">Hapus Filter</button>
            </motion.div>
          ) : (
            <motion.div key="grid" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
              {products.map((p) => <ProductCard key={p.id} product={p} onNavigateAR={(product) => openARProduct(product, navigate)} />)}
            </motion.div>
          )}
        </AnimatePresence>

        {meta && meta.total > 16 && !loading && !errorData && (
          <div className="flex justify-center items-center gap-6 mt-20 pt-8 border-t border-white/5">
            <button disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))} className="text-xs font-semibold uppercase tracking-widest text-white/40 hover:text-white disabled:opacity-20 transition-colors flex items-center gap-2"><CaretRight size={14} weight="bold" className="rotate-180" /> Prev</button>
            <div className="text-[10px] font-semibold bg-white/5 border border-white/10 px-5 py-2.5 rounded-full tracking-[0.2em] uppercase text-white/70">HALAMAN {page} / {Math.ceil(meta.total / 16)}</div>
            <button disabled={page >= Math.ceil(meta.total / 16)} onClick={() => setPage(p => p + 1)} className="text-xs font-semibold uppercase tracking-widest text-white/40 hover:text-white disabled:opacity-20 transition-colors flex items-center gap-2">Next <CaretRight size={14} weight="bold" /></button>
          </div>
        )}
      </main>

      {/* Panel Debug Developer */}
      <div className="fixed bottom-6 left-6 z-50">
        <button onClick={() => setShowDebug(!showDebug)} className="w-10 h-10 bg-white/10 backdrop-blur-md border border-white/20 text-white rounded-full flex items-center justify-center opacity-30 hover:opacity-100 transition-opacity"><TerminalWindow size={16} weight="light" /></button>
        <AnimatePresence>
          {showDebug && (
            <motion.div initial={{ opacity: 0, scale: 0.9, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.9, y: 20 }} className="absolute bottom-14 left-0 w-80 bg-[#0a0a0a]/95 backdrop-blur-xl border border-white/10 text-emerald-400 p-5 rounded-3xl shadow-2xl text-[10px] font-mono z-50">
              <div className="flex justify-between items-center border-b border-white/10 pb-3 mb-4">
                <span className="font-semibold text-white uppercase tracking-widest flex items-center gap-2"><Pulse size={14} weight="bold" className="text-emerald-400" /> Monitor</span>
                <button onClick={() => setShowDebug(false)} className="w-6 h-6 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10"><X size={12} className="text-white/60" /></button>
              </div>
              <div className="space-y-3 font-medium">
                <p className="flex justify-between items-center"><span>Network</span> <span className={`px-2 py-0.5 rounded-sm ${isOnline ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-400'}`}>{isOnline ? 'ONLINE' : 'OFFLINE'}</span></p>
                <p className="flex justify-between items-center"><span>API Base</span> <span className="text-blue-300 truncate max-w-[150px] opacity-80" title={NGROK_BACKEND_URL}>{NGROK_BACKEND_URL}</span></p>
                <p className="flex justify-between items-center"><span>Active Query</span> <span className="text-amber-300 opacity-80">"{activeSearch || 'none'}"</span></p>
                <p className="flex justify-between items-center"><span>Gender State</span> <span className="text-violet-300 opacity-80">{gender}</span></p>
                <p className="flex justify-between items-center"><span>Pagination</span> <span className="text-white/60">Page {page} of {meta?.total_pages || 1}</span></p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

export default function ProductsPage() {
  return (
    <ErrorBoundary>
      <ProductsPageInternal />
    </ErrorBoundary>
  )
}
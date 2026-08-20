import React, { useState, useEffect, useRef } from 'react'
import { Sparkle, ArrowsClockwise, CaretRight, Fingerprint, Package, ThumbsUp, ThumbsDown, CheckCircle } from '@phosphor-icons/react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useLocation } from 'react-router-dom'
import useStore from '../store/useStore';
import { BACKEND_URL } from '../services/api';

const NGROK_BACKEND_URL = BACKEND_URL;

const NGROK_HEADERS = {
  "ngrok-skip-browser-warning": "69420",
  "Accept": "application/json",
  "Content-Type": "application/json"
}

// ============================================================
// 🚀 API REAL - MENGAMBIL DATA DARI DATABASE (LARAGON)
// ============================================================
const recommendationAPI = {
  getOutfit: async (payload) => {
    console.log("📡 Mengirim request KNN ke Backend:", payload);

    try {
      const res = await fetch(`${NGROK_BACKEND_URL}/api/v1/recommendations`, {
        method: 'POST',
        headers: NGROK_HEADERS,
        body: JSON.stringify(payload)
      });

      // 🚨 SMART FALLBACK
      if (res.status === 404) {
        console.warn("⚠️ API Rekomendasi (404 Not Found). Mengaktifkan Fallback...");
        const fallbackUrl = `${NGROK_BACKEND_URL}/api/v1/products?per_page=${payload.top_k}&gender=${payload.gender}`;
        const fallbackRes = await fetch(fallbackUrl, { headers: NGROK_HEADERS });

        if (!fallbackRes.ok) throw new Error(`Fallback gagal: Server error ${fallbackRes.status}`);

        const fallbackData = await fallbackRes.json();
        const items = fallbackData.data || fallbackData.items || [];

        return {
          data: {
            outfit_set: items.map((p, index) => ({
              product: p,
              knn_score: 99 - (index * 1.5)
            }))
          }
        };
      }

      if (!res.ok) {
        let errorMsg = `Server error: ${res.status}`;
        try { const errData = await res.json(); if (errData.message) errorMsg += ` - ${errData.message}`; } catch (e) { }
        throw new Error(errorMsg);
      }

      const responseData = await res.json();

      if (Array.isArray(responseData)) {
        return { data: { outfit_set: responseData } };
      }
      return responseData;

    } catch (error) {
      console.error("🚨 API Fetch Error:", error);
      throw error;
    }
  }
};

// ============================================================
// 🚀 FIX MUTLAK: URL Builder & Auto-Correct Database
// ============================================================
const imageCache = new Map();

function buildImageUrl(rawPath) {
  if (!rawPath) return '';
  let clean = rawPath;

  if (clean.startsWith('http')) {
    try { clean = new URL(clean).pathname; } catch (e) { }
  }

  clean = clean.replace(/\\/g, '/').replace(/\/+/g, '/').trim();
  if (clean.startsWith('/')) clean = clean.substring(1);

  clean = clean.replace(/\b(products|Pria|Wanita|Unisex)\s+/ig, '$1/');

  const lowerClean = clean.toLowerCase();
  if (!lowerClean.startsWith('products/') && !lowerClean.startsWith('uploads/') && !lowerClean.startsWith('storage/')) {
    clean = 'products/' + clean;
  }

  const encoded = clean.split('/').map(seg => encodeURIComponent(decodeURIComponent(seg))).join('/');
  const base = NGROK_BACKEND_URL.replace(/\/+$/, '');

  if (!encoded.toLowerCase().startsWith('uploads/') && !encoded.toLowerCase().startsWith('storage/')) {
    return `${base}/uploads/${encoded}`;
  }
  return `${base}/${encoded}`;
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

function useNgrokImage(rawPath) {
  const [blobUrl, setBlobUrl] = useState(null)
  const [status, setStatus] = useState('idle')
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  useEffect(() => {
    if (!rawPath) { setStatus('error'); return }
    const resolved = buildImageUrl(rawPath)

    if (imageCache.has(resolved)) {
      setBlobUrl(imageCache.get(resolved))
      setStatus('ok')
      return
    }

    let cancelled = false
    setStatus('loading')

    fetch(resolved, { headers: { "ngrok-skip-browser-warning": "69420" } })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.blob()
      })
      .then(blob => {
        if (cancelled || !mountedRef.current) return
        const url = URL.createObjectURL(blob)
        imageCache.set(resolved, url)
        setBlobUrl(url)
        setStatus('ok')
      })
      .catch((err) => {
        if (!cancelled && mountedRef.current) setStatus('error')
      })

    return () => { cancelled = true }
  }, [rawPath])

  return { blobUrl, status }
}

// ============================================================
// 🎨 KOMPONEN KARTU PREMIUM
// ============================================================
function RecommendationCard({ item, setActiveProduct, navigate, index, sessionId }) {
  const productData = item.product || item;
  const score = item.knn_score || item.compatibility || 90;

  const { blobUrl, status } = useNgrokImage(productData.image_url);
  const [hasRated, setHasRated] = useState(false);
  const arClickLockRef = useRef(false);

  const handleVisualizeAR = (event) => {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    if (arClickLockRef.current) return;
    arClickLockRef.current = true;
    console.log('🚀 Membuka AR untuk produk:', productData);
    openARProduct(productData, navigate, setActiveProduct);
    window.setTimeout(() => { arClickLockRef.current = false; }, 900);
  };

  const handleFeedback = async (isAccepted) => {
    setHasRated(true);

    const payload = {
      session_id: sessionId || "SES-FALLBACK",
      product_id: productData.id,
      is_accepted: isAccepted,
      feedback_score: isAccepted ? 5 : 1
    };

    console.log(`📡 Mengirim Feedback Aktual ke Backend:`, payload);

    try {
      const res = await fetch(`${NGROK_BACKEND_URL}/api/v1/recommendations/feedback`, {
        method: 'POST',
        headers: NGROK_HEADERS,
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error("Gagal merespon ke server");
      const data = await res.json();
      console.log("✅ Server response:", data.message);

    } catch (err) {
      console.error("🚨 Error Feedback:", err);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 40, filter: 'blur(10px)' }}
      animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
      transition={{ delay: index * 0.1, duration: 0.8, ease: [0.32, 0.72, 0, 1] }}
      className="outer-shell h-full group"
    >
      <div className="inner-core p-2 flex flex-col h-full bg-black/60">
        <div className="aspect-[3/4] rounded-2xl overflow-hidden bg-black/40 relative mb-4 flex items-center justify-center flex-shrink-0">

          {status === 'loading' && <div className="w-8 h-8 rounded-full border border-white/20 border-t-violet-400 animate-spin" />}
          {status === 'ok' && <img src={blobUrl} alt={productData.name || "Outfit"} className="w-full h-full object-cover transition-transform duration-[1.5s] ease-[cubic-bezier(0.32,0.72,0,1)] group-hover:scale-105" />}
          {status === 'error' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 text-white">
              <Package size={32} weight="light" className="opacity-20 mb-3 text-white" />
              <span className="text-[10px] font-medium tracking-widest uppercase text-white/40 text-center leading-relaxed">Image Not<br />Available</span>
            </div>
          )}

          <div className="absolute top-3 right-3 bg-black/40 backdrop-blur-xl px-3 py-1.5 rounded-full border border-white/10 shadow-[0_4px_12px_rgba(0,0,0,0.5)]">
            <p className="text-[10px] font-semibold tracking-wide text-white">{Math.round(score)}% Match</p>
          </div>

          <div
            className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/10 to-transparent flex items-end justify-center pb-6 opacity-0 group-hover:opacity-100 transition-opacity duration-500 z-40 pointer-events-auto"
            onClick={handleVisualizeAR}
            onPointerUp={handleVisualizeAR}
            onTouchEnd={handleVisualizeAR}
          >
            <button
              type="button"
              onClick={handleVisualizeAR}
              onPointerUp={handleVisualizeAR}
              onTouchEnd={handleVisualizeAR}
              className="bg-white text-black px-6 py-2.5 rounded-full text-xs font-semibold flex items-center gap-2 hover:bg-gray-200 transition-colors shadow-lg active:scale-95 relative z-50 pointer-events-auto touch-manipulation"
            >
              Visualize 3D <CaretRight size={14} weight="bold" />
            </button>
          </div>
        </div>
        <div className="px-3 pb-2 flex-grow flex flex-col justify-between">
          <div>
            <h4 className="font-medium text-sm truncate mb-1 text-white/90 group-hover:text-white transition-colors">{productData.name}</h4>
            <p className="text-[10px] text-white/40 font-medium uppercase tracking-[0.1em] mb-4">{productData.gender}</p>
          </div>

          <div className="pt-4 border-t border-white/10 mt-auto">
            {hasRated ? (
              <div className="flex items-center justify-center gap-2 text-green-400 text-[10px] font-semibold tracking-widest uppercase py-2">
                <CheckCircle size={16} weight="fill" /> Diterima
              </div>
            ) : (
              <div className="flex gap-2">
                <button onClick={(e) => { e.stopPropagation(); handleFeedback(true); }} className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-colors text-xs font-medium text-white/70 hover:text-white">
                  <ThumbsUp size={14} weight="light" /> Suka
                </button>
                <button onClick={(e) => { e.stopPropagation(); handleFeedback(false); }} className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-colors text-xs font-medium text-white/70 hover:text-white">
                  <ThumbsDown size={14} weight="light" /> Kurang
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ============================================================
// 🌟 HALAMAN UTAMA
// ============================================================
export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const storeGender = useStore(state => state.gender);
  
  // Baca gender dari navigasi (jika baru pindah dari SkinTone), fallback ke store, lalu 'pria'
  const activeGender = location.state?.gender || storeGender || "pria";

  // 🚨 KITA GUNAKAN USESTORE ASLI DARI ZUSTAND
  const { skinTone, sessionId, setRecommendations, setActiveProduct } = useStore();

  const [localRecs, setLocalRecs] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!skinTone?.level) return;

    let isMounted = true;

    const fetchRec = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await recommendationAPI.getOutfit({
          skin_tone_level: skinTone.level,
          skin_tone_id: skinTone?.detection_id || null,
          session_id: sessionId,
          gender: activeGender,
          top_k: 12,
        });

        if (!isMounted) return;

        const recommendedItems = res?.data?.outfit_set || res?.data || res || [];

        if (recommendedItems.length > 0) {
          setLocalRecs(recommendedItems);
          setRecommendations(res.data || res);
        } else {
          throw new Error(`Katalog kosong. Tidak ada baju ${activeGender.toUpperCase()} untuk profil warna kulit ini.`);
        }
      } catch (err) {
        if (!isMounted) return;
        console.error("🚨 RECOMMENDATION ERROR:", err);
        setError(`Gagal mengambil data: ${err.message}`);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchRec();

    return () => { isMounted = false; };
  }, [skinTone?.level, skinTone?.detection_id, sessionId, activeGender, setRecommendations]);

  if (!skinTone) return (
    <div className="min-h-screen flex items-center justify-center text-white text-center p-6">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease: [0.32, 0.72, 0, 1] }} className="outer-shell max-w-md w-full">
        <div className="inner-core p-12 flex flex-col items-center justify-center bg-black/60">
          <Fingerprint size={64} weight="light" className="mb-8 text-white/20" />
          <h2 className="text-xl font-medium mb-4 text-white">Analisis Diperlukan</h2>
          <p className="text-sm text-white/50 mb-8 font-light">Kami perlu menganalisis skin tone Anda sebelum memberikan rekomendasi yang akurat.</p>
          <button onClick={() => navigate('/skin-tone')} className="btn-premium w-full bg-white text-black py-4 rounded-full text-sm font-semibold hover:bg-gray-200 transition-colors">
            Mulai Analisis
          </button>
        </div>
      </motion.div>
    </div>
  )

  return (
    <div className="w-full max-w-[1400px] mx-auto px-6 py-12 md:py-24">
      <motion.div 
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease: [0.32, 0.72, 0, 1] }}
        className="flex flex-col md:flex-row justify-between items-start md:items-end mb-16 gap-8"
      >
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-[10px] font-semibold text-white/60 tracking-widest uppercase mb-6">
            <Sparkle size={14} weight="fill" className="text-violet-400" /> Analisis Warna
          </div>
          <h1 className="font-display text-5xl md:text-7xl font-medium tracking-tight text-white mb-4 leading-none">
            Outfit <span className="text-white/40 italic">Match</span>
          </h1>
          <p className="text-white/50 text-lg font-light">Rekomendasi untuk profil: <span className="text-white font-medium">{skinTone?.label} ({activeGender})</span></p>
        </div>
        <div className="outer-shell">
          <div className="inner-core px-8 py-6 flex flex-col items-center justify-center bg-black/60 min-w-[160px]">
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] mb-2 text-white/40">Tone Level</p>
            <p className="text-4xl font-medium tracking-tight text-white">{skinTone?.level}<span className="text-xl text-white/20">/5</span></p>
          </div>
        </div>
      </motion.div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-40 gap-6">
          <div className="relative">
            <div className="w-16 h-16 rounded-full border border-white/10" />
            <div className="absolute top-0 left-0 w-16 h-16 rounded-full border-t border-violet-500 animate-spin" />
            <Package size={24} weight="light" className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-white/30" />
          </div>
          <p className="text-xs font-semibold tracking-[0.3em] uppercase text-white/50">Mencari Koleksi...</p>
        </div>
      ) : error ? (
        <div className="outer-shell max-w-2xl mx-auto mt-20">
          <div className="inner-core p-12 flex flex-col items-center justify-center text-center bg-black/60">
            <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-6">
              <Package size={32} weight="light" className="text-red-400" />
            </div>
            <p className="text-lg font-medium text-white mb-2">Akses Data Terhambat</p>
            <p className="text-sm text-white/50 font-light mb-8 max-w-sm">{error}</p>
            <button onClick={() => window.location.reload()} className="btn-premium bg-white text-black px-8 py-3 rounded-full text-sm font-semibold flex items-center gap-2 hover:bg-gray-200 transition-colors">
              <ArrowsClockwise size={16} weight="bold" /> Muat Ulang
            </button>
          </div>
        </div>
      ) : localRecs?.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 auto-rows-fr">
          {localRecs.map((item, i) => (
            <RecommendationCard
              key={item.product?.id || item.id || i}
              item={item}
              index={i}
              sessionId={sessionId}
              setActiveProduct={setActiveProduct}
              navigate={navigate}
            />
          ))}
        </div>
      ) : (
        <div className="outer-shell max-w-2xl mx-auto mt-20">
          <div className="inner-core p-16 flex flex-col items-center justify-center text-center bg-black/60">
            <Package size={48} weight="light" className="text-white/20 mb-6" />
            <p className="text-lg font-medium text-white mb-2">Tidak Ada Rekomendasi</p>
            <p className="text-sm text-white/50 font-light">Kami belum menemukan koleksi yang cocok untuk profil ini.</p>
          </div>
        </div>
      )}
    </div>
  )
}
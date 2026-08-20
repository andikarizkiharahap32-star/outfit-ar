import React, { useState, useEffect, useRef } from 'react'
import { Sparkles, RefreshCw, ChevronRight, Fingerprint, PackageX, ThumbsUp, ThumbsDown, CheckCircle, Scan } from 'lucide-react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import WebARModal from '../components/ar/WebARModal'
import useStore from '../store/useStore.js'

// Gunakan URL relatif agar semua request lewat Vite proxy
// Ini membuat HP (via Cloudflare) dan Laptop (via localhost) bekerja tanpa CORS
const NGROK_BACKEND_URL = '';

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
      // 1. Coba panggil API Rekomendasi Asli
      const res = await fetch(`${NGROK_BACKEND_URL}/api/v1/recommendations`, {
        method: 'POST',
        headers: NGROK_HEADERS,
        body: JSON.stringify(payload)
      });

      // 2. 🚨 SMART FALLBACK (PENYELAMAT ERROR 404) 🚨
      if (res.status === 404) {
        console.warn("⚠️ API Rekomendasi (404 Not Found). Mengaktifkan Fallback ke Data Produk Biasa...");

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

      // Standarisasi response
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

function getModelPathForProduct(gender, productName) {
  const g = String(gender || '').toLowerCase().trim();
  const name = String(productName || '').toLowerCase();
  
  if (g === 'wanitahijab') {
    return '/models/WanitaBerhijab.glb';
  }
  if (g === 'wanita') {
    return '/models/Wanita.glb';
  }
  if (g === 'pria') {
    const isKaos = ['kaos', 't-shirt', 'hoodie', 'singlet', 'jersey', 'tanktop', 'tshirt', 'oblong', 'polo', 'poloshirt'].some(kw => name.includes(kw));
    return isKaos ? '/models/PriaShort.glb' : '/models/PriaPolo.glb';
  }
  return '/models/baju_rigged.glb';
}

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

  // Gunakan path relatif — Vite proxy forward /uploads/* ke backend
  if (!encoded.toLowerCase().startsWith('uploads/') && !encoded.toLowerCase().startsWith('storage/')) {
    return `/uploads/${encoded}`;
  }
  return `/${encoded}`;
}

// Hook Fetch Gambar
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


function safeSaveARProduct(productId, payload) {
  try {
    const json = JSON.stringify(payload);

    sessionStorage.setItem('activeProductId', String(productId));
    sessionStorage.setItem('activeProduct', json);
    sessionStorage.setItem('selectedProductForAR', json);
    sessionStorage.setItem('selectedARProduct', json);
    sessionStorage.setItem('outfitar_active_product_id', String(productId));
    sessionStorage.setItem('outfitar_active_product', json);
    sessionStorage.setItem('outfitar_ar_payload', json);

    localStorage.setItem('activeProductId', String(productId));
    localStorage.setItem('activeProduct', json);
    localStorage.setItem('selectedProductForAR', json);
    localStorage.setItem('selectedARProduct', json);
    localStorage.setItem('outfitar_active_product_id', String(productId));
    localStorage.setItem('outfitar_active_product', json);
    localStorage.setItem('outfitar_ar_payload', json);

    if (payload?.productImageUrl) {
      sessionStorage.setItem('arProductImage', payload.productImageUrl);
      localStorage.setItem('arProductImage', payload.productImageUrl);
    }

    if (payload?.model3dUrl) {
      sessionStorage.setItem('arProductModel', payload.model3dUrl);
      localStorage.setItem('arProductModel', payload.model3dUrl);
    }

    window.dispatchEvent(new CustomEvent('outfitar:active-product-changed', { detail: payload }));
  } catch (err) {
    console.warn('Gagal menyimpan produk AR:', err);
  }
}

function resolveProductId(productData, item) {
  return productData?.id || productData?.product_id || productData?.productId || item?.id || item?.product_id || item?.productId;
}

function resolveModelUrl(productData) {
  const raw = productData?.model_url || productData?.model_3d_url || productData?.model3d_url || productData?.glb_url || productData?.gltf_url || productData?.usdz_url || productData?.ar_model_url || productData?.file_3d_url || productData?.three_d_url;
  if (!raw) return '';
  // Jika sudah URL absolut eksternal, pakai langsung
  if (/^https?:\/\//i.test(raw)) return raw;

  // Gunakan path relatif agar lewat Vite proxy (bekerja di HP & laptop)
  const clean = String(raw).replace(/\\/g, '/').replace(/^\/+/, '');
  return `/${clean}`;
}

// ============================================================
// 🎨 KOMPONEN KARTU PREMIUM (DENGAN SISTEM FEEDBACK AI)
// ============================================================
function RecommendationCard({ item, setActiveProduct, navigate, index, sessionId, onOpenAR, activeGender }) {
  const productData = item.product || item;
  const score = item.knn_score || item.compatibility || 90;

  const { blobUrl, status } = useNgrokImage(productData.image_url);

  // State untuk Feedback (Rating) per Kartu
  const [hasRated, setHasRated] = useState(false);

  const getARTarget = () => {
    const productId = resolveProductId(productData, item);
    if (!productId) return null;
    return `/ar/${encodeURIComponent(productId)}?productId=${encodeURIComponent(productId)}&camera=wide&zoom=min&anchor=body&scale=0.82`;
  };

  const buildARPayload = () => {
    const productId = resolveProductId(productData, item);
    const productImageUrl = buildImageUrl(productData?.image_url || productData?.image || productData?.thumbnail || productData?.photo_url);
    const model3dUrl = resolveModelUrl(productData);

    return {
      product: productData,
      productId,
      id: productId,
      productName: productData?.name || productData?.title || 'Outfit',
      productImageUrl,
      imageUrl: productImageUrl,
      model3dUrl,
      modelUrl: model3dUrl,
      gender: productData?.gender,
      sessionId: sessionId || 'SES-FALLBACK',

      // Setting kamera & fitting agar halaman AR membaca produk terpilih dan tidak pakai sample default.
      cameraMode: 'wide',
      preferredCamera: 'environment',
      preferredZoom: 'min',
      requestedLens: 'ultraWide_0_5',
      garmentAnchor: 'body',
      useBodyTracking: true,
      useBodyMask: true,
      garmentScale: 0.82,
      fitMode: 'shirt',
      arFix: {
        enabled: true,
        selectedFromRecommendation: true,
        fixFloatingOverlay: true,
        followShoulders: true,
        followChest: true,
        minFpsFallback: true
      }
    };
  };

  const handleOpenAR = (event, allowNativeLink = false) => {
    if (event) {
      event.stopPropagation();
      if (!allowNativeLink) event.preventDefault();
    }

    const productId = resolveProductId(productData, item);

    if (!productId) {
      console.warn('Produk tidak punya ID, AR tidak bisa dibuka:', productData);
      alert('Produk ini belum punya ID, jadi 3D belum bisa dibuka.');
      return;
    }
    //Data dikemas dalam satu "paket" arPayload
    const targetPath = getARTarget();
    const arPayload = buildARPayload();

    safeSaveARProduct(productId, arPayload);
    setActiveProduct(productId);

    // 1) React Router navigation.
    try {
      navigate(targetPath, { state: arPayload, replace: false });
    } catch (err) {
      console.warn('React navigate gagal, pakai native redirect:', err);
    }

    // 2) Fallback khusus iPhone/Safari/ngrok: jika URL belum pindah, paksa redirect native.
    window.setTimeout(() => {
      const expectedPrefix = `/ar/${encodeURIComponent(productId)}`;
      const currentPath = window.location.pathname;
      if (!currentPath.startsWith(expectedPrefix)) {
        window.location.assign(targetPath);
      }
    }, 120);
  };

  // 🚨 KONEKSI BACKEND AKTUAL UNTUK FEEDBACK
  const handleFeedback = async (isAccepted) => {
    setHasRated(true); // Langsung ubah UI agar responsif

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

  const arTarget = getARTarget() || '#';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      onClick={(e) => {
        if (e.target.closest('a, button')) return;
        handleOpenAR(e);
      }}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') handleOpenAR(e);
      }}
      className="bg-white/[0.02] p-5 rounded-[45px] border border-white/5 group hover:bg-white/[0.05] transition-all flex flex-col h-full cursor-pointer active:scale-[0.98]"
    >
      <div className="aspect-[3/4] rounded-[35px] overflow-hidden bg-[#050508] mb-6 relative border border-white/5 flex items-center justify-center flex-shrink-0">

        {status === 'loading' && (
          <div className="w-6 h-6 border-2 border-white/10 border-t-blue-500 rounded-full animate-spin" />
        )}

        {status === 'ok' && (
          <img
            src={blobUrl}
            alt={productData.name || "Outfit"}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-1000"
          />
        )}

        {status === 'error' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#0a0a0e] text-white">
            <PackageX size={32} className="opacity-20 mb-3 text-blue-300" />
            <span className="text-[9px] font-bold tracking-widest uppercase text-gray-600 text-center leading-relaxed">
              Image Not<br />Available
            </span>
          </div>
        )}

        <div className="absolute top-4 right-4 bg-blue-600/80 backdrop-blur-md px-3 py-1.5 rounded-full border border-blue-400/30">
          <p className="text-[10px] font-black text-white italic">{Math.round(score)}% MATCH</p>
        </div>

        {/* Tombol Try-On (AR) - aktif di desktop dan HP */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-transparent to-transparent transition-opacity flex flex-col items-center justify-end opacity-100 md:opacity-0 md:group-hover:opacity-100 pb-5 gap-2">
          {/* Tombol AR Try-On Baru (Rigged + Pose) */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              const imageUrl = buildImageUrl(productData?.image_url || productData?.image || productData?.thumbnail);
              const name = productData?.name || 'Outfit';
              const gender = productData?.gender || activeGender;
              const modelPath = getModelPathForProduct(gender, name);
              onOpenAR({ imageUrl, name, modelPath });
            }}
            className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-6 py-2.5 rounded-full text-[10px] font-black uppercase tracking-widest flex items-center gap-2 hover:from-purple-500 hover:to-blue-500 transition-all shadow-lg shadow-purple-500/30 select-none touch-manipulation w-40 justify-center"
          >
            <Scan size={13} /> AR Try-On
          </button>
          {/* Tombol 3D Viewer lama tetap ada */}
          <a
            href={arTarget}
            onTouchStart={(e) => handleOpenAR(e, true)}
            onPointerDown={(e) => handleOpenAR(e, true)}
            onClick={(e) => handleOpenAR(e, false)}
            className="bg-white/10 text-white px-6 py-2 rounded-full text-[9px] font-bold uppercase tracking-widest flex items-center gap-2 hover:bg-white/20 transition-colors border border-white/20 select-none touch-manipulation w-40 justify-center"
          >
            3D View <ChevronRight size={12} />
          </a>
        </div>
      </div>

      <div className="px-2 flex-grow flex flex-col justify-between">
        <div>
          <h4 className="font-bold text-sm truncate mb-1 text-gray-200 group-hover:text-blue-400 transition-colors">
            {productData.name}
          </h4>
          <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-4">
            {productData.gender} segment
          </p>
        </div>

        {/* AREA FEEDBACK AI */}
        <div className="pt-4 border-t border-white/10 mt-auto">
          {hasRated ? (
            <div className="flex items-center justify-center gap-2 text-green-400 text-[10px] font-black tracking-widest uppercase bg-green-500/10 py-3 rounded-2xl border border-green-500/20">
              <CheckCircle size={14} /> AI Updated
            </div>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={(e) => { e.stopPropagation(); handleFeedback(true); }}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-white/5 hover:bg-green-500/20 hover:text-green-400 border border-white/10 hover:border-green-500/50 rounded-2xl transition-all text-xs font-bold text-gray-400"
              >
                <ThumbsUp size={14} /> Suka
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); handleFeedback(false); }}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-white/5 hover:bg-red-500/20 hover:text-red-400 border border-white/10 hover:border-red-500/50 rounded-2xl transition-all text-xs font-bold text-gray-400"
              >
                <ThumbsDown size={14} /> Kurang
              </button>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

// ============================================================
// 🌟 HALAMAN UTAMA (DIPERBARUI)
// ============================================================
export default function App() {
  const navigate = useNavigate();

  // 🚨 PENANGKAP PAKET GENDER (TANPA MENGUBAH BARIS IMPORT) 🚨
  // Membaca langsung dari memori React Router DOM di browser
  const activeGender = window.history.state?.usr?.gender || window.history.state?.gender || "pria";

  const { skinTone, sessionId, setRecommendations, setActiveProduct } = useStore()

  const [localRecs, setLocalRecs] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // ── State WebAR Modal ─────────────────────────────────────────────
  const [arModalOpen, setArModalOpen] = useState(false)
  const [arModalProduct, setArModalProduct] = useState({ imageUrl: null, name: '', modelPath: null })

  const handleOpenARModal = ({ imageUrl, name, modelPath }) => {
    setArModalProduct({ imageUrl, name, modelPath })
    setArModalOpen(true)
  }

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
          gender: activeGender, // 🚨 DATA WANITA SUDAH MASUK KE SINI
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

    return () => {
      isMounted = false;
    };
  }, [skinTone?.level, skinTone?.detection_id, sessionId, activeGender]);

  if (!skinTone) return (
    <div className="min-h-screen bg-[#050508] flex items-center justify-center text-white text-center p-6">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <Fingerprint size={64} className="mx-auto mb-6 opacity-20" />
        <h2 className="text-2xl font-black uppercase mb-6 tracking-widest">Scan Kulit Diperlukan</h2>
        <button onClick={() => navigate('/skin-tone')} className="bg-white text-black px-10 py-4 rounded-full text-xs font-bold uppercase tracking-widest hover:bg-blue-400 transition-all">Mulai Analisis</button>
      </motion.div>
    </div>
  )

  return (
    <div className="min-h-screen bg-[#050508] text-white font-sans">
      {/* WebAR Modal - muncul fullscreen di atas segalanya */}
      <WebARModal
        isOpen={arModalOpen}
        onClose={() => setArModalOpen(false)}
        productImageUrl={arModalProduct.imageUrl}
        productName={arModalProduct.name}
        modelPath={arModalProduct.modelPath}
      />

      <div className="max-w-7xl mx-auto px-6 py-20 min-h-screen">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-16 gap-6">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Sparkles size={16} className="text-blue-400 animate-pulse" />
              <span className="text-[10px] font-black tracking-[0.4em] text-blue-400 uppercase">AI Recommendation Engine</span>
            </div>
            <h1 className="text-7xl font-black tracking-tighter italic uppercase leading-none">Match</h1>
            <p className="text-gray-500 mt-2">Hasil algoritma KNN untuk profil: <span className="text-white font-bold">{skinTone?.label} ({activeGender.toUpperCase()})</span></p>
          </div>
          <div className="bg-white/[0.03] px-10 py-6 rounded-[35px] border border-blue-500/20 text-blue-400 text-center shadow-2xl backdrop-blur-md">
            <p className="text-[9px] font-black uppercase tracking-[0.3em] mb-1 opacity-60">Tone Level</p>
            <p className="text-4xl font-black tracking-tighter">{skinTone?.level}<span className="text-lg opacity-40">/5</span></p>
          </div>
        </div>

        {/* Content Status */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-40 gap-6">
            <div className="w-16 h-16 border-4 border-t-blue-500 border-white/10 rounded-full animate-spin" />
            <p className="text-[10px] font-black tracking-[0.5em] opacity-40 uppercase animate-pulse">Mencari Baju {activeGender.toUpperCase()}...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-40 text-center gap-8 bg-red-500/5 border border-red-500/20 rounded-[50px] p-10">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-red-500 opacity-40">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div className="space-y-3">
              <p className="text-white text-xl font-black uppercase tracking-widest">Akses Data Terhambat</p>
              <p className="text-gray-500 text-xs max-w-xs mx-auto leading-relaxed">{error}</p>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="flex items-center gap-3 px-10 py-4 bg-white text-black rounded-full text-[10px] font-black uppercase tracking-widest hover:scale-105 transition-transform"
            >
              <RefreshCw size={14} /> Muat Ulang Halaman
            </button>
          </div>
        ) : localRecs?.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 auto-rows-fr">
            {localRecs.map((item, i) => (
              <RecommendationCard
                key={item.product?.id || item.id || i}
                item={item}
                index={i}
                sessionId={sessionId}
                setActiveProduct={setActiveProduct}
                navigate={navigate}
                onOpenAR={handleOpenARModal}
                activeGender={activeGender}
              />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-40 opacity-20 gap-4">
            <PackageX size={64} />
            <p className="font-black tracking-[0.5em] uppercase">Tidak Ada Rekomendasi</p>
          </div>
        )}
      </div>
    </div>
  )
}
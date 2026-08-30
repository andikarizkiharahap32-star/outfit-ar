import React, { useEffect, useRef, useState, useCallback, Suspense } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft, MagnifyingGlassMinus, ArrowUp, ArrowDown, MagnifyingGlassPlus,
  Question, Camera, ArrowsClockwise, DownloadSimple, X, Pulse,
  CaretLeft, CaretRight, HandsClapping, Desktop
} from '@phosphor-icons/react';
import { Canvas, useFrame } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';

// ─── Konstanta MediaPipe ──────────────────────────────────────────────────────
const MP_LEFT_SHOULDER   = 11;
const MP_RIGHT_SHOULDER  = 12;
const MP_LEFT_ELBOW      = 13;
const MP_RIGHT_ELBOW     = 14;
const MP_LEFT_WRIST      = 15;
const MP_RIGHT_WRIST     = 16;
const MP_LEFT_HIP        = 23;
const MP_RIGHT_HIP       = 24;

// ─── Tuning AR Posisi Langsung (tanpa bone/skeleton) ────────────────────────
// Model GLB tidak punya skeleton → tracking posisi/rotasi scene langsung dari landmark
const EMA_ALPHA    = 0.25;  // Smoothing EMA untuk semua tracking (0=tidak bergerak, 1=mentah)
const STABLE_MIN   = 1;     // frame valid sebelum model mulai muncul (dikecilkan agar HP tidak delay)
// FOV kamera Three.js: camera.position.z=4.5, fov=60
// Mapping: titik MP (0..1) → ruang world Three.js
// Faktor X dan Y dikalibrasi dari screenshot user
const MP_TO_WORLD_X = -3.2;  // negatif karena kamera di-mirror
const MP_TO_WORLD_Y =  3.8;  // tinggi ruang world
// Offset Y agar baju turun ke BADAN bukan di leher (dalam unit world)
const COLLAR_OFFSET = 0.0;   // 0=baju mulai dari titik bahu, positif=turun lebih rendah

// ─── Klasifikasi Produk → Model 3D ───────────────────────────────────────────
//
// ATURAN:
//  1. Celana / Rok (bawahan) → TIDAK ada 3D, tampil pesan "AR hanya untuk atasan"
//  2. Kaos / Hoodie (pria)   → PriaShort.glb
//  3. Kemeja / Sweater / Jaket / Blazer (pria) → PriaPolo.glb
//  4. Semua atasan wanita    → Wanita.glb
//  5. Semua wanitahijab      → WanitaBerhijab.glb

// Bawahan → tidak ada 3D AR
const BOTTOM_WEAR_KEYWORDS = [
  'celana', 'rok', 'pants', 'skirt', 'legging', 'jeans',
  'shorts', 'chino', 'sarung', 'kain',
];

// Pria: atasan lengan pendek / kaos
const PRIA_KAOS_KEYWORDS = [
  'kaos', 't-shirt', 'tshirt', 't shirt', 'hoodie',
  'tanktop', 'tank top', 'singlet', 'polo shirt',
];

// Pria: atasan berkerah / lengan panjang
const PRIA_POLO_KEYWORDS = [
  'kemeja', 'sweater', 'sweatshirt', 'jaket', 'jacket',
  'blazer', 'cardigan', 'vest', 'jas', 'bomber',
  'windbreaker', 'parka', 'coat', 'rompi', 'outer',
];

// Wanita: semua atasan (bukan rok)
const WANITA_TOP_KEYWORDS = [
  'blouse', 'dress', 'kaos', 'cardigan', 'outer',
  'tunik', 'kebaya', 'top', 'kemeja', 'jaket',
  'sweater', 'blazer', 'atasan', 'baju',
];

// WanitaHijab: semua atasan
const HIJAB_TOP_KEYWORDS = [
  'abaya', 'gamis', 'tunik', 'outer', 'blouse',
  'kaftan', 'jubah', 'kimono', 'coat', 'cardigan',
  'dress', 'baju', 'atasan', 'kemeja',
];

/**
 * Cek apakah produk adalah BAWAHAN (celana/rok) → tidak ada model 3D
 */
function isBottomWear(productName) {
  const name = String(productName || '').toLowerCase();
  return BOTTOM_WEAR_KEYWORDS.some(kw => name.includes(kw));
}

/**
 * Kembalikan daftar model berdasarkan gender + nama produk.
 * Return [] jika bawahan (tidak ada AR).
 * Urutan pertama = model utama yang langsung tampil.
 */
function getAvailableModels(gender, productName) {
  const g    = String(gender || '').toLowerCase().trim();
  const name = String(productName || '').toLowerCase();

  // Bawahan → tidak ada model
  if (isBottomWear(name)) return [];

  // ── PRIA ──────────────────────────────────────────────────────────────
  if (g === 'pria') {
    const isKaos = PRIA_KAOS_KEYWORDS.some(kw => name.includes(kw));
    if (isKaos) {
      // Kaos/Hoodie → PriaShort utama, PriaPolo alternatif
      return ['/models/PriaShort.glb', '/models/PriaPolo.glb'];
    }
    // Kemeja/Sweater/Jaket → PriaPolo utama, PriaShort alternatif
    return ['/models/PriaPolo.glb', '/models/PriaShort.glb'];
  }

  // ── WANITA ────────────────────────────────────────────────────────────
  if (g === 'wanita') {
    // Rok sudah ter-exclude oleh isBottomWear di atas
    // Semua atasan wanita → Wanita.glb
    return ['/models/Wanita.glb'];
  }

  // ── WANITA HIJAB ──────────────────────────────────────────────────────
  if (g === 'wanitahijab') {
    return ['/models/WanitaBerhijab.glb'];
  }

  // ── DEFAULT (unisex / tidak dikenali) ─────────────────────────────────
  return ['/models/PriaPolo.glb'];
}


// ─── GLB Cache: Preload di background saat JS pertama kali dimuat ────────────
// Model di-download ke ArrayBuffer dan di-cache agar AR langsung muncul tanpa loading
const glbCache = new Map(); // url -> ArrayBuffer
const glbLoading = new Map(); // url -> Promise (hindari duplikat download)

const ALL_MODELS = [
  '/models/PriaShort.glb',
  '/models/PriaPolo.glb',
  '/models/Wanita.glb',
  '/models/WanitaBerhijab.glb',
];

function preloadGLBInBackground(url) {
  if (glbCache.has(url) || glbLoading.has(url)) return;
  const p = fetch(url)
    .then(r => r.arrayBuffer())
    .then(buf => { glbCache.set(url, buf); glbLoading.delete(url); })
    .catch(() => { glbLoading.delete(url); });
  glbLoading.set(url, p);
}

// Mulai preload SEMUA model segera saat modul JS dimuat
// Saat user masuk AR, file sudah ada di cache
ALL_MODELS.forEach(preloadGLBInBackground);

// ─── Konversi nama warna / hex ke THREE.Color ─────────────────────────────────
function parseProductColor(colorStr) {
  if (!colorStr) return new THREE.Color('#6B7ADE');
  const str = String(colorStr).toLowerCase().trim();

  if (str.startsWith('#') && (str.length === 4 || str.length === 7)) {
    try { return new THREE.Color(str); } catch (_) {}
  }

  const colorMap = {
    'putih': '#F5F5F2', 'white': '#F5F5F2',
    'hitam': '#1C1C1E', 'black': '#1C1C1E',
    'merah': '#C0392B', 'red': '#C0392B',
    'merah tua': '#922B21', 'maroon': '#922B21',
    'biru': '#2980B9', 'blue': '#2980B9',
    'biru muda': '#5DADE2', 'light blue': '#5DADE2',
    'biru tua': '#1A5276', 'navy': '#1A3A6E', 'biru navy': '#1A3A6E',
    'hijau': '#1E8449', 'green': '#1E8449',
    'hijau muda': '#58D68D', 'lime': '#82E0AA',
    'hijau tua': '#196F3D', 'olive': '#7D6608',
    'kuning': '#D4AC0D', 'yellow': '#D4AC0D',
    'orange': '#CA6F1E', 'jingga': '#CA6F1E',
    'ungu': '#7D3C98', 'purple': '#7D3C98', 'violet': '#8E44AD',
    'pink': '#F1948A', 'merah muda': '#F1948A', 'salmon': '#E59866',
    'abu': '#7F8C8D', 'abu-abu': '#7F8C8D', 'grey': '#7F8C8D', 'gray': '#7F8C8D',
    'coklat': '#6E2F1A', 'brown': '#6E2F1A', 'coklat muda': '#A04000',
    'krem': '#F0E6D3', 'cream': '#F0E6D3', 'beige': '#F5F0DC',
    'tosca': '#17A589', 'teal': '#148F77',
    'gold': '#D4AC0D', 'emas': '#D4AC0D',
    'silver': '#BFC9CA',
    'magenta': '#C0392B', 'fuchsia': '#C0392B',
    'lavender': '#BB8FCE', 'lilac': '#D7BDE2',
    'mustard': '#B7950B', 'kuning mustard': '#B7950B',
    'nude': '#E8D5C4', 'mocca': '#7B5E57',
  };

  for (const [key, hex] of Object.entries(colorMap)) {
    if (str.includes(key)) {
      try { return new THREE.Color(hex); } catch (_) {}
    }
  }
  try { return new THREE.Color(str); } catch (_) {}
  return new THREE.Color('#6B7ADE');
}

// ─── EMA Filter ──────────────────────────────────────────────────────────────
function emaVal(prev, next, alpha) {
  if (prev === null || prev === undefined) return next;
  return prev + alpha * (next - prev);
}

function emaLM(prev, next, alpha) {
  if (!prev) return { ...next };
  return {
    x: emaVal(prev.x, next.x, alpha),
    y: emaVal(prev.y, next.y, alpha),
    z: emaVal(prev.z, next.z, alpha),
    visibility: emaVal(prev.visibility, next.visibility, alpha),
  };
}

// ─── Komponen model 3D: Fully Imperative (Safari-safe, no React state) ───────
// useGLTF + setGltfScene gagal di Safari karena R3F reconciler issue.
// Solusi: load GLB lalu langsung group.add(scene) secara imperatif Three.js.
function RiggedCloth({ modelPath, poseLandmarksRef, productColor, userModelScale, userModelY }) {
  const groupRef    = useRef();
  const smoothPos   = useRef({ x: 0, y: 0 });
  const smoothScale = useRef(1.35);
  const smoothRot   = useRef(0.0);
  const loadedRef   = useRef(false); // sudah load atau belum

  // ── Load GLB & langsung add ke Three.js group (imperatif, tanpa setState) ──
  useEffect(() => {
    let cancelled = false;
    loadedRef.current = false;

    // Tunggu sedikit agar groupRef.current sudah terpasang
    const timer = setTimeout(() => {
      const group = groupRef.current;
      if (!group || cancelled) return;

      const doLoad = async () => {
        try {
          const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js')
            .catch(() => import('three/examples/jsm/loaders/GLTFLoader.js'));
          const loader = new GLTFLoader();

          // Fetch + ArrayBuffer (browser HTTP cache akan serve ini cepat jika sudah pernah didownload)
          const buf = await fetch(modelPath).then(r => {
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.arrayBuffer();
          });
          if (cancelled) return;

          loader.parse(buf, '', (gltf) => {
            if (cancelled) return;
            const currentGroup = groupRef.current;
            if (!currentGroup) return;

            // Terapkan warna produk
            const color = parseProductColor(productColor);
            gltf.scene.traverse(child => {
              if (child.isMesh || child.isSkinnedMesh) {
                const apply = (mat) => {
                  if (!mat) return mat;
                  const m = mat.clone();
                  m.color = color; m.roughness = 0.72; m.metalness = 0.04;
                  m.needsUpdate = true; return m;
                };
                child.material = Array.isArray(child.material)
                  ? child.material.map(apply) : apply(child.material);
              }
            });

            // Normalisasi posisi/skala GLB (beberapa GLB punya offset aneh)
            gltf.scene.position.set(0, 0, 0);
            gltf.scene.rotation.set(0, 0, 0);
            gltf.scene.scale.set(1, 1, 1);

            // IMPERATIF: langsung tambah ke Three.js group tanpa setState/re-render
            // Hapus anak lama dulu (jika ada model sebelumnya)
            while (currentGroup.children.length > 0) {
              currentGroup.remove(currentGroup.children[0]);
            }
            currentGroup.add(gltf.scene);
            currentGroup.visible = true;
            loadedRef.current = true;

          }, (err) => {
            console.error('[AR] GLB parse error:', err);
          });

        } catch (err) {
          console.error('[AR] Load error:', err);
        }
      };

      doLoad();
    }, 100); // 100ms delay agar groupRef.current sudah terpasang

    return () => {
      cancelled = true;
      clearTimeout(timer);
      // Bersihkan Three.js group saat unmount
      const g = groupRef.current;
      if (g) while (g.children.length > 0) g.remove(g.children[0]);
      loadedRef.current = false;
    };
  }, [modelPath, productColor]);

  // ── Tracking pose ─────────────────────────────────────────────────────
  useFrame(() => {
    const target = groupRef.current;
    if (!target) return;

    const safeY     = typeof userModelY     === 'number' && !isNaN(userModelY)     ? userModelY     : -1.2;
    const safeScale = typeof userModelScale === 'number' && !isNaN(userModelScale) ? userModelScale : 1.35;
    const lm = poseLandmarksRef.current;

    target.visible = true;

    if (!lm || lm.length < 17) {
      target.position.set(0, safeY, 0);
      target.scale.setScalar(smoothScale.current);
      target.rotation.z = 0;
      return;
    }

    const lSh = lm[MP_LEFT_SHOULDER];
    const rSh = lm[MP_RIGHT_SHOULDER];
    const vis  = p => (p?.visibility ?? 0);

    if (!lSh || !rSh || (vis(lSh) < 0.1 && vis(rSh) < 0.1)) {
      target.position.set(0, safeY, 0);
      target.scale.setScalar(smoothScale.current);
      return;
    }

    const mpCX = (lSh.x + rSh.x) / 2;
    const mpCY = (lSh.y + rSh.y) / 2;
    const dxSh = lSh.x - rSh.x;
    const dySh = lSh.y - rSh.y;
    const shoulderWidthMP = Math.sqrt(dxSh * dxSh + dySh * dySh);

    const halfH = 4.5 * Math.tan((60 * Math.PI / 180) / 2);
    const halfW = halfH * (window.innerWidth / window.innerHeight);
    const worldX = -(mpCX - 0.5) * halfW * 2;
    const worldY = (0.5 - mpCY) * halfH * 2;

    let targetScale = smoothScale.current;
    let targetTilt  = smoothRot.current;

    if (Math.abs(dxSh) > 0.12) {
      const sw = shoulderWidthMP * halfW * 2;
      targetScale = Math.max(0.4, Math.min(3.5, (sw * 1.35) + (safeScale - 1.35)));
      const rawTilt = Math.atan2(rSh.y - lSh.y, lSh.x - rSh.x);
      targetTilt = Math.max(-0.35, Math.min(0.35, rawTilt));
    }

    smoothPos.current.x = emaVal(smoothPos.current.x, worldX,      EMA_ALPHA);
    smoothPos.current.y = emaVal(smoothPos.current.y, worldY,      EMA_ALPHA);
    smoothScale.current = emaVal(smoothScale.current, targetScale, EMA_ALPHA * 0.5);
    smoothRot.current   = emaVal(smoothRot.current,   targetTilt,  EMA_ALPHA);

    target.position.x = smoothPos.current.x;
    target.position.y = smoothPos.current.y + safeY;
    target.position.z = 0;
    target.scale.setScalar(smoothScale.current);
    target.rotation.z = smoothRot.current;
  });

  // Selalu render group kosong — model ditambah secara imperatif oleh useEffect
  return <group ref={groupRef} />;
}

// ─── Scene Three.js ───────────────────────────────────────────────────────────
function ARScene({ modelPath, scale, position, poseLandmarksRef, productColor }) {
  return (
    <>
      <ambientLight intensity={2.0} />
      <directionalLight position={[0, 4, 4]}   intensity={2.2} />
      <directionalLight position={[-3, 2, 2]}  intensity={0.8} color="#cce4ff" />
      <pointLight       position={[0, 1, 3]}   intensity={1.0} />
      <RiggedCloth
        key={modelPath}
        modelPath={modelPath}
        userModelScale={scale}
        userModelY={position ? position[1] : -1.8}
        poseLandmarksRef={poseLandmarksRef}
        productColor={productColor}
      />
    </>
  );
}


// ─── Config Backend ───────────────────────────────────────────────────────────
// Gunakan URL relatif agar semua request lewat Vite proxy
// HP (Cloudflare) dan Laptop (localhost) bekerja tanpa CORS issue
const NGROK_BACKEND_URL = import.meta.env.VITE_API_URL || '';
const NGROK_HEADERS = {
  'ngrok-skip-browser-warning': '69420',
  Accept: 'application/json',
};

function readStoredProduct(productId) {
  const keys = ['outfitar_selected_product', 'outfitar_active_product', 'selectedProduct', 'activeProduct'];
  for (const storage of [sessionStorage, localStorage]) {
    for (const key of keys) {
      try {
        const raw = storage.getItem(key);
        if (!raw) continue;
        const parsed = JSON.parse(raw);
        const storedId = String(parsed?.id || parsed?.product_id || parsed?.productId || '');
        if (!productId || storedId === String(productId)) return parsed;
      } catch (_) {}
    }
  }
  return null;
}

// ─── Komponen Utama ───────────────────────────────────────────────────────────
export default function StreamHP() {
  const params   = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const productId = params.id || params.productId || params.sessionId || params.product_id || '';

  const videoRef        = useRef(null);
  const glCanvasRef     = useRef(null);
  const streamRef       = useRef(null);
  const poseLandmarksRef = useRef(null);

  const initialProduct = location.state?.selectedProduct || readStoredProduct(productId) || null;

  const [selectedProduct, setSelectedProduct] = useState(initialProduct);
  const [cameraFacing,   setCameraFacing]   = useState('user');
  const [cameraStatus,   setCameraStatus]   = useState('idle');
  const [cameraError,    setCameraError]    = useState('');
  const [poseReady,      setPoseReady]      = useState(false);

  // Model scale & position (dikalibrasi: origin model di kaki, baju di Y≈1.2–1.5)
  const [modelScale, setModelScale] = useState(1.35); // Diperkecil sedikit
  const [modelY,     setModelY]     = useState(-1.2); // Dinaikkan lebih tinggi
  const [modelX,     setModelX]     = useState(0);

  // Pilihan model (untuk produk pria ada 2 model: Polo & Short)
  const [modelIndex, setModelIndex] = useState(0);

  const [showHelp,    setShowHelp]    = useState(false);
  const [captureUrl,  setCaptureUrl]  = useState('');

  // ─── Turunkan data produk ──────────────────────────────────────────
  const productGender = selectedProduct?.gender || selectedProduct?.product?.gender || '';
  const productColor  = selectedProduct?.color  || selectedProduct?.product?.color  || '';
  const productName   = selectedProduct?.name   || selectedProduct?.title           || `Produk #${productId || '-'}`;

  // Daftar model berdasarkan gender DAN tipe produk (kaos vs kemeja/polo)
  const availableModels = getAvailableModels(productGender, productName);
  // Index yang aman — hindari modulo 0 jika availableModels kosong
  const safeIndex  = availableModels.length > 0 ? modelIndex % availableModels.length : 0;
  const modelPath  = availableModels[safeIndex] ?? null;  // null jika bottom wear / no product

  // Preview warna untuk UI
  const colorCSS = parseProductColor(productColor).getStyle();

  // ─── Fetch produk dari backend jika belum tersedia ─────────────────
  useEffect(() => {
    if (selectedProduct || !productId) return;
    let cancelled = false;
    // Gunakan path relatif /api/v1 agar lewat Vite proxy (bekerja di HP & laptop)
    fetch(`/api/v1/products/${productId}`, { headers: NGROK_HEADERS })
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        if (cancelled || !data) return;
        const p = data.data || data.product || data;
        setSelectedProduct(p);
        try { localStorage.setItem('outfitar_selected_product', JSON.stringify(p)); } catch (_) {}
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [productId, selectedProduct]);

  // ─── Reset model index setiap kali produk berubah (gender ATAU nama) ────
  useEffect(() => { setModelIndex(0); }, [productGender, productName]);

  // ─── Inisialisasi MediaPipe Pose ───────────────────────────────────
  const initMediaPipe = useCallback(async (videoEl) => {
    try {
      // @mediapipe/pose bisa export sebagai CJS (default) atau ESM (named)
      // Gunakan fallback chain untuk handle keduanya
      const poseModule = await import('@mediapipe/pose');
      const Pose       = poseModule.Pose ?? poseModule.default?.Pose ?? poseModule.default ?? window.Pose;
      const camModule  = await import('@mediapipe/camera_utils');
      const Camera     = camModule.Camera ?? camModule.default?.Camera ?? camModule.default ?? window.Camera;

      if (typeof Pose !== 'function') throw new Error('MediaPipe Pose tidak tersedia');
      if (typeof Camera !== 'function') throw new Error('MediaPipe Camera tidak tersedia');

      const pose = new Pose({
        locateFile: f => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${f}`,
      });
      pose.setOptions({
        modelComplexity:        0,  // Diubah dari 1 ke 0 untuk FPS maksimal
        smoothLandmarks:        true,
        enableSegmentation:     false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence:  0.4, // Sedikit lebih rendah agar tracking tidak putus saat gerak cepat
      });
      pose.onResults(results => {
        poseLandmarksRef.current = results.poseLandmarks ?? null;
        setPoseReady(!!results.poseLandmarks);
      });

      const cam = new Camera(videoEl, {
        onFrame: async () => {
          if (videoEl.readyState >= 2) await pose.send({ image: videoEl });
        },
        width: 640, height: 480,
      });
      await cam.start();
    } catch (err) {
      console.warn('[AR] MediaPipe gagal:', err.message);
    }
  }, []);

  // ─── Mulai kamera ──────────────────────────────────────────────────
  const startCamera = useCallback(async (facing) => {
    const facingMode = facing || cameraFacing;
    setCameraStatus('requesting');
    setCameraError('');
    setPoseReady(false);

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: { ideal: facingMode }, width: { ideal: 640 }, height: { ideal: 480 } },
      });
      streamRef.current = stream;

      const video = videoRef.current;
      if (video) {
        video.srcObject = stream;
        video.onloadedmetadata = () => video.play().catch(() => {});
      }

      setCameraStatus('ready');

      // Delay 2 detik sebelum mulai MediaPipe agar kamera stabil
      setTimeout(() => initMediaPipe(video), 2000);
    } catch (err) {
      setCameraStatus('error');
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraError('Izin kamera ditolak. Buka Pengaturan → Safari/Chrome → Kamera → Izinkan.');
      } else if (err.name === 'NotFoundError') {
        setCameraError('Kamera tidak ditemukan di perangkat ini.');
      } else {
        setCameraError(`Kamera tidak bisa dibuka: ${err.message}`);
      }
    }
  }, [cameraFacing, initMediaPipe]);

  const switchCamera = () => {
    const next = cameraFacing === 'user' ? 'environment' : 'user';
    setCameraFacing(next);
    startCamera(next);
  };

  // Ganti antara model (jika gender pria punya 2: Polo & Short)
  const cycleModel = (dir) => {
    setModelIndex(i => {
      const len  = availableModels.length;
      return ((i + dir) % len + len) % len;
    });
  };

  useEffect(() => {
    return () => {
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
    };
  }, []);

  // ─── Capture foto ──────────────────────────────────────────────────
  const capturePhoto = () => {
    const video = videoRef.current;
    if (!video) return;

    const aspect = window.innerWidth / window.innerHeight;
    const videoWidth = video.videoWidth || 640;
    const videoHeight = video.videoHeight || 480;
    const videoAspect = videoWidth / videoHeight;

    let sx = 0, sy = 0, sw = videoWidth, sh = videoHeight;
    if (videoAspect > aspect) {
      sw = videoHeight * aspect;
      sx = (videoWidth - sw) / 2;
    } else {
      sh = videoWidth / aspect;
      sy = (videoHeight - sh) / 2;
    }

    const destHeight = videoHeight;
    const destWidth = videoHeight * aspect;

    const cap = document.createElement('canvas');
    cap.width  = destWidth;
    cap.height = destHeight;
    const ctx  = cap.getContext('2d');

    // 1. Draw video feed (mirrored if cameraFacing === 'user')
    if (cameraFacing === 'user') {
      ctx.translate(destWidth, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(video, sx, sy, sw, sh, 0, 0, destWidth, destHeight);

    // 2. Draw WebGL canvas directly on top (unmirrored, reset transform first)
    if (glCanvasRef.current) {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(glCanvasRef.current, 0, 0, destWidth, destHeight);
    }

    setCaptureUrl(cap.toDataURL('image/jpeg', 0.92));
  };

  const resetPosition = () => { setModelX(0); setModelY(-1.2); setModelScale(1.35); };

  // ─── Model label yang sedang aktif ────────────────────────────────
  const modelLabel = (() => {
    if (!modelPath) return '🚫 AR Tidak Tersedia';
    if (modelPath.includes('PriaShort'))     return '👕 Kaos / T-Shirt';
    if (modelPath.includes('PriaPolo'))      return '👔 Kemeja / Polo';
    if (modelPath.includes('WanitaBerhijab')) return '🧕 Hijab Style';
    if (modelPath.includes('Wanita'))        return '👗 Wanita';
    return modelPath.split('/').pop().replace('.glb', '').replace('%20', ' ');
  })();

  // ─── CSS helper untuk tombol kontrol ─────────────────────────────
  const btnStyle = {
    height: 50, display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(14px)',
    border: '1px solid rgba(255,255,255,0.2)', color: '#fff',
    borderRadius: 14, cursor: 'pointer',
  };

  // ─── Render ───────────────────────────────────────────────────────
  return (
    <div style={{ position: 'fixed', inset: 0, background: '#000', overflow: 'hidden', fontFamily: 'system-ui,sans-serif' }}>

      {/* ── Layer 1: Video kamera ── */}
      <video
        ref={videoRef}
        autoPlay playsInline muted
        style={{
          position: 'absolute', inset: 0, width: '100%', height: '100%',
          objectFit: 'cover',
          transform: cameraFacing === 'user' ? 'scaleX(-1)' : 'none',
          zIndex: 1,
          display: cameraStatus === 'ready' ? 'block' : 'none',
        }}
      />

      {/* ── Layer 2: Three.js canvas TRANSPARAN ── */}
      {cameraStatus === 'ready' && availableModels.length > 0 && (
        <Canvas
          style={{
            position: 'absolute', inset: 0, width: '100%', height: '100%',
            zIndex: 2, background: 'transparent',
          }}
          camera={{ position: [0, 0, 4.5], fov: 60 }}
          gl={{
            alpha: true,
            premultipliedAlpha: false,
            antialias: true,
            preserveDrawingBuffer: true,
          }}
          onCreated={({ gl }) => {
            gl.setClearColor(0x000000, 0);
            glCanvasRef.current = gl.domElement;
          }}
        >
          <ARScene
            modelPath={modelPath}
            scale={modelScale}
            position={[modelX, modelY, 0]}
            poseLandmarksRef={poseLandmarksRef}
            productColor={productColor}
          />
        </Canvas>
      )}

      {/* ── Layer 2b: Pesan bawahan (celana/rok) — tidak ada AR 3D ── */}
      {cameraStatus === 'ready' && availableModels.length === 0 && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 2,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          gap: 16, pointerEvents: 'none',
        }}>
          <div style={{
            background: 'rgba(0,0,0,0.72)', backdropFilter: 'blur(20px)',
            border: '1px solid rgba(255,200,100,0.35)', borderRadius: 20,
            padding: '24px 32px', maxWidth: 300, textAlign: 'center',
          }}>
            <div style={{ fontSize: 48, marginBottom: 8 }}>👖</div>
            <div style={{ color: '#fbbf24', fontWeight: 800, fontSize: 15, marginBottom: 6 }}>
              AR Hanya untuk Atasan
            </div>
            <div style={{ color: 'rgba(255,255,255,0.65)', fontSize: 13, lineHeight: 1.6 }}>
              Produk <strong style={{ color: '#fff' }}>{productName}</strong> adalah bawahan.
              Pilih kaos, kemeja, sweater, atau jaket untuk mencoba model 3D.
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════
          LAYAR IDLE — tap untuk aktifkan kamera
          ══════════════════════════════════════════════════ */}
      {cameraStatus === 'idle' && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 20,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 24,
          background: '#050505',
          color: '#fff', padding: 32, textAlign: 'center',
        }}>
          <div style={{
            width: 80, height: 80, borderRadius: '50%', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 8
          }}>
            <Desktop size={40} weight="light" className="text-white/50" />
          </div>
          
          <div>
            <h2 style={{ fontSize: 28, fontWeight: 500, margin: 0, letterSpacing: '0.05em' }}>Virtual Try-On 3D</h2>
            <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13, maxWidth: 280, lineHeight: 1.6, margin: '8px auto 0', fontWeight: 300 }}>
              Simulasi pakaian real-time menggunakan deteksi postur tubuh.
            </p>
          </div>

          {/* Info produk + warna */}
          <div style={{
            background: 'rgba(255,255,255,0.03)', borderRadius: 24, padding: '20px 24px',
            border: '1px solid rgba(255,255,255,0.08)', display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 300, width: '100%',
            backdropFilter: 'blur(12px)'
          }}>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', fontWeight: 600, letterSpacing: '0.15em', textTransform: 'uppercase' }}>
              Memuat Model
            </div>
            <div style={{ fontSize: 16, fontWeight: 500, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {productName}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4 }}>
              <div style={{ width: 16, height: 16, borderRadius: '50%', background: colorCSS, border: '1px solid rgba(255,255,255,0.2)', flexShrink: 0 }} />
              <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', fontWeight: 300 }}>
                {productColor || 'Default'} · {productGender || 'Unisex'}
              </span>
            </div>
          </div>

          <button onClick={() => startCamera()} className="btn-premium" style={{
            background: '#fff',
            color: '#000', border: 'none', borderRadius: 50,
            padding: '16px 40px', fontSize: 13, fontWeight: 600,
            letterSpacing: '0.05em', cursor: 'pointer',
            marginTop: 8
          }}>
            AKTIFKAN KAMERA
          </button>

          <button onClick={() => navigate(-1)} style={{
            background: 'transparent', color: 'rgba(255,255,255,0.4)',
            border: 'none', borderRadius: 50,
            padding: '12px 24px', fontSize: 12, cursor: 'pointer',
            fontWeight: 500
          }}>Kembali ke Katalog</button>
        </div>
      )}

      {/* ══════════════════════════════════════════════════
          LOADING
          ══════════════════════════════════════════════════ */}
      {cameraStatus === 'requesting' && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 20,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20,
          background: 'rgba(5,5,5,0.95)', backdropFilter: 'blur(24px)', color: '#fff',
        }}>
          <div style={{
            width: 48, height: 48, border: '2px solid rgba(255,255,255,0.1)',
            borderTopColor: '#fff', borderRadius: '50%',
            animation: 'ar-spin 0.8s linear infinite',
          }} />
          <p style={{ fontSize: 11, letterSpacing: '0.2em', textTransform: 'uppercase', opacity: 0.5, margin: 0, fontWeight: 500 }}>
            Menginisialisasi Kamera
          </p>
          <style>{`@keyframes ar-spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* ══════════════════════════════════════════════════
          ERROR
          ══════════════════════════════════════════════════ */}
      {cameraStatus === 'error' && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 30,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 24,
          background: '#050505', color: '#fff', padding: 32, textAlign: 'center',
        }}>
          <div style={{ width: 80, height: 80, borderRadius: '50%', background: 'rgba(239,68,68,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ef4444' }}>
            <Pulse size={40} weight="light" />
          </div>
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 500, margin: 0, letterSpacing: '0.05em' }}>Kamera Gagal Diakses</h2>
            <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13, maxWidth: 300, lineHeight: 1.6, margin: '8px auto 0', fontWeight: 300 }}>
              {cameraError}
            </p>
          </div>
          <button onClick={() => startCamera()} className="btn-premium" style={{
            background: '#fff',
            color: '#000', border: 'none', borderRadius: 50,
            padding: '14px 32px', fontSize: 13, fontWeight: 600, cursor: 'pointer', marginTop: 8
          }}>Coba Lagi</button>
          <button onClick={() => navigate(-1)} style={{
            background: 'transparent', color: 'rgba(255,255,255,0.4)',
            border: 'none', borderRadius: 50,
            padding: '12px 24px', fontSize: 12, cursor: 'pointer', fontWeight: 500
          }}>Kembali</button>
        </div>
      )}

      {/* ══════════════════════════════════════════════════
          HUD — saat kamera aktif
          ══════════════════════════════════════════════════ */}
      {cameraStatus === 'ready' && (
        <>
          {/* ─ Header ─ */}
          <div style={{
            position: 'absolute', top: 'max(16px,env(safe-area-inset-top))',
            left: 16, right: 16, zIndex: 10, display: 'flex', alignItems: 'center', gap: 12,
          }}>
            {/* Tombol kembali */}
            <button onClick={() => navigate(-1)} style={{
              background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(24px)',
              border: '1px solid rgba(255,255,255,0.1)', color: '#fff',
              borderRadius: 50, padding: '12px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <ArrowLeft size={18} weight="light" />
            </button>

            {/* Info produk */}
            <div style={{
              flex: 1, background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(24px)',
              border: '1px solid rgba(255,255,255,0.1)', borderRadius: 50, padding: '8px 16px',
              display: 'flex', alignItems: 'center', gap: 12, overflow: 'hidden',
            }}>
              <div style={{
                width: 10, height: 10, borderRadius: '50%',
                background: colorCSS, flexShrink: 0,
                boxShadow: `0 0 10px ${colorCSS}`
              }} />
              <div style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column', gap: 2 }}>
                <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)', fontWeight: 600, letterSpacing: '0.15em', textTransform: 'uppercase' }}>
                  {modelLabel}
                </div>
                <div style={{ fontSize: 13, color: '#fff', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {productName}
                </div>
              </div>
            </div>

            {/* Indikator pose */}
            <div style={{
              background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(24px)',
              border: `1px solid ${poseReady ? 'rgba(74,222,128,0.2)' : 'rgba(248,113,113,0.2)'}`,
              borderRadius: 50, padding: '8px 16px',
              display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0,
              height: 42
            }}>
              <Pulse size={16} weight={poseReady ? "fill" : "light"} style={{ color: poseReady ? '#4ade80' : '#f87171' }} />
              <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.05em', color: poseReady ? '#4ade80' : '#f87171' }}>
                {poseReady ? 'TERDETEKSI' : 'MEMINDAI'}
              </span>
            </div>
          </div>

          {/* ─ Model switcher (muncul jika ada >1 model untuk gender ini) ─ */}
          {availableModels.length > 1 && (
            <div style={{
              position: 'absolute', top: 'calc(max(16px,env(safe-area-inset-top)) + 64px)',
              left: '50%', transform: 'translateX(-50%)', zIndex: 10,
              display: 'flex', alignItems: 'center', gap: 16,
              background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(24px)',
              border: '1px solid rgba(255,255,255,0.1)', borderRadius: 50, padding: '6px 16px',
            }}>
              <button onClick={() => cycleModel(-1)} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', padding: 4, display: 'flex', opacity: 0.7 }}>
                <CaretLeft size={16} weight="bold" />
              </button>
              <span style={{ fontSize: 10, fontWeight: 600, color: '#fff', letterSpacing: '0.1em' }}>
                {modelLabel}
              </span>
              <button onClick={() => cycleModel(1)} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', padding: 4, display: 'flex', opacity: 0.7 }}>
                <CaretRight size={16} weight="bold" />
              </button>
            </div>
          )}

          {/* ─ Kontrol bawah ─ */}
          <div style={{
            position: 'absolute', bottom: 'max(24px,env(safe-area-inset-bottom))',
            left: 24, right: 24, zIndex: 10,
          }}>
            {showHelp && (
              <div style={{
                marginBottom: 16, background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(24px)',
                border: '1px solid rgba(255,255,255,0.1)', borderRadius: 24,
                padding: '20px', fontSize: 12, color: 'rgba(255,255,255,0.7)', lineHeight: 1.7,
                textAlign: 'center'
              }}>
                <div style={{ fontWeight: 500, color: '#fff', marginBottom: 8, fontSize: 13 }}>Cara Penggunaan</div>
                Gunakan panah untuk menyesuaikan posisi baju.<br />
                Gunakan kaca pembesar untuk mengatur ukuran.<br />
                Pakaian akan otomatis mengikuti postur Anda.
              </div>
            )}

            {/* Baris tombol kontrol posisi & skala */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 10, marginBottom: 16 }}>
              {[
                { icon: <MagnifyingGlassMinus size={22} weight="light" />, fn: () => setModelScale(v => Math.max(0.4, +(v - 0.2).toFixed(1))) },
                { icon: <ArrowUp   size={22} weight="light" />, fn: () => setModelY(v => +(v + 0.3).toFixed(2)) },
                { icon: <ArrowDown size={22} weight="light" />, fn: () => setModelY(v => +(v - 0.3).toFixed(2)) },
                { icon: <MagnifyingGlassPlus    size={22} weight="light" />, fn: () => setModelScale(v => Math.min(5.0, +(v + 0.2).toFixed(1))) },
                { icon: <Question size={22} weight="light" />, fn: () => setShowHelp(v => !v) },
              ].map((b, i) => (
                <button key={i} onClick={b.fn} style={{
                  height: 48, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(24px)',
                  border: '1px solid rgba(255,255,255,0.1)', color: '#fff',
                  borderRadius: 16, cursor: 'pointer', transition: 'background 0.2s'
                }}>{b.icon}</button>
              ))}
            </div>

            {/* Baris bawah: kamera ← shutter → reset */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 84px 1fr', gap: 16, alignItems: 'center' }}>
              <button onClick={switchCamera} style={{
                height: 56, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(24px)',
                border: '1px solid rgba(255,255,255,0.1)', color: '#fff',
                borderRadius: 50, cursor: 'pointer', fontSize: 11, fontWeight: 600, letterSpacing: '0.05em'
              }}>
                <Camera size={20} weight="light" /> FLIP
              </button>

              {/* Tombol shutter */}
              <button onClick={capturePhoto} style={{
                width: 84, height: 84, borderRadius: '50%',
                border: '4px solid rgba(255,255,255,0.8)',
                background: 'transparent', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto'
              }}>
                <div style={{ width: 66, height: 66, borderRadius: '50%', background: '#fff' }} />
              </button>

              <button onClick={resetPosition} style={{
                height: 56, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(24px)',
                border: '1px solid rgba(255,255,255,0.1)', color: '#fff',
                borderRadius: 50, cursor: 'pointer', fontSize: 11, fontWeight: 600, letterSpacing: '0.05em'
              }}>
                <ArrowsClockwise size={20} weight="light" /> RESET
              </button>
            </div>
          </div>
        </>
      )}

      {/* ══════════════════════════════════════════════════
          Preview foto setelah capture
          ══════════════════════════════════════════════════ */}
      {captureUrl && (
        <div style={{
          position: 'absolute', inset: 0, background: 'rgba(5,5,5,0.95)', backdropFilter: 'blur(24px)', zIndex: 40,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
        }}>
          <div style={{ width: '100%', maxWidth: 420, textAlign: 'center' }}>
            <img
              src={captureUrl}
              alt="Hasil capture AR"
              style={{ width: '100%', borderRadius: 32, border: '1px solid rgba(255,255,255,0.1)' }}
            />
            <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
              <a href={captureUrl} download={`outfitar-${productId || 'capture'}.jpg`} className="btn-premium" style={{
                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                background: '#fff', color: '#000',
                borderRadius: 50, padding: '16px 24px', fontSize: 13, fontWeight: 600, textDecoration: 'none',
              }}>
                <DownloadSimple size={18} weight="bold" /> Simpan Foto
              </a>
              <button onClick={() => setCaptureUrl('')} style={{
                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                background: 'rgba(255,255,255,0.05)', color: '#fff',
                border: '1px solid rgba(255,255,255,0.1)', borderRadius: 50,
                padding: '16px 24px', fontSize: 13, fontWeight: 500, cursor: 'pointer',
              }}>
                <X size={18} weight="bold" /> Tutup
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

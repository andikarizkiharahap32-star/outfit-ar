# OutfitAR — Agent Rules & Learned Behaviors

Rules ini dipersist dari hasil audit dan pengembangan proyek OutfitAR.
Berlaku untuk semua sesi agent di workspace ini.

---

## ML Audit Checklist (CNN + KNN)

Setiap kali mengaudit atau membangun komponen ML di proyek ini, verifikasi semua poin berikut:

### CNN Training Pipeline
- [ ] Label format konsisten: `label_mode` di dataset loader **sinkron** dengan loss function
  - Gunakan `label_mode='int'` + `SparseCategoricalCrossentropy` (integer label 0,1,2...)
  - ATAU `label_mode='categorical'` + `CategoricalCrossentropy` (one-hot) — pilih satu, jangan campur
- [ ] Learning rate ≤ **1e-4** untuk fine-tuning pretrained model (bukan 1e-3 default)
- [ ] Urutan layer head yang **benar**: `Dense(linear) → BatchNorm → Activation(relu) → Dropout`
  - **SALAH**: `Dense(relu) → Dropout → BatchNorm`
- [ ] L2 regularization pada Dense head: `kernel_regularizer=keras.regularizers.L2(1e-4)`
- [ ] Data augmentation aktif untuk dataset kecil/terbatas (terutama face/skin images):
  - `RandomFlip("horizontal")`, `RandomBrightness(±20%)`, `RandomContrast(±20%)`, `RandomRotation(≤10°)`
  - Jangan augment yang mengubah warna kulit drastis (no extreme color jitter)
- [ ] Class weight handling untuk imbalanced dataset: hitung `class_weights` dari distribusi, pass ke `model.fit()`
- [ ] Callbacks terpasang: `EarlyStopping` + `ModelCheckpoint(save_best_only=True)` + `ReduceLROnPlateau`

### CNN Inference / Feature Extraction
- [ ] Feature extraction wajib menggunakan **intermediate `keras.Model`** — jangan panggil layer langsung:
  ```python
  # BENAR ✅
  extractor = keras.Model(inputs=model.input, outputs=model.get_layer("efficientnetb0").output)
  feature_vec = extractor.predict(input_tensor, verbose=0)[0]

  # SALAH ❌ — bypass preprocessing pipeline
  extractor = model.get_layer("efficientnetb0")
  feature_vec = extractor(input_tensor, training=False).numpy()[0]
  ```
- [ ] Preprocessing saat inference **sama persis** dengan saat training
- [ ] Input validation sebelum inference: cek `None`, ukuran minimum (≥10px), dan format gambar valid
- [ ] Jika file weights tidak ditemukan, log WARNING yang jelas (bukan silent fallback ke ImageNet)
- [ ] Bangun intermediate model **sekali (lazy)** — jangan rebuild setiap inference call

### KNN Recommendation Engine
- [ ] `n_neighbors` dan skin tone range **sinkron** dengan jumlah kelas CNN:
  - 3-class CNN → `range(1, 4)` bukan `range(1, 6)`
- [ ] `save()` wajib memanggil `self._check_fitted()` di awal — cegah serialize model kosong
- [ ] Slot outfit fallback berbasis keyword ketika `category_id = NULL`:
  - Implementasi `_slot_from_name(product_name)` menggunakan keyword matching
- [ ] Dedup kandidat menggunakan `product_id` — **bukan** object equality dataclass (bisa salah pada float score)
- [ ] Hindari double L2 normalization: jika `fit()` sudah pakai `sklearn normalize`, jangan normalize lagi di extractor
- [ ] KNN yang diimplementasi tapi tidak dipakai di endpoint harus **didokumentasikan eksplisit**:
  - Tambahkan komentar `# NOTE: KNN disabled — requires feature_vector population via feature_extractor.py`
  - Jangan biarkan sebagai silent dead code

### API / Endpoint
- [ ] `await db.commit()` wajib dipanggil setelah `db.add()` + `db.flush()` untuk persist data
- [ ] `diversity_score` harus **dihitung nyata** (pairwise color distance), bukan hardcoded `1.0`
- [ ] `category_slot` harus dari keyword matching nama produk — bukan hardcoded string `"top"` atau `"aksesori"`
- [ ] Hindari pola `shuffle → re-sort` (self-defeating): gunakan deterministic diversity selection
  - Contoh benar: MMR (Maximum Marginal Relevance) atau max pairwise color distance

---

## OutfitAR: Product-Type → 3D Model Mapping

Logic yang sudah terbukti benar (27/27 test cases). Gunakan ini sebagai referensi
jika ada perubahan pada AR model selection di `StreamHP.jsx` atau backend.

### Bottom Wear → NO AR (sembunyikan canvas, tampil overlay)
Keywords: `celana`, `rok`, `pants`, `skirt`, `legging`, `jeans`, `shorts`, `chino`, `sarung`, `kain`

### Pria — Top Wear
| Tipe Produk | Model 3D | Keywords |
|---|---|---|
| Kaos / Hoodie / T-shirt | `PriaShort.glb` | kaos, t-shirt, tshirt, hoodie, tanktop, singlet, polo shirt |
| Kemeja / Sweater / Jaket | `PriaPolo.glb` | kemeja, sweater, sweatshirt, jaket, jacket, blazer, cardigan, bomber, outer, parka, coat, rompi |

Jika user pilih Kaos → default ke PriaShort, dengan tombol switch ke PriaPolo.
Jika user pilih Kemeja → default ke PriaPolo, dengan tombol switch ke PriaShort.

### Wanita — Semua Top Wear → `Wanita.glb`
Rok dikecualikan via bottom wear detection (bukan karena gender).

### Wanita Berhijab — Semua → `WanitaBerhijab .glb`
> ⚠️ Perhatikan: ada **spasi** di nama file `WanitaBerhijab .glb` — ini nama file asli di `/public/models/`

### Implementasi di `StreamHP.jsx`
```js
function getAvailableModels(gender, productName) {
  const g    = String(gender || '').toLowerCase().trim();
  const name = String(productName || '').toLowerCase();
  if (isBottomWear(name)) return [];  // No AR
  if (g === 'pria') {
    const isKaos = PRIA_KAOS_KEYWORDS.some(kw => name.includes(kw));
    return isKaos
      ? ['/models/PriaShort.glb', '/models/PriaPolo.glb']
      : ['/models/PriaPolo.glb', '/models/PriaShort.glb'];
  }
  if (g === 'wanita')      return ['/models/Wanita.glb'];
  if (g === 'wanitahijab') return ['/models/WanitaBerhijab .glb'];
  return ['/models/PriaPolo.glb'];
}
```
Return `[]` (array kosong) → tampil overlay pesan "AR hanya tersedia untuk pakaian atasan".

---

## OutfitAR: 3D Animation Anti-Stiffness Pattern

Saat mengimplementasi animasi bone-based di Three.js + MediaPipe Pose,
gunakan pattern berikut untuk menghindari gerakan kaku/robotic:

### 1. EMA Filter pada Landmark Input
Haluskan setiap landmark SEBELUM dipakai ke bone rotation:
```js
const EMA_ALPHA = 0.30;
smoothed[key] = prev[key] + EMA_ALPHA * (current[key] - prev[key]);
```
Alpha 0.30 = balance antara responsif dan smooth. Nilai lebih rendah = lebih lambat tapi lebih mulus.

### 2. Adaptive LERP (bukan fixed speed)
```js
const dot = qCurrent.dot(qTarget);           // 1.0 = sama, 0.0 = tegak lurus
const t   = LERP_FAST + (LERP_SLOW - LERP_FAST) * Math.abs(dot);
// LERP_FAST = 0.18, LERP_SLOW = 0.07
qCurrent.slerp(qTarget, t);
```
- Ketika sudah dekat (dot≈1) → pakai LERP_SLOW (gerakan pelan, smooth)
- Ketika jauh (dot≈0) → pakai LERP_FAST (catch-up cepat)

### 3. Graceful Fade-out saat Tracking Hilang
Jangan reset ke T-pose langsung. Decay perlahan:
```js
const FADE_SPEED = 0.04;
target.set(0, 0, 0);       // Fade ke rest pose
qCurrent.slerp(qTarget, FADE_SPEED);
```

### 4. Stability Counter Sebelum Aktifkan Animasi
Tunggu minimum N frame valid sebelum mulai rotate bones:
```js
const STABLE_MIN = 15;
if (++stableFrames < STABLE_MIN) return;
```
Mencegah gerakan spurious dari landmark noise saat pertama kali tracking.

### 5. Tracking Loss Timeout
Jika tidak ada landmark valid selama N frame, fade ke rest pose:
```js
const LOST_MAX = 30;
if (lostFrames > LOST_MAX) { fadeToRest(); }
```

---

## Cara Menjalankan Ulang Proyek

**Terminal 1 — Backend (FastAPI):**
```powershell
cd C:\Final_outfitAR\outfit-ar\backend
$env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"; $env:TF_ENABLE_ONEDNN_OPTS="0"
.\venv_fix\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 2 — Frontend (Vite + React):**
```powershell
cd C:\Final_outfitAR\outfit-ar\frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

Buka browser: `http://localhost:5173`

**Training ulang CNN (jika dataset tersedia):**
```powershell
cd C:\Final_outfitAR\outfit-ar\backend\ml\cnn
..\..\..\venv_fix\Scripts\python.exe train_cnn.py
# Output: ml/weights/best_skin_tone_model.keras
```

---

## iPhone / iOS — Kamera AR Wajib HTTPS

Safari di iPhone/iPad **MEMBLOKIR** akses kamera (`getUserMedia`) pada halaman HTTP biasa.
Untuk semua fitur yang menggunakan kamera (AR, scan wajah, dll), WAJIB menggunakan HTTPS.

**Solusi yang harus langsung disarankan saat user ingin test di iPhone:**
1. Gunakan `ngrok http [PORT]` untuk mendapatkan URL HTTPS instan
2. ATAU gunakan `npx localtunnel --port [PORT]` sebagai alternatif gratis
3. ATAU gunakan `cloudflared tunnel --url http://localhost:[PORT]`
4. **JANGAN** menyuruh user mengakses URL `http://IP_LOKAL:PORT` dari iPhone untuk fitur kamera
5. Setelah tunnel aktif, update juga `VITE_API_URL` di `.env` frontend ke URL backend tunnel agar API calls tidak putus

---

## ngrok Free Tier — Batas Sesi & Alternatif

ngrok Free Tier memiliki batasan:
- Hanya 1 tunnel aktif dalam satu waktu
- Sesi tunnel berakhir setelah terminal ngrok ditutup
- Jika muncul error `ERR_NGROK_108` atau "session limit exceeded":

**Alternatif yang langsung bisa direkomendasikan (gratis, tanpa akun):**
```powershell
# Opsi 1: localtunnel — paling mudah, tanpa signup
npx localtunnel --port 5173

# Opsi 2: cloudflared — paling stabil, tanpa akun
cloudflared tunnel --url http://localhost:5173
```

**Jika user sudah punya akun ngrok**, tambahkan authtoken agar sesi lebih lama:
```powershell
ngrok config add-authtoken [TOKEN_DARI_DASHBOARD_NGROK]
ngrok http 5173
```

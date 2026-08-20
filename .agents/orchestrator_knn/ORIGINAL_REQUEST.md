# Original User Request

## Initial Request — 2026-06-28T16:16:28+07:00

Aktivasi sistem KNN pada aplikasi **OutfitAR** dengan cara:
(1) Membuat batch script untuk mengekstrak feature_vector dari 947 gambar produk
via HTTP streaming dari URL Zalora dan menyimpannya ke database,
(2) Mengintegrasikan `KNNOutfitRecommender` sebagai pre-filter di endpoint
rekomendasi sebelum Seasonal Color Analysis scoring.

Working directory: C:\Final_outfitAR\outfit-ar
Integrity mode: development

---

## Konteks Sistem yang Ada

- **Backend**: FastAPI + SQLAlchemy async, database MySQL/MariaDB
- **Tabel `products`**: 947 produk, kolom `feature_vector` ada tapi semua NULL
- **`feature_extractor.py`**: `OutfitFeatureExtractor` sudah ada di `backend/ml/cnn/`
  menggunakan EfficientNet-B0 (1280-dim CNN + 96-dim color histogram + 1-dim texture = 1377-dim)
- **`outfit_recommender.py`**: `KNNOutfitRecommender` sudah lengkap di `backend/ml/knn/`
  dengan cosine similarity, Gap Diversity MMR, slot balancing
- **`recommendations.py`**: Endpoint `POST /api/v1/recommendations` saat ini menggunakan
  Seasonal Color Analysis murni — KNN belum terhubung
- **Python venv**: `backend/venv_fix/` (gunakan `.\venv_fix\Scripts\python.exe`)
- **Database credentials**: ada di `backend/.env`

---

## Requirements

### R1. Batch Feature Extraction Script
Buat script Python (`backend/scripts/populate_features.py`) yang:
- Mengambil semua produk yang `feature_vector IS NULL` dari database
- Untuk setiap produk: stream gambar dari `image_url` via HTTP (tanpa menyimpan ke disk)
- Ekstrak feature vector menggunakan `OutfitFeatureExtractor` yang sudah ada
- Simpan hasilnya ke kolom `feature_vector` di tabel `products` (format JSON array)
- Handle error per-produk secara graceful: jika URL gagal/timeout, skip dan log — jangan hentikan batch
- Tampilkan progress bar dan summary akhir (berapa berhasil, berapa gagal)
- Gunakan concurrent requests (max 5 parallel) untuk mempercepat proses
- Timeout per request: 10 detik

### R2. Integrasi KNN sebagai Pre-filter di Endpoint Rekomendasi
Modifikasi `backend/app/routers/recommendations.py` agar:
- KNN model di-build/fit saat pertama kali dibutuhkan (lazy initialization) dari produk yang sudah punya feature_vector
- Endpoint `POST /api/v1/recommendations` menggunakan KNN untuk mencari
  50 kandidat produk terdekat
- Kandidat KNN kemudian di-re-rank menggunakan Seasonal Color Analysis yang sudah ada
- Jika kurang dari 10 produk punya feature_vector, fallback otomatis ke Seasonal Color Analysis murni
- Response API tidak berubah strukturnya (backward compatible)
- Field `algorithm_ver` menunjukkan `"v5.0-knn+seasonal"` jika KNN aktif

### R3. Query Vector untuk KNN
Karena user tidak punya feature vector produk, gunakan pendekatan ini untuk query:
- Representasikan skin tone user sebagai color histogram 96-dim dari warna RGB skin tone
  (SKIN_TONE_MAP sudah ada di recommendations.py: level 1=dark RGB, 2=fair RGB, 3=light RGB)
- Zero-pad ke 1377-dim agar kompatibel dengan feature matrix produk
- Normalisasi L2 sebelum query ke KNN

---

## Acceptance Criteria

### Batch Script
- [ ] Script dapat dijalankan: `.\venv_fix\Scripts\python.exe scripts\populate_features.py`
- [ ] Script berhasil memproses minimal 10 produk pertama tanpa crash
- [ ] Produk yang berhasil diproses memiliki `feature_vector IS NOT NULL` di database
- [ ] Produk dengan URL gambar gagal di-skip dengan log WARNING (tidak crash)
- [ ] Summary akhir menampilkan: total diproses, berhasil, gagal

### Integrasi KNN
- [ ] `POST /api/v1/recommendations` tetap mengembalikan HTTP 200 setelah integrasi
- [ ] Jika `feature_vector` tersedia >= 10 produk: KNN digunakan sebagai pre-filter
- [ ] Jika `feature_vector` tersedia < 10 produk: fallback ke Seasonal Color Analysis
- [ ] Response struktur tidak berubah (field `outfit_set`, `diversity_score`, dll. tetap ada)
- [ ] Field `algorithm_ver` di response menunjukkan `"v5.0-knn+seasonal"` jika KNN aktif

### Verifikasi End-to-End
- [ ] Backend dapat distart tanpa error:
  `.\venv_fix\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001`
- [ ] Setelah populate minimal 10 produk, test endpoint memberikan HTTP 200:
  `POST http://localhost:8001/api/v1/recommendations` dengan body `{"gender":"pria","skin_tone_level":2,"top_k":5}`

---

## Verification Commands

```powershell
# 1. Jalankan batch populate (dari backend/ folder)
cd C:\Final_outfitAR\outfit-ar\backend
$env:PYTHONIOENCODING='utf-8'; $env:TF_ENABLE_ONEDNN_OPTS='0'
.\venv_fix\Scripts\python.exe scripts\populate_features.py

# 2. Cek feature_vector tersimpan di DB
.\venv_fix\Scripts\python.exe -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv
import os
load_dotenv('.env')
DATABASE_URL = os.getenv('DATABASE_URL')
async def check():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        r = await conn.execute(text('SELECT COUNT(*) FROM products WHERE feature_vector IS NOT NULL'))
        print(f'Products with feature_vector: {r.scalar()}')
asyncio.run(check())
"

# 3. Start backend
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'; $env:TF_ENABLE_ONEDNN_OPTS='0'
.\venv_fix\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 4. Test rekomendasi
$body = '{"gender":"pria","skin_tone_level":2,"top_k":5}'
Invoke-WebRequest -Uri 'http://localhost:8001/api/v1/recommendations' -Method POST -ContentType 'application/json' -Body $body -UseBasicParsing | Select-Object StatusCode, @{N='algo';E={($_.Content | ConvertFrom-Json).data.algorithm_ver}}
```

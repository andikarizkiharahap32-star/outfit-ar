# Original User Request

## Initial Request — 2026-06-28T02:35:41Z

Audit, perbaikan, dan hardening sistem ML pada aplikasi **OutfitAR** — sebuah AR fashion try-on app (React + FastAPI) yang mendeteksi warna kulit user via CNN EfficientNet-B0 dan merekomendasikan outfit via Seasonal Color Analysis. Proyek ini sudah berjalan tetapi ditemukan 15 bug kritis dan risiko overfitting yang perlu diperbaiki tanpa mengubah fungsionalitas yang sudah benar.

Working directory: C:\Final_outfitAR\outfit-ar
Integrity mode: development

---

## Hasil Audit (Temuan yang Harus Diperbaiki)

### Bug Kritis #1 — KNN Dead Code
File: `backend/ml/knn/outfit_recommender.py` dan `backend/app/routers/recommendations.py`
`KNNOutfitRecommender` class sudah diimplementasi lengkap tapi TIDAK PERNAH diimport atau dipanggil di `recommendations.py`. Seluruh KNN system adalah dead code. Integrasikan KNN sebagai pre-filter sebelum seasonal color scoring, ATAU dokumentasikan dengan jelas sebagai fitur future dan buat stub yang eksplisit (bukan diam-diam tidak dipakai).

### Bug Kritis #2 — Tidak Ada Data Augmentation di CNN Training
File: `backend/ml/cnn/train_cnn.py`
Tidak ada `RandomFlip`, `RandomBrightness`, `RandomContrast`, `RandomRotation` di pipeline training. Untuk face/skin tone classification ini adalah risiko overfitting tinggi. Tambahkan augmentation layer ke dalam pipeline training dataset.

### Bug Kritis #3 — diversity_score Hardcoded 1.0
File: `backend/app/routers/recommendations.py` sekitar line 413
`diversity_score=1.0` hardcoded — tidak pernah dihitung. Hitung diversity nyata sebagai rata-rata pairwise color distance antar produk yang direkomendasikan.

### Bug Kritis #4 — category_slot Hardcoded "top"
File: `backend/app/routers/recommendations.py` sekitar line 391
`category_slot="top"` hardcoded untuk semua produk. Gunakan keyword matching dari nama produk (seperti yang sudah ada di `frontend/src/pages/StreamHP.jsx`) untuk menentukan slot: kaos/hoodie→atasan, kemeja/sweater/jaket→atasan, celana→celana, rok→bawahan, dll.

### Bug Kritis #5 — Shuffle + Re-Sort Logic Rusak
File: `backend/app/routers/recommendations.py` sekitar lines 377-384
Kode melakukan `shuffle` top-30 lalu langsung `sort` lagi by score — shuffle tidak memberikan diversity, hanya randomness. Ganti dengan deterministic diversity selection: pilih produk dengan variasi warna terbesar (max color distance) dari kandidat top-30.

### Bug Tinggi #6 — Feature Vector Bypass Preprocessing
File: `backend/ml/cnn/skin_tone_classifier.py` fungsi `_predict_cnn` sekitar line 192-193
```python
extractor = self._model.get_layer("efficientnetb0")
feature_vec = extractor(input_tensor, training=False).numpy()[0]
```
Memanggil EfficientNet layer langsung tanpa `preprocess_input`. Buat intermediate model yang proper:
```python
intermediate = keras.Model(inputs=self._model.input, outputs=self._model.get_layer("efficientnetb0").output)
feature_vec = intermediate.predict(input_tensor, verbose=0)[0]
```

### Bug Tinggi #7 — Ensemble Banker's Rounding
File: `backend/ml/cnn/skin_tone_classifier.py` fungsi `_ensemble_prediction` line 218
```python
final_level = round((cnn_level * 0.7) + (hsv_level * 0.3))
```
Python `round()` pakai banker's rounding. Ganti dengan `int(x + 0.5)` atau `math.floor(x + 0.5)` untuk rounding yang predictable.

### Bug Tinggi #8 — Urutan Layer Salah (Dropout sebelum BatchNorm)
File: `backend/ml/cnn/efficientnet_backbone.py` sekitar line 46-48
```python
x = keras.layers.Dense(256, activation="relu", name="head_dense")(x)
x = keras.layers.Dropout(0.4, name="head_dropout")(x)   # SALAH: Dropout sebelum BN
x = keras.layers.BatchNormalization(name="head_bn")(x)
```
Urutkan yang benar: `Dense(linear) → BatchNorm → Activation(relu) → Dropout → output`

### Bug Medium #9 — Skin Tone Range Tidak Sinkron (1-5 vs 1-3)
File: `backend/ml/knn/outfit_recommender.py` line 169
```python
compat = self._product_skin_compat.get(pid, list(range(1, 6)))  # harusnya range(1, 4)
```
Ganti semua `range(1, 6)` dengan `range(1, 4)` karena CNN hanya punya 3 kelas (1=Dark, 2=Fair, 3=Light).

### Bug Medium #10 — Category Slot Tidak Efektif (category_id=NULL)
File: `backend/ml/knn/outfit_recommender.py` `CATEGORY_SLOTS` dan fungsi `recommend()`
Semua 947 produk di database punya `category_id=NULL`. `CATEGORY_SLOTS.get(cat_id, "aksesori")` mengembalikan "aksesori" untuk semua produk. Tambahkan fallback ke keyword-based slot detection dari nama produk.

### Bug Medium #11 — save() Tanpa Fitted Check
File: `backend/ml/knn/outfit_recommender.py` fungsi `save()` line 363
Tambahkan `self._check_fitted()` di awal fungsi `save()` untuk mencegah serialisasi model yang belum dilatih.

### Bug Medium #12 — SkinToneDetection Tidak Di-commit
File: `backend/app/routers/recommendations.py` lines 145-147
`db.flush()` dipanggil tanpa `db.commit()`. Tambahkan `await db.commit()` setelah `await db.refresh(detection)` untuk memastikan data tersimpan ke database.

### Bug Medium #13 — Tidak Ada Class Weight di Training
File: `backend/ml/cnn/train_cnn.py`
Tidak ada `class_weight` parameter di `model.fit()`. Hitung class weights dari distribusi dataset dan tambahkan ke training untuk menangani imbalanced dataset.

### Bug Medium #14 — Double L2 Normalization
File: `backend/ml/cnn/feature_extractor.py`
Feature vector di-normalize L2 di `_extract_cnn()` lalu di-normalize lagi di `KNNOutfitRecommender.fit()`. Hapus salah satu normalisasi.

### Bug Medium #15 — Learning Rate Terlalu Tinggi
File: `backend/ml/cnn/train_cnn.py` line 75
`Adam(learning_rate=0.001)` terlalu tinggi untuk fine-tuning pretrained model. Ubah ke `Adam(learning_rate=1e-4)`. Tambahkan juga `kernel_regularizer=keras.regularizers.L2(1e-4)` ke Dense layer di `efficientnet_backbone.py`.

---

## Requirements

### R1. Perbaiki semua 15 bug yang sudah diidentifikasi di atas
Setiap perbaikan harus minimal dan tepat sasaran — jangan mengubah fungsionalitas yang sudah benar. Pertahankan: arsitektur EfficientNet-B0, Seasonal Color Analysis logic, EarlyStopping+ModelCheckpoint, dan Gap Diversity MMR algorithm.

### R2. Integrasikan atau Dokumentasikan KNN dengan Jelas
Pilih salah satu:
- (a) Integrasikan `KNNOutfitRecommender` sebagai pre-filter di `recommendations.py` jika feature_vector sudah tersedia di database
- (b) Jika feature_vector tidak tersedia, tambahkan komentar `# NOTE: KNN disabled - requires feature_vector population` yang jelas dan buat fungsi placeholder `_knn_prefilter()` yang return None dengan penjelasan

### R3. Tambahkan Data Augmentation yang Tepat
Augmentation harus sesuai untuk skin tone detection dari foto wajah:
- RandomFlip horizontal (valid untuk wajah)
- RandomBrightness ±20% (simulasi kondisi cahaya berbeda)
- RandomContrast ±20% (variasi kamera)
- RandomRotation maksimal 10 derajat (posisi kepala)
- JANGAN tambahkan RandomCrop agresif atau color jitter ekstrem yang mengubah warna kulit

### R4. Jalankan Backend dan Verifikasi Endpoint
Setelah semua perbaikan diterapkan:
- Jalankan backend: `cd C:\Final_outfitAR\outfit-ar\backend && .\venv_fix\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001`
- Verifikasi endpoint rekomendasi berfungsi dengan test request
- Pastikan tidak ada import error atau startup error

---

## Acceptance Criteria

### CNN Training Pipeline
- [ ] `train_cnn.py` berhasil diimport tanpa error: `python -c "import sys; sys.path.insert(0, 'ml/cnn'); from train_cnn import main"`
- [ ] Data augmentation aktif (RandomFlip, RandomBrightness, RandomContrast ada di kode)
- [ ] Learning rate ≤ 1e-4
- [ ] L2 regularization ada di Dense head
- [ ] Class weight calculation ada di training script

### Feature Extraction
- [ ] `_predict_cnn` menggunakan intermediate model (bukan direct layer call)
- [ ] Feature vector shape = 1280 (verifikasi dengan unit test sederhana)
- [ ] Ensemble menggunakan `int(x + 0.5)` bukan `round()`

### KNN & Recommendation Logic  
- [ ] Skin tone range konsisten 1-3: `grep -rn "range(1, 6)" backend/ml/` harus mengembalikan 0 hasil
- [ ] KNN status jelas: terintegrasi atau terdokumentasi (bukan silent dead code)
- [ ] `save()` memanggil `_check_fitted()` di awal
- [ ] `diversity_score` dihitung nyata (bukan hardcoded 1.0)
- [ ] `category_slot` ditentukan dari nama produk (bukan hardcoded "top")

### Database & API
- [ ] `await db.commit()` ada setelah `db.flush()` di endpoint detect-skin-tone
- [ ] Backend start tanpa error: `python -c "from app.main import app; print('OK')"`
- [ ] GET/POST `/api/v1/recommendations` mengembalikan HTTP 200 dengan produk valid

### Layer Order
- [ ] `efficientnet_backbone.py` head sequence: `Dense(linear) → BN → relu → Dropout → Dense(softmax)`

---

## Verification Commands

```powershell
# 1. Check skin tone range consistency
Select-String -Pattern 'range\(1, 6\)' -Path backend\ml\knn\outfit_recommender.py

# 2. Check backend can import
cd C:\Final_outfitAR\outfit-ar\backend
.\venv_fix\Scripts\python.exe -c "from app.main import app; print('Backend import OK')"

# 3. Start backend
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'
.\venv_fix\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 4. Test recommendation endpoint
Invoke-WebRequest -Uri 'http://localhost:8001/api/v1/recommendations' -Method POST -ContentType 'application/json' -Body '{"gender":"pria","skin_tone_level":2,"top_k":5}'

# 5. Test health check
Invoke-WebRequest -Uri 'http://localhost:8001/health' -Method GET
```

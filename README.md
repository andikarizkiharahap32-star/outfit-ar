# OutfitAR — Rekomendasi Outfit dengan AR Real-time

> CNN EfficientNet + KNN Gap Diversity + U-Net AR Virtual Try-On

## Stack Teknologi
- **Backend**: Python 3.10, FastAPI, SQLAlchemy (async), MySQL (Laragon)
- **ML/AI**: TensorFlow/Keras, EfficientNet-B0, U-Net, MediaPipe, scikit-learn
- **Frontend**: React 18, Vite, TailwindCSS, Zustand, Framer Motion
- **Database**: MySQL via Laragon

## Struktur Folder
```
outfit-ar/
├── backend/
│   ├── app/
│   │   ├── config/          # Settings & Database
│   │   ├── models/          # SQLAlchemy Models
│   │   ├── schemas/         # Pydantic Schemas
│   │   ├── routers/         # FastAPI Routers
│   │   └── main.py          # Entry point
│   ├── ml/
│   │   ├── cnn/             # EfficientNet (skin tone + feature extractor)
│   │   ├── knn/             # KNN Gap Diversity Recommender
│   │   └── ar/              # U-Net Virtual Try-On
│   ├── scripts/             # Import CSV & Training
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/           # React pages
│       ├── components/      # UI Components
│       ├── store/           # Zustand state
│       └── services/        # API calls
├── database/
│   └── schema.sql           # MySQL schema
└── data/
    └── raw/provenance.csv   # Data produk
```

## Cara Menjalankan (Step by Step)

### 1. Persiapan Database (Laragon)
1. Jalankan Laragon → Start All
2. Buka HeidiSQL / phpMyAdmin
3. Buat database: `CREATE DATABASE outfit_ar CHARACTER SET utf8mb4;`
4. Import: `database/schema.sql`

### 2. Backend (Python)
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env           # Edit sesuai kebutuhan
python scripts/import_csv.py --file ../data/raw/provenance.csv
python scripts/train_models.py
uvicorn app.main:app --reload --port 8000
```
Akses API docs: http://localhost:8000/api/docs

### 3. Frontend (React)
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Akses aplikasi: http://localhost:5173

## Endpoint API Utama
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| POST | /api/v1/recommendations/detect-skin-tone | Upload foto → deteksi skin tone |
| POST | /api/v1/recommendations/outfit | Generate rekomendasi KNN |
| GET  | /api/v1/products | Daftar produk dengan filter |
| POST | /api/v1/ar/tryon/photo | AR try-on dari foto |
| WS   | /api/v1/ar/tryon/realtime/{id} | AR real-time WebSocket |

#Sisi Backend (Yang Membuka Gerbang)
import logging
import sys
import time
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from loguru import logger

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.config.settings import get_settings
from app.config.database import engine, create_tables
from app.routers import products, users, recommendations, ar, health

# --- 1. LOGGING SETUP ---
# setup logging standar Python buat nangkep log level INFO ke atas
# format-nya: waktu | level | pesan — biar gampang dibaca di terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    stream=sys.stdout
)

# loguru lebih enak dari logging biasa karena bisa colorize & format fleksibel
# enqueue=True biar thread-safe waktu nulis log
logger.remove()  # hapus handler default loguru dulu sebelum pasang yang custom
logger.add(
    sys.stdout, 
    colorize=True, 
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    enqueue=True
)

# load semua config dari settings (env variables, dll)
settings = get_settings()

# dict buat nyimpen frame kamera dari HP lewat WebSocket
# key = session_id, value = frame data (base64 biasanya)
remote_camera_frames = {}

# --- 2. SUCCESS BANNER ---
# fungsi ini cuma buat nge-print banner ke terminal waktu server nyala
# actual_path = path folder uploads yang lagi dipake
def print_success_banner(actual_path):
    banner = f"""
{"="*85}
[OUTFITAR] SISTEM BERHASIL DIJALANKAN! (FIXED CORS VERSION)
{"="*85}
STATUS      : ONLINE & READY
DATASET     : 947+ Zalora Products Loaded
BACKEND     : http://localhost:8000
UPLOADS     : /uploads mapped to -> {actual_path}
SECURITY    : Strict CORS Middleware (Auto-handled)
{"="*85}
    """
    # Encode aman untuk Windows terminal (cp1252 tidak support emoji)
    try:
        print(banner, flush=True)
    except UnicodeEncodeError:
        # fallback kalau ada karakter yang ga bisa di-encode Windows
        print(banner.encode('ascii', errors='replace').decode('ascii'), flush=True)

# --- 3. LIFESPAN ---
# BASE_DIR = folder root project (2 level ke atas dari file ini)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# folder uploads ada di luar app/, sejajar sama folder backend/
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# lifespan dijalankan waktu app start & shutdown
# ini pengganti cara lama pakai @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    # bikin folder uploads kalau belum ada, exist_ok=True biar ga error kalau udah ada
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        logger.info(f"[Storage] New folder created: {UPLOAD_DIR}")
    
    logger.info("[Database] Ensuring tables exist...")
    await create_tables()

    # --- AUTO-MIGRATION: tambah kolom yang mungkin belum ada di Railway ---
    # Ini aman dijalankan berkali-kali karena pakai IF NOT EXISTS
    migration_sqls = [
        "ALTER TABLE skin_tone_detections ADD COLUMN IF NOT EXISTS gender ENUM('pria','wanita','unisex') NOT NULL DEFAULT 'pria'",
        "ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS gender ENUM('pria','wanita','unisex') NOT NULL DEFAULT 'pria'",
        "ALTER TABLE outfit_combinations ADD COLUMN IF NOT EXISTS gender ENUM('pria','wanita','unisex') NOT NULL DEFAULT 'pria'",
    ]
    from sqlalchemy import text
    async with engine.begin() as conn:
        for sql in migration_sqls:
            try:
                await conn.execute(text(sql))
                logger.info(f"[Migration] OK: {sql[:60]}...")
            except Exception as mig_err:
                # Log tapi jangan crash — mungkin kolom sudah ada dengan format berbeda
                logger.warning(f"[Migration] Skipped (might already exist): {mig_err}")

    print_success_banner(UPLOAD_DIR)
    logger.info("[Storage] Storage engine active: {UPLOAD_DIR}")

    # --- AUTO-SEED: Masukkan produk sample jika DB kosong (untuk Railway) ---
    try:
        from database.seed_production import seed_products_if_empty
        await seed_products_if_empty(engine)
        
        # FIX: Bersihkan URL gambar yang salah format secara langsung di database
        from sqlalchemy import text
        from app.config.database import AsyncSessionFactory
        async with AsyncSessionFactory() as session:
            await session.execute(text("UPDATE products SET image_url = REPLACE(image_url, 'products/https://', 'https://') WHERE image_url LIKE 'products/https://%'"))
            await session.commit()
    except Exception as seed_err:
        logger.warning(f"[Seed] Auto-seed dilewati: {seed_err}")
    
    yield  # titik ini adalah saat app jalan normal, kode di bawah yield = waktu shutdown
    logger.warning("[Server] Shutting down...")
    await engine.dispose()  # tutup koneksi database dengan bersih


# inisialisasi FastAPI app utama
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)
#Sisi Backend (Yang Membuka Gerbang)
# middleware buat handle header X-Forwarded-For dari reverse proxy (nginx, ngrok, dll)
app.add_middleware(ProxyHeadersMiddleware)

# CORS middleware — allow_origins="*" biar bisa diakses dari mana aja (development mode)
# allow_credentials=False karena kalau origins="*" ga bisa True (browser block)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# --- 5. DEBUG MIDDLEWARE (SUDAH DIBERSIHKAN DARI KONFLIK CORS) ---
# middleware ini jalan di setiap request — buat logging & nambah header tambahan
@app.middleware("http")
async def debug_middleware(request: Request, call_next):
    start_time = time.time()  # catat waktu mulai buat hitung durasi response
    origin = request.headers.get("origin", "*")
    method = request.method
    path = request.url.path
    
    logger.info(f"[REQUEST] {method}: {path} | Origin: {origin}")
    
    try:
        response = await call_next(request)  # terusin request ke handler berikutnya
        duration = (time.time() - start_time) * 1000  # konversi ke milidetik
        
       
        # header ini diperlukan supaya ngrok ga redirect ke halaman warning-nya
        response.headers["ngrok-skip-browser-warning"] = "true" 
        
        # log berbeda tergantung status code — 200 = sukses, lainnya = perlu perhatian
        if response.status_code == 200:
            logger.success(f"[200 OK] {path} ({duration:.1f}ms)")
        else:
            logger.warning(f"[{response.status_code}] {path} ({duration:.1f}ms)")
            
        return response

    except Exception as e:
        # kalau ada exception tak terduga di middleware, return 500 langsung
        # CORS header ditambah manual karena middleware CORS mungkin belum jalan
        logger.critical(f"[CRASH] Backend Crash in Middleware: {str(e)}")
        return JSONResponse(
            status_code=500, 
            content={"error": str(e)},
            headers={"Access-Control-Allow-Origin": "*"}
        )

# --- 6. STATIC FILES MOUNTING ---
# route /uploads bakal serve file langsung dari folder UPLOAD_DIR di filesystem
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# --- 7. WEBSOCKET ---
# endpoint ini buat terima stream frame dari kamera HP secara real-time
# session_id dipakai buat identifikasi siapa yang lagi konek
@app.websocket("/api/v1/stream/hp/{session_id}")
async def websocket_hp_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"[WS] iPhone Connected: {session_id}")
    try:
        while True:
            data = await websocket.receive_json()
            # simpan frame terbaru ke dict, tiap session punya slot sendiri
            if data.get("type") == "frame":
                remote_camera_frames[session_id] = data.get("frame")
    except WebSocketDisconnect:
        # kalau HP disconnect, hapus frame-nya dari dict biar ga makan memori
        if session_id in remote_camera_frames:
            del remote_camera_frames[session_id]

# share dict frames ke seluruh app lewat app.state biar bisa diakses router lain
app.state.remote_frames = remote_camera_frames

# --- 8. REGISTRASI ROUTER ---
# semua endpoint di-prefix /api/v1 biar versinya jelas
API_PREFIX = "/api/v1"
app.include_router(health.router,            prefix=API_PREFIX, tags=["Health"])
app.include_router(users.router,             prefix=API_PREFIX, tags=["Users"])
app.include_router(products.router,          prefix=API_PREFIX, tags=["Products"])
app.include_router(recommendations.router,   prefix=API_PREFIX, tags=["Recommendations"])
app.include_router(ar.router,                prefix=API_PREFIX, tags=["AR Engine"])

# root endpoint — buat ngecek cepat apakah server nyala
@app.get("/")
async def root():
    return {"app": "OutfitAR", "status": "online", "dataset_count": 947}

# --- 9. ENDPOINT DETEKTIF ---
# endpoint debug buat ngecek apakah file gambar ada di path yang bener
# berguna waktu gambar ga muncul di frontend — bisa debug langsung dari browser
@app.get("/api/v1/debug-path/{sub_path:path}")
async def debug_image_path(sub_path: str):
    full_path = os.path.join(UPLOAD_DIR, sub_path)
    exists = os.path.exists(full_path)
    return {
        "python_is_looking_here": full_path,
        "file_exists": exists,
        "is_it_a_file": os.path.isfile(full_path) if exists else False,
        "parent_folder_exists": os.path.exists(os.path.dirname(full_path))
    }
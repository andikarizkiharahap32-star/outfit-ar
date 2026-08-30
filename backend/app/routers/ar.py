import uuid
import base64
import cv2
import numpy as np
from pathlib import Path
from urllib.parse import urlparse, unquote
from fastapi import APIRouter, Depends, File, UploadFile, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.config.database import get_db_session
from app.config.settings import get_settings
from app.models.models import ARSession, Product
from app.schemas.schemas import ARSessionOut, ARSessionResponse, ARMaskResponse

# Router AR — menangani semua endpoint Virtual Try-On (WebSocket dan HTTP)
router = APIRouter(prefix="/ar")
settings = get_settings()
# Global instance AR engine — lazy loaded agar server tidak crash saat startup jika TF gagal load
_ar_engine = None


def convert_frame_to_base64(frame, quality=55):
    # Konversi frame OpenCV (numpy array BGR) ke string base64 untuk dikirim via WebSocket
    # Quality 55 = tradeoff antara kualitas gambar dan kecepatan transmisi
    try:
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ret:
            return ""
        return base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        logger.error(f"Gagal konversi frame ke base64: {e}")
        return ""


@router.get("/check")
async def health_check():
    # Endpoint sederhana untuk cek apakah AR router bisa diakses dan engine sudah siap
    return {
        "status": "online",
        "engine_ready": _ar_engine is not None,
        "message": "OutfitAR Router is Reachable",
        "websocket": "/api/v1/ar/tryon/realtime/{product_id}",
    }


def get_root_dir() -> Path:
    # Naik 3 level dari file ini (ar.py → routers → app → backend) untuk dapat root backend
    return Path(__file__).resolve().parent.parent.parent


def get_ar_engine():
    # Lazy initialization: AR engine hanya dibuat saat pertama kali dibutuhkan
    # Ini mencegah error startup kalau TensorFlow tidak tersedia saat server pertama nyala
    global _ar_engine
    if _ar_engine is None:
        from ml.ar.virtual_tryon import VirtualTryOnEngine
        root = get_root_dir()
        # Coba beberapa kemungkinan path file weights agar fleksibel di berbagai environment
        possible_paths = [
            root / "ml" / "weights" / settings.unet_weights,
            root / "app" / "ml" / "weights" / settings.unet_weights,
            Path(r"C:\Final_outfitAR\outfit-ar\backend\ml\weights") / settings.unet_weights,
        ]

        unet_weights = None
        for p in possible_paths:
            if p.exists():
                unet_weights = p
                logger.success(f"Weights found at: {p}")
                break

        if unet_weights is None:
            logger.error("Weights file 'unet_final.h5' TIDAK DITEMUKAN! Engine akan mencoba fallback.")

        _ar_engine = VirtualTryOnEngine(
            unet_weights=str(unet_weights) if unet_weights else None,
            backbone="efficientnet",
            target_fps=settings.ar_frame_rate,
        )
    return _ar_engine


def normalize_product_id(product_id: str):
    # Konversi product_id ke integer jika memungkinkan, biarkan string jika tidak
    product_id = str(product_id).strip()
    return int(product_id) if product_id.isdigit() else product_id


def clean_upload_path(raw_path: str) -> str:
    # Bersihkan path gambar dari berbagai format yang mungkin datang dari database
    if not raw_path:
        return ""
    clean = str(raw_path).strip().replace("\\", "/")
    # Jika URL penuh (http://...), ekstrak hanya path-nya
    if clean.startswith("http"):
        try:
            clean = unquote(urlparse(clean).path)
        except Exception:
            pass
    clean = clean.lstrip("/")
    # Hapus prefix 'uploads/' atau 'storage/' agar path relatif terhadap UPLOAD_DIR
    for prefix in ("uploads/", "storage/"):
        if clean.lower().startswith(prefix):
            clean = clean[len(prefix):]
    return clean


def resolve_product_image_path(raw_path: str) -> Path | None:
    # Cari file gambar baju di berbagai kemungkinan lokasi folder
    root = get_root_dir()
    clean = clean_upload_path(raw_path)
    if not clean:
        return None

    # Daftar lokasi yang mungkin — dicoba satu per satu sampai ketemu
    candidates = [
        root / "uploads" / clean,
        root / clean,
        root / "backend" / "uploads" / clean,
    ]

    # Jika path tidak dimulai dengan 'products/', coba tambahkan prefix tersebut
    if not clean.lower().startswith("products/"):
        candidates.extend([
            root / "uploads" / "products" / clean,
            root / "backend" / "uploads" / "products" / clean,
        ])

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    logger.warning(f"File gambar baju tidak ditemukan. raw='{raw_path}', clean='{clean}'")
    return None


async def load_product(db: AsyncSession, product_id: str):
    # Cari produk di database — coba sebagai integer ID dulu, lalu fallback ke string
    lookup_id = normalize_product_id(product_id)
    result = await db.execute(select(Product).where(Product.id == lookup_id))
    product = result.scalar_one_or_none()

    # Kalau tidak ketemu sebagai int, coba lagi dengan string (untuk product_external_id)
    if product is None and isinstance(lookup_id, int):
        result = await db.execute(select(Product).where(Product.product_external_id == str(lookup_id)))
        product = result.scalar_one_or_none()

    return product


# ================================================================
# ENDPOINT UTAMA AR — WebSocket Real-Time Virtual Try-On
# Alur: Koneksi → Load gambar baju → Loop terima frame → Render AR → Kirim balik
# ================================================================
@router.websocket("/tryon/realtime/{product_id}")
async def tryon_realtime(websocket: WebSocket, product_id: str, db: AsyncSession = Depends(get_db_session)):
    await websocket.accept()
    logger.success(f"WebSocket AR terhubung untuk produk: {product_id}")

    engine = get_ar_engine()
    session_id = uuid.uuid4().hex  # ID unik per sesi AR
    frame_count = 0

    # Default clothing: warna coklat placeholder jika gambar baju tidak ditemukan
    clothing = np.zeros((512, 512, 3), dtype=np.uint8)
    clothing[:] = (180, 120, 80)
    texture_b64 = None
    product_payload = None

    try:
        # Ambil data produk dari database dan load gambarnya ke memory
        product = await load_product(db, product_id)
        if product:
            product_payload = {
                "id": product.id,
                "name": getattr(product, "name", None),
                "image_url": getattr(product, "image_url", None),
                "gender": getattr(product, "gender", None),
            }
            image_path = resolve_product_image_path(getattr(product, "image_url", ""))
            if image_path:
                loaded_img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
                if loaded_img is not None:
                    # Resize ke 512x512 agar konsisten dengan input AR engine
                    clothing = cv2.resize(loaded_img, (512, 512))
                    # Encode gambar asli ke base64 untuk dikirim ke frontend sebagai texture 3D
                    ret, buffer = cv2.imencode('.jpg', loaded_img, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                    if ret:
                        texture_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')
                    logger.info(f"Berhasil memuat gambar baju: {image_path}")
        else:
            logger.warning(f"Produk id={product_id} tidak ditemukan. Pakai placeholder.")
    except Exception as e:
        logger.warning(f"Gagal memuat produk/gambar baju: {e}")

    # Kirim pesan konfirmasi koneksi berhasil + texture baju ke frontend
    await websocket.send_json({
        "type": "connected",
        "session_id": session_id,
        "product_id": product_id,
        "product": product_payload,
        "message": "AR engine initialized",
        "texture_base64": texture_b64,  # Texture ini dipakai Three.js untuk render model 3D
    })

    try:
        while True:
            # Terima data frame dari frontend (dikirim setiap ~33ms untuk 30 FPS)
            data = await websocket.receive_json()

            # Perintah stop dari frontend — keluar dari loop
            if data.get("type") == "stop":
                break

            # Abaikan pesan selain frame (misalnya ping atau metadata lain)
            if data.get("type") != "frame":
                continue

            try:
                frame_raw = data.get("frame", "")
                # Format base64 dari kamera browser: "data:image/jpeg;base64,/9j/..."
                # Hapus prefix sebelum koma agar bisa di-decode
                if "," in frame_raw:
                    frame_raw = frame_raw.split(",", 1)[1]

                # Decode base64 → bytes → numpy array → gambar OpenCV
                frame_bytes = base64.b64decode(frame_raw)
                nparr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue

                # Kirim frame ke AR engine untuk diproses (overlay baju ke badan)
                result = engine.render_frame(
                    frame_bgr=frame,
                    clothing_bgr=clothing,
                    product_id=product_id,
                )

                # Jika pose tidak terdeteksi, kirim frame asli tanpa overlay
                final_output = result.frame_bgr if getattr(result, "pose_detected", False) else frame
                frame_b64 = convert_frame_to_base64(final_output)

                # Ekstrak data pose landmarks jika tersedia — digunakan frontend Three.js untuk tracking
                pose_data = None
                if hasattr(result, "pose_landmarks") and result.pose_landmarks:
                    pose_data = {
                        i: {"x": lm.x, "y": lm.y, "z": lm.z}
                        for i, lm in enumerate(result.pose_landmarks.landmark)
                    }

                # Kirim hasil render kembali ke frontend
                await websocket.send_json({
                    "type": "ar_frame",
                    "frame": frame_b64,
                    "landmarks": pose_data,                                      # Koordinat titik tubuh
                    "pose_detected": bool(getattr(result, "pose_detected", False)),
                    "render_time_ms": float(getattr(result, "render_time_ms", 0.0)),
                    "frame_index": frame_count,
                })
                frame_count += 1

            except Exception as e:
                logger.error(f"Error saat memproses frame: {e}")
                await websocket.send_json({"type": "error", "message": f"Frame gagal diproses: {str(e)}"})

    except WebSocketDisconnect:
        logger.warning(f"Sesi AR {session_id[:8]} terputus oleh pengguna.")
    except Exception as e:
        logger.error(f"Error Runtime AR: {e}")
    finally:
        # Pastikan WebSocket selalu ditutup dengan benar meskipun ada error
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info(f"Sesi AR {session_id[:8]} selesai.")


@router.post("/tryon/photo", response_model=ARMaskResponse)
async def tryon_photo(user_photo: UploadFile = File(...), product_id: int = 0, db: AsyncSession = Depends(get_db_session)):
    # Endpoint ini sengaja belum diaktifkan — semua AR pakai mode realtime WebSocket
    raise NotImplementedError("Endpoint photo try-on belum diaktifkan. Pakai websocket realtime.")


@router.get("/sessions")
async def list_ar_sessions(user_id: int | None = None, db: AsyncSession = Depends(get_db_session)):
    # Ambil 20 sesi AR terbaru — bisa difilter per user_id kalau pengguna sudah login
    q = select(ARSession).order_by(ARSession.created_at.desc()).limit(20)
    if user_id:
        q = q.where(ARSession.user_id == user_id)
    sessions = (await db.execute(q)).scalars().all()
    return {"success": True, "data": [ARSessionOut.model_validate(s) for s in sessions]}
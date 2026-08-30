import uuid
import re
import numpy as np
import cv2  # Tambahan untuk membaca gambar dari HP
import logging
import time
import os
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field   
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.config.database import get_db_session
from app.config.settings import get_settings
from app.models.models import Product, SkinToneDetection, Recommendation
from app.schemas.schemas import (
    SkinToneDetectionResponse,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationOut,
    OutfitSetItem,
    ProductOut,
    BaseResponse,
)

# Import model AI (CNN skin tone classifier) dan palet warna yang sudah didefinisikan
from ml.cnn.skin_tone_classifier import SkinToneClassifier, SKIN_TONE_RECOMMENDED_COLORS
import json
# Import mesin KNN untuk mencocokkan vektor fitur produk
from ml.knn.outfit_recommender import KNNOutfitRecommender

# Inisialisasi objek KNN dengan 50 tetangga terdekat menggunakan metric cosine similarity
knn_recommender = KNNOutfitRecommender(n_neighbors=50, metric="cosine")

# Setup logger khusus untuk modul rekomendasi agar mudah dimonitor di terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OUTFITAR-DIAGNOSTIC-ENGINE")

# Router ini menangani semua endpoint yang berhubungan dengan rekomendasi outfit dan deteksi skin tone
router = APIRouter(prefix="/recommendations")
settings = get_settings()

# =====================================================================
# INISIALISASI MODEL AI (Dijalankan sekali saat server pertama kali nyala)
# Kalau gagal load, skin_classifier diset None agar server tetap bisa jalan
# =====================================================================
try:
    # Path mengarah ke file model hasil training CNN di folder ml/weights/
    WEIGHTS_PATH = os.path.join("ml", "weights", "best_skin_tone_model.keras")
    skin_classifier = SkinToneClassifier(weights_path=WEIGHTS_PATH)
    logger.info("[OK] BINGO! Model AI Skin Tone berhasil dimuat ke dalam memori.")
except Exception as e:
    logger.error(f"[ERROR] GAGAL memuat model AI: {e}")
    # Jika model gagal dimuat, set None dan sistem akan throw HTTP 500 saat ada request
    skin_classifier = None


# --- UTILITY 1: KONVERSI WARNA (HEX/TEKS → RGB NumPy) ---
def hex_to_rgb(color_str):
    """Mengonversi string HEX atau TEKS WARNA ke array RGB NumPy."""
    # Jika input kosong atau tidak dikenal, kembalikan warna abu-abu netral
    if not color_str or str(color_str).lower() == 'unknown' or str(color_str).strip() == "":
        return np.array([128, 128, 128]) 
        
    color_str = str(color_str).strip().lower()

    # Kamus penerjemah: nama warna teks (dari scraping Zalora/Shopee) → kode HEX
    color_dictionary = {
        "hitam": "#000000", "black": "#000000",
        "putih": "#FFFFFF", "white": "#FFFFFF",
        "merah": "#FF0000", "red": "#FF0000", "maroon": "#800000",
        "biru": "#0000FF", "blue": "#0000FF", "navy": "#000080",
        "hijau": "#008000", "green": "#008000", "olive": "#808000",
        "kuning": "#FFFF00", "yellow": "#FFFF00", "mustard": "#FFDB58",
        "cokelat": "#A52A2A", "brown": "#A52A2A", "khaki": "#C3B091", "mocca": "#A38068",
        "abu-abu": "#808080", "grey": "#808080", "gray": "#808080", "silver": "#C0C0C0",
        "pink": "#FFC0CB", "merah muda": "#FFC0CB", "peach": "#FFE5B4",
        "ungu": "#800080", "purple": "#800080", "lilac": "#C8A2C8",
        "orange": "#FFA500", "oranye": "#FFA500"
    }

    # Cek apakah color_str mengandung nama warna dari kamus, lalu ubah ke HEX
    for text_color, hex_code in color_dictionary.items():
        if text_color in color_str:
            color_str = hex_code
            break

    # Ubah string HEX (contoh: "#FF0000") menjadi array [R, G, B] untuk perhitungan jarak warna
    try:
        color_str = color_str.lstrip('#')
        # Pastikan panjangnya 6 karakter, kalau tidak berarti format tidak valid
        if len(color_str) != 6:
            return np.array([128, 128, 128])
        return np.array([int(color_str[i:i+2], 16) for i in (0, 2, 4)])
    except Exception:
        return np.array([128, 128, 128])

# --- UTILITY 2: MEMBERSIHKAN URL GAMBAR PRODUK DARI DATABASE ---
def sanitize_image_url(raw_url: str) -> str:
    # Hapus spasi, ubah backslash Windows ke slash, dan perbaiki format path
    if not raw_url:
        return ""
    if raw_url.startswith("http://") or raw_url.startswith("https://"):
        return raw_url
    clean = raw_url.strip().replace("\\", "/")
    clean = re.sub(r'(?i)\b(products|pria|wanita|unisex)\s+', r'\1/', clean)
    lower_clean = clean.lower()
    # Tambahkan prefix "products/" jika path belum dimulai dari folder yang benar
    if not lower_clean.startswith('products/') and not lower_clean.startswith('uploads/') and not lower_clean.startswith('storage/'):
        clean = f"products/{clean}"
    return clean

# Referensi warna RGB untuk setiap level skin tone — digunakan untuk kalkulasi jarak warna
SKIN_TONE_MAP = {
    1: np.array([139, 69, 19]),   # Level 1: Dark (warna coklat gelap)
    2: np.array([210, 180, 140]), # Level 2: Fair (warna kuning langsat)
    3: np.array([255, 224, 189]), # Level 3: Light (warna kulit terang)
}

# --- ENDPOINT 1: DETEKSI SKIN TONE MENGGUNAKAN MODEL CNN ---
@router.post("/detect-skin-tone", response_model=SkinToneDetectionResponse)
async def detect_skin_tone(
    image: UploadFile = File(...),
    user_id: int | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    logger.info("--- [SCAN] MENGANALISIS WAJAH DENGAN AI ---")
    
    # Kalau model AI belum berhasil dimuat saat server startup, langsung tolak request
    if skin_classifier is None:
        raise HTTPException(status_code=500, detail="Mesin AI sedang offline/rusak.")

    try:
        # Baca bytes dari file gambar yang diupload, ubah ke format numpy array agar bisa diproses OpenCV
        contents = await image.read()
        nparr = np.frombuffer(contents, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Validasi: pastikan file yang diupload benar-benar gambar yang valid
        if img_bgr is None:
            raise ValueError("File bukan format gambar yang valid.")

        # OPTIMASI KECEPATAN: Resize gambar besar ke max 640px sebelum masuk CNN
        # CNN EfficientNet-B0 hanya butuh 224x224, gambar besar hanya buang waktu processing
        h, w = img_bgr.shape[:2]
        max_dim = 640
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            img_bgr = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
            logger.info(f"[SCAN] Gambar diresize: ({w}x{h}) -> ({new_w}x{new_h}) untuk percepatan CNN")

        # Kirim gambar ke CNN (EfficientNet-B0) untuk diklasifikasikan skin tone-nya
        ai_result = skin_classifier.detect(img_bgr)
        
    except ValueError as ve:
        logger.warning(f"Deteksi wajah gagal: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error AI Internal: {e}")
        raise HTTPException(status_code=500, detail="Terjadi kesalahan pada mesin AI.")

    # Simpan hasil deteksi ke tabel skin_tone_detections di database MySQL
    # Catatan: gender tidak disimpan ke DB karena kolom mungkin belum ada di Railway
    # Gender tetap dikembalikan di response dari ai_result
    detection = SkinToneDetection(
        user_id=user_id,
        skin_tone_level=ai_result.level,
        skin_tone_hex=ai_result.hex_color,
        confidence=ai_result.confidence,
        # Buat nama file unik untuk path gambar (8 karakter random)
        image_path=f"uploads/skins/scan_{uuid.uuid4().hex[:8]}.jpg",
        feature_vector=ai_result.feature_vector
    )
    db.add(detection)
    await db.commit()
    await db.refresh(detection)

    # Kembalikan hasil lengkap: level kulit, hex warna, label, dan palet warna yang cocok/dihindari
    return SkinToneDetectionResponse(
        message="Analisis AI Selesai",
        skin_tone_level=ai_result.level,
        skin_tone_hex=ai_result.hex_color,
        confidence=ai_result.confidence,
        skin_tone_label=ai_result.label,
        recommended_colors=ai_result.recommended_colors,
        avoid_colors=ai_result.avoid_colors,
        detection_id=detection.id,
        gender=ai_result.gender,
    )

# --- ENDPOINT 2: SEASONAL COLOR RECOMMENDATION ENGINE ---
# =====================================================================
# Logika ini mengklasifikasikan warna pakaian ke dalam 4 musim
# (Spring/Summer/Autumn/Winter) berdasarkan nilai HSV-nya, lalu
# mencocokkan dengan profil warna kulit pengguna.
#
# Mapping skin tone ke musim yang cocok:
#   Level 1 (Dark)  -> Autumn & Winter (warna dalam dan hangat)
#   Level 2 (Fair)  -> Spring & Autumn (warna hangat dan natural)
#   Level 3 (Light) -> Summer & Winter (warna dingin dan lembut)
# =====================================================================

def classify_color_season(hex_color: str) -> str:
    """
    Klasifikasikan satu warna HEX ke dalam musim berdasarkan nilai HSV.
    Ini yang menentukan apakah sebuah warna baju cocok dengan skin tone pengguna.
    
    Returns: 'Spring' | 'Summer' | 'Autumn' | 'Winter'
    """
    rgb = hex_to_rgb(hex_color)
    r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
    
    # Konversi RGB ke HSV menggunakan OpenCV — OpenCV pakai format BGR, bukan RGB
    pixel = np.uint8([[[b, g, r]]])  # OpenCV uses BGR
    hsv = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0][0]
    h, s, v = float(hsv[0]), float(hsv[1]), float(hsv[2])
    
    # Normalisasi nilai HSV ke skala 0-1 agar lebih mudah dibandingkan
    h_norm = h / 179.0  # OpenCV Hue range: 0-179 (bukan 0-360)
    s_norm = s / 255.0
    v_norm = v / 255.0
    
    # --- Aturan Klasifikasi Musiman berdasarkan teori Personal Color Analysis ---
    
    # Warna sangat gelap (Value rendah) -> Winter (cool, deep, clear)
    if v_norm < 0.20:
        return "Winter"
    
    # Warna sangat terang/pucat (Value tinggi, Saturation rendah) -> Summer (cool, light, muted)
    if v_norm > 0.80 and s_norm < 0.20:
        return "Summer"
    
    # Warm Hues (merah, oranye, kuning): H = 0-30 & 150-179 di OpenCV
    is_warm_hue = (h <= 30) or (h >= 150)
    # Cool Hues (biru, hijau, ungu): H = 30-150
    is_cool_hue = (30 < h < 150)
    
    if is_warm_hue:
        if s_norm > 0.40 and v_norm > 0.55:
            return "Spring"   # Hangat, terang, cerah
        elif s_norm > 0.25 and v_norm <= 0.55:
            return "Autumn"   # Hangat, dalam, earthy
        elif s_norm <= 0.25:
            return "Summer"   # Warm muted -> diperlakukan sebagai Summer netral
        else:
            return "Spring"
    else:  # Cool hues
        if v_norm > 0.55 and s_norm < 0.50:
            return "Summer"   # Dingin, terang, soft
        elif v_norm > 0.55 and s_norm >= 0.50:
            return "Winter"   # Dingin, dalam, jewel tones
        elif v_norm <= 0.55 and s_norm >= 0.30:
            return "Autumn"   # Cool muted -> earthy
        else:
            return "Winter"   # Gelap dan dingin

# Tabel mapping: Skin Tone Level -> Musim yang cocok (primer dan sekunder)
SKIN_TONE_SEASON_MAP = {
    1: {  # Dark Skin -> cocok dengan warna cerah & kontras tinggi
        "primary": ["Autumn", "Winter"],
        "secondary": ["Spring"],
        "primary_boost": 1.0,
        "secondary_boost": 0.7,
    },
    2: {  # Fair / Kuning Langsat -> cocok dengan warna hangat & natural
        "primary": ["Spring", "Autumn"],
        "secondary": ["Summer"],
        "primary_boost": 1.0,
        "secondary_boost": 0.65,
    },
    3: {  # Light Skin -> cocok dengan warna dingin & lembut
        "primary": ["Summer", "Winter"],
        "secondary": ["Spring"],
        "primary_boost": 1.0,
        "secondary_boost": 0.6,
    },
}

# Musim yang HARUS dihindari untuk setiap level skin tone (diberi skor sangat rendah)
SKIN_TONE_AVOID_SEASONS = {
    1: ["Summer"],    # Kulit gelap hindari warna pastel/pucat
    2: ["Winter"],    # Kulit kuning langsat hindari warna terlalu dingin/gelap
    3: ["Autumn"],    # Kulit terang hindari warna terlalu earthy/hangat gelap
}

# Endpoint ini bisa dipanggil dengan POST /recommendations atau POST /recommendations/
@router.post("")
@router.post("/")
async def recommend_outfit(
    request: Request, 
    db: AsyncSession = Depends(get_db_session),
):
    start_time = time.time()
    
    # Ambil payload JSON dari body request, fallback ke dict kosong jika gagal parse
    try:
        payload = await request.json()
    except Exception:
        payload = {}
        
    # Ekstrak parameter dari payload, dengan nilai default yang aman
    target_gender = payload.get("gender", "pria").lower().strip()
    skin_tone_level = int(payload.get("skin_tone_level", 2))
    # Validasi skin_tone_level harus di antara 1-3, kalau tidak fallback ke 2 (Fair)
    if skin_tone_level not in [1, 2, 3]:
        skin_tone_level = 2
    skin_tone_id = payload.get("skin_tone_id")
    session_id = payload.get("session_id", "guest_session")
    top_k = int(payload.get("top_k", 12))
    
    # Ambil referensi warna RGB dari skin tone level pengguna
    user_rgb = SKIN_TONE_MAP.get(skin_tone_level, np.array([210, 180, 140]))
    
    # Jika ada skin_tone_id (dari hasil deteksi sebelumnya), ambil warna hex yang lebih presisi dari DB
    cnn_feature_vector = None
    if isinstance(skin_tone_id, int) or (isinstance(skin_tone_id, str) and skin_tone_id.isdigit()):
        try:
            detection = await db.get(SkinToneDetection, int(skin_tone_id))
            if detection:
                user_rgb = hex_to_rgb(detection.skin_tone_hex)
                
                # Load feature vector 1280-dim from detection (hasil CNN)
                if detection.feature_vector:
                    fv = detection.feature_vector
                    if isinstance(fv, str):
                        try:
                            fv = json.loads(fv)
                        except Exception:
                            pass
                    # Pastikan bentuknya list dan panjangnya 1280
                    if isinstance(fv, list) and len(fv) == 1280:
                        cnn_feature_vector = np.array(fv, dtype=np.float32)
        except Exception:
            pass

    logger.info("=" * 60)
    logger.info(f"[KNN v5.0] ENGINE START [{target_gender.upper()}] | Skin Level: {skin_tone_level}")
    logger.info("=" * 60)

    # Ambil semua produk yang sudah punya feature_vector (hasil ekstraksi CNN)
    # Produk tanpa feature_vector tidak bisa diproses KNN
    stmt_all = select(Product).where(Product.feature_vector.isnot(None))
    result_all = await db.execute(stmt_all)
    products_with_features = result_all.scalars().all()
    
    # Tentukan apakah pakai KNN atau fallback ke seasonal color saja
    # Minimal 10 produk dengan feature_vector agar KNN bisa bekerja
    use_knn = len(products_with_features) >= 10
    
    # Ambil produk sesuai gender (termasuk unisex) untuk fallback jika KNN tidak tersedia
    stmt = select(Product).where(Product.gender.in_([target_gender, 'unisex']))
    result = await db.execute(stmt)
    raw_products = result.scalars().all()

    verified_products = []
    missing_image_count = 0
    
    # Filter produk: isi field kosong dengan default, bersihkan URL gambar, skip produk tanpa gambar
    for p in raw_products:
        p.color = p.color if p.color else "#000000"
        p.price = p.price if p.price else 0.0
        p.name = p.name if p.name else "Unknown Product"
        
        # Bersihkan URL gambar dari format yang salah (hasil scraping Zalora)
        clean_url = sanitize_image_url(p.image_url) if p.image_url else ""
        p.image_url = clean_url
        
        # Produk tanpa gambar dilewati agar tidak tampil di frontend
        if not p.image_url:
            missing_image_count += 1
            continue

        verified_products.append(p)

    if not verified_products:
        raise HTTPException(status_code=404, detail=f"Katalog {target_gender} kosong.")

    # Ambil konfigurasi musim yang cocok/dihindari berdasarkan skin tone pengguna
    season_config = SKIN_TONE_SEASON_MAP.get(skin_tone_level, SKIN_TONE_SEASON_MAP[2])
    avoid_seasons = SKIN_TONE_AVOID_SEASONS.get(skin_tone_level, [])
    
    primary_seasons = season_config["primary"]
    secondary_seasons = season_config["secondary"]
    primary_boost = season_config["primary_boost"]
    secondary_boost = season_config["secondary_boost"]
    
    # Ambil list warna yang direkomendasikan oleh CNN classifier untuk skin tone ini
    recommended_hex_list = SKIN_TONE_RECOMMENDED_COLORS.get(skin_tone_level, ["#FFFFFF", "#000000"])
    recommended_rgb_list = [hex_to_rgb(h) for h in recommended_hex_list]

    logger.info(f"[Season] Primary: {primary_seasons} | Secondary: {secondary_seasons} | Avoid: {avoid_seasons}")

    scored_candidates = []
    season_stats = {"Spring": 0, "Summer": 0, "Autumn": 0, "Winter": 0}
    algorithm_ver = "v4.0-seasonal-color-analysis"

    if use_knn:
        # Lazy initialization KNN: hanya fit satu kali saat pertama kali dipanggil
        if knn_recommender._knn is None:
            feature_matrix = []
            product_ids = []
            product_categories = {}
            product_skin_compat = {}
            product_names = {}
            product_genders = {}
            
            for p in products_with_features:
                try:
                    feat = p.feature_vector
                    # Feature vector disimpan sebagai JSON string di DB, parse dulu
                    if isinstance(feat, str):
                        feat = json.loads(feat)
                    # Pastikan dimensi feature vector sesuai (1377-dim dari CNN+histogram)
                    if feat and len(feat) == 1377:
                        feature_matrix.append(feat)
                        product_ids.append(p.id)
                        product_categories[p.id] = p.category_id
                        
                        compat = p.skin_tone_compat
                        # skin_tone_compat juga disimpan sebagai JSON string, parse dulu
                        if isinstance(compat, str):
                            try:
                                compat = json.loads(compat)
                            except Exception:
                                compat = None
                        # Jika compat NULL atau bukan list valid, anggap cocok untuk semua skin tone
                        # Ini penting agar skin tone level 1 (Dark) dapat cukup rekomendasi
                        if not isinstance(compat, list) or len(compat) == 0:
                            compat = [1, 2, 3]
                        # Pastikan selalu ada fallback: hapus level yang tidak valid (bukan integer 1-3)
                        compat = [c for c in compat if isinstance(c, int) and 1 <= c <= 3]
                        if not compat:
                            compat = [1, 2, 3]
                        product_skin_compat[p.id] = compat
                        
                        product_names[p.id] = p.name or ""
                        product_genders[p.id] = p.gender.value if hasattr(p.gender, 'value') else str(p.gender)
                except Exception as e:
                    logger.warning(f"Error parsing feature for product {p.id}: {e}")
            
            # Fit KNN hanya jika ada minimal 10 produk yang bisa diproses
            if len(product_ids) >= 10:
                knn_recommender.fit(
                    feature_matrix=np.array(feature_matrix, dtype=np.float32),
                    product_ids=product_ids,
                    product_categories=product_categories,
                    product_skin_compat=product_skin_compat,
                    product_names=product_names,
                    product_genders=product_genders
                )

        # Jalankan KNN search jika sudah berhasil di-fit
        if knn_recommender._knn is not None:
            algorithm_ver = "v5.0-knn+seasonal"
            
            # Bangun query vector 96-dim dari warna kulit pengguna (HSV histogram)
            # Caranya: buat pixel 1x1 dengan warna kulit, konversi ke HSV, hitung histogram
            bgr_1x1 = np.zeros((1, 1, 3), dtype=np.uint8)
            bgr_1x1[0, 0] = [user_rgb[2], user_rgb[1], user_rgb[0]]
            hsv_1x1 = cv2.cvtColor(bgr_1x1, cv2.COLOR_BGR2HSV)
            
            bins = 32
            hists = []
            for ch in range(3):
                # Range Hue OpenCV: 0-180, Saturation & Value: 0-256
                ranges = [0, 180] if ch == 0 else [0, 256]
                hist = cv2.calcHist([hsv_1x1], [ch], None, [bins], ranges)
                hist = hist.flatten().astype(np.float32)
                total = hist.sum()
                # Normalisasi histogram agar total = 1 (probability distribution)
                if total > 0:
                    hist /= total
                hists.append(hist)
            skin_hist = np.concatenate(hists) # Hasilnya 96-dim (3 channel x 32 bins)
            
            # Pad ke 1377-dim agar dimensinya cocok dengan feature vector produk
            # Dimensi: [0:1280] = CNN features, [1280:1376] = histogram, [1376:1377] = padding/texture
            query_vector = np.zeros(1377, dtype=np.float32)
            
            # ISI CNN FEATURE VECTOR (Sangat Krusial untuk akurasi KNN)
            if cnn_feature_vector is not None:
                query_vector[0:1280] = cnn_feature_vector
            else:
                logger.warning("[KNN] cnn_feature_vector kosong! KNN hanya akan mencocokkan berdasar histogram.")
                
            query_vector[1280:1376] = skin_hist
            
            logger.info(f"[KNN] Query vector berdimensi {query_vector.shape} siap digunakan")
            norm = np.linalg.norm(query_vector)
            if norm > 0:
                query_vector /= norm
                
            # Cari kandidat produk paling dekat (ambil banyak dulu, nanti difilter diversity)
            candidates = knn_recommender.recommend(
                query_vector,
                skin_tone_level=skin_tone_level,
                top_k=max(50, top_k * 6),
                gender=target_gender,
                diversity_threshold=0.15,   # Threshold longgar agar slot outfit bisa lengkap
                target_slots=["atasan", "celana", "sepatu", "aksesori", "bawahan"]
            )
            
            # Fallback: jika hasil KNN terlalu sedikit, coba dengan threshold lebih longgar lagi
            if len(candidates) < top_k:
                logger.info(f"[KNN] Sedikit kandidat ({len(candidates)}) untuk skin_tone={skin_tone_level}, expand filter")
                candidates_expanded = knn_recommender.recommend(
                    query_vector,
                    skin_tone_level=skin_tone_level,
                    top_k=max(50, top_k * 6),
                    gender=target_gender,
                    diversity_threshold=0.10,
                    target_slots=["atasan", "celana", "sepatu", "aksesori", "bawahan"]
                )
                if len(candidates_expanded) > len(candidates):
                    candidates = candidates_expanded
            
            # Buat lookup dict agar pencarian produk berdasarkan ID lebih cepat (O(1))
            pid_to_product = {p.id: p for p in products_with_features}
            
            # Re-rank kandidat KNN menggunakan Seasonal Color Analysis
            # Ini yang menentukan urutan final rekomendasi
            for cand in candidates:
                p = pid_to_product.get(cand.product_id)
                if not p:
                    continue
                p.color = p.color if p.color else "#000000"
                p.price = p.price if p.price else 0.0
                p.name = p.name if p.name else "Unknown Product"
                p.image_url = sanitize_image_url(p.image_url) if p.image_url else ""
                try:
                    prod_rgb = hex_to_rgb(p.color)
                    # Klasifikasikan warna produk ke musim (Spring/Summer/Autumn/Winter)
                    product_season = classify_color_season(p.color)
                    season_stats[product_season] += 1
                    
                    # Skor musim berdasarkan skin tone (primer/sekunder/hindari)
                    season_score = 0.0
                    if product_season in primary_seasons:
                        season_score = 50.0 * primary_boost    # Skor maksimal
                    elif product_season in secondary_seasons:
                        season_score = 50.0 * secondary_boost  # Skor sedang
                    elif product_season in avoid_seasons:
                        season_score = 2.0                      # Sangat rendah (dihindari)
                    else:
                        season_score = 15.0                     # Musim netral
                        
                    # Hitung color_score: seberapa dekat warna produk dengan palet warna skin tone
                    distances = [np.linalg.norm(rec_rgb - prod_rgb) for rec_rgb in recommended_rgb_list]
                    best_distance = min(distances)
                    max_dist = 441.67
                    color_score = max(0.0, 50.0 - ((best_distance / max_dist) * 50.0))

                    # === SKIN TONE DIFFERENTIATOR ===
                    # Hitung jarak warna produk ke warna kulit referensi
                    # Produk yang warnanya terlalu mirip kulit (jarak dekat) dapat penalti
                    # Produk yang warnanya kontras/komplemen mendapat bonus
                    skin_ref_rgb = SKIN_TONE_MAP.get(skin_tone_level, np.array([210, 180, 140]))
                    dist_to_skin = np.linalg.norm(prod_rgb.astype(float) - skin_ref_rgb.astype(float))
                    
                    # Kontras ideal: warna produk harus berbeda dari warna kulit (jarak > 80)
                    # Jika terlalu mirip kulit (dist < 60) → penalti besar
                    # Jika kontras bagus (dist 80-200) → bonus
                    if skin_tone_level == 1:  # Dark: butuh warna cerah/kontras tinggi
                        if dist_to_skin > 150:
                            contrast_bonus = 20.0   # Kontras tinggi = sangat bagus
                        elif dist_to_skin > 80:
                            contrast_bonus = 10.0
                        elif dist_to_skin < 50:
                            contrast_bonus = -15.0  # Terlalu mirip kulit gelap = jelek
                        else:
                            contrast_bonus = 0.0
                    elif skin_tone_level == 2:  # Fair: butuh warna hangat/natural
                        if 60 < dist_to_skin < 180:
                            contrast_bonus = 12.0   # Kontras sedang = paling bagus untuk Fair
                        elif dist_to_skin < 40:
                            contrast_bonus = -10.0
                        else:
                            contrast_bonus = 5.0
                    else:  # Light (3): butuh warna lembut/pastel/dingin
                        if dist_to_skin > 100:
                            contrast_bonus = 8.0    # Warna kuat di kulit terang = cukup ok
                        elif 40 < dist_to_skin <= 100:
                            contrast_bonus = 15.0   # Kontras lembut = terbaik untuk Light
                        elif dist_to_skin < 30:
                            contrast_bonus = -12.0  # Terlalu pucat = tenggelam di kulit terang
                        else:
                            contrast_bonus = 0.0
                    
                    # Skor akhir = season + color palet + kontras kulit
                    final_score = season_score + color_score + contrast_bonus
                    
                    scored_candidates.append({
                        "product": p,
                        "score": float(final_score),
                        "season": product_season,
                    })
                except Exception:
                    continue

    # Fallback mode: jika KNN tidak tersedia, gunakan Seasonal Color Analysis saja
    if not use_knn or not scored_candidates:
        for p in verified_products:
            try:
                prod_rgb = hex_to_rgb(p.color)
                product_season = classify_color_season(p.color)
                season_stats[product_season] += 1
                
                season_score = 0.0
                if product_season in primary_seasons:
                    season_score = 50.0 * primary_boost
                elif product_season in secondary_seasons:
                    season_score = 50.0 * secondary_boost
                elif product_season in avoid_seasons:
                    season_score = 2.0
                else:
                    season_score = 15.0
                
                distances = [np.linalg.norm(rec_rgb - prod_rgb) for rec_rgb in recommended_rgb_list]
                best_distance = min(distances)
                max_dist = 441.67
                color_score = max(0.0, 50.0 - ((best_distance / max_dist) * 50.0))

                # Skin tone contrast differentiator (sama dengan KNN path)
                skin_ref_rgb = SKIN_TONE_MAP.get(skin_tone_level, np.array([210, 180, 140]))
                dist_to_skin = np.linalg.norm(prod_rgb.astype(float) - skin_ref_rgb.astype(float))
                if skin_tone_level == 1:
                    contrast_bonus = 20.0 if dist_to_skin > 150 else (10.0 if dist_to_skin > 80 else (-15.0 if dist_to_skin < 50 else 0.0))
                elif skin_tone_level == 2:
                    contrast_bonus = 12.0 if 60 < dist_to_skin < 180 else (-10.0 if dist_to_skin < 40 else 5.0)
                else:
                    contrast_bonus = 15.0 if 40 < dist_to_skin <= 100 else (8.0 if dist_to_skin > 100 else (-12.0 if dist_to_skin < 30 else 0.0))

                final_score = season_score + color_score + contrast_bonus
                
                scored_candidates.append({
                    "product": p, 
                    "score": float(final_score),
                    "season": product_season,
                })
            except Exception:
                continue

    # Urutkan semua kandidat dari skor tertinggi ke terendah
    scored_candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Diversity Selection dari 30 kandidat terbaik menggunakan max color distance
    # Prinsipnya: setiap produk yang dipilih harus warnanya berbeda dari yang sudah dipilih
    best_candidates = scored_candidates[:30]
    if not best_candidates:
        top_hits = []
    else:
        # Mulai dengan kandidat skor tertinggi
        selected = [best_candidates[0]]
        while len(selected) < min(top_k, len(best_candidates)):
            best_candidate = None
            max_min_dist = -1.0
            for cand in best_candidates:
                if cand in selected:
                    continue
                cand_rgb = hex_to_rgb(cand['product'].color)
                # Hitung jarak minimum dari kandidat ini ke semua yang sudah dipilih
                min_dist = min(np.linalg.norm(cand_rgb - hex_to_rgb(s['product'].color)) for s in selected)
                # Pilih kandidat yang paling jauh warnanya (paling berbeda = paling diverse)
                if min_dist > max_min_dist:
                    max_min_dist = min_dist
                    best_candidate = cand
                elif abs(min_dist - max_min_dist) < 1e-5:
                    # Jika jarak hampir sama, pilih yang punya skor lebih tinggi
                    if best_candidate is None or cand['score'] > best_candidate['score']:
                        best_candidate = cand
            if best_candidate is not None:
                selected.append(best_candidate)
            else:
                break
        top_hits = selected
    
    # Urutkan kembali hasil final berdasarkan skor (yang paling relevan tetap di atas)
    top_hits.sort(key=lambda x: x['score'], reverse=True)

    outfit_items = []
    for h in top_hits:
        p = h['product']
        name_lower = p.name.lower() if p.name else ""
        
        # Tentukan slot outfit (atasan/celana/sepatu/aksesori) berdasarkan category_id
        slot = "aksesori"
        if p.category_id is not None:
            cat_map = {
                5: "atasan", 6: "atasan", 8: "atasan",
                7: "celana", 9: "celana",
                10: "sepatu", 11: "sepatu",
                12: "aksesori", 13: "aksesori", 14: "aksesori", 15: "aksesori", 16: "aksesori"
            }
            slot = cat_map.get(p.category_id, "aksesori")

        # Override slot berdasarkan kata kunci di nama produk (lebih akurat dari category_id)
        if any(keyword in name_lower for keyword in ["kaos", "hoodie", "kemeja", "jaket", "sweater", "blouse", "tunik", "gamis", "tshirt", "t-shirt", "outer", "atasan"]):
            slot = "atasan"
        elif any(keyword in name_lower for keyword in ["celana", "chino", "jeans"]):
            slot = "celana"
        elif any(keyword in name_lower for keyword in ["rok", "bawahan"]):
            slot = "bawahan"
        elif any(keyword in name_lower for keyword in ["sepatu", "sandal", "sneakers", "boots"]):
            slot = "sepatu"
        elif any(keyword in name_lower for keyword in ["kaus kaki", "ikat pinggang", "dasi", "tas", "jam tangan", "hijab", "aksesori", "pashmina", "khimar"]):
            slot = "aksesori"

        outfit_items.append(
            OutfitSetItem(
                product=ProductOut.model_validate(p), 
                knn_score=h['score'], 
                category_slot=slot
            )
        )

    # Hitung diversity score: rata-rata jarak warna antar semua produk yang direkomendasikan
    if len(outfit_items) < 2:
        diversity_score = 1.0
    else:
        colors_rgb = []
        for item in outfit_items:
            color_hex = item.product.color
            colors_rgb.append(hex_to_rgb(color_hex))
        
        # Hitung pairwise distance semua kombinasi warna
        distances = []
        for i in range(len(colors_rgb)):
            for j in range(i + 1, len(colors_rgb)):
                dist = np.linalg.norm(colors_rgb[i] - colors_rgb[j])
                distances.append(dist / 441.67)  # Normalize ke 0-1
        diversity_score = float(np.mean(distances))

    execution_time = time.time() - start_time
    logger.info("-" * 60)
    logger.info(f"[DONE] Execution: {execution_time:.2f}s | Total Products: {len(raw_products)} | Recommendations: {len(outfit_items)}")
    logger.info(f"[Season Stats] Spring={season_stats['Spring']} Summer={season_stats['Summer']} Autumn={season_stats['Autumn']} Winter={season_stats['Winter']}")
    if top_hits:
        logger.info(f"[Top-1] {top_hits[0]['product'].name} ({top_hits[0]['season']}, Score={top_hits[0]['score']:.1f})")
    logger.info("-" * 60)

    return RecommendationResponse(
        message="Rekomendasi biometrik berhasil diverifikasi",
        data=RecommendationOut(
            id=1, 
            session_id=session_id, 
            outfit_set=outfit_items,
            diversity_score=diversity_score,
            skin_tone_level=skin_tone_level, 
            algorithm_ver=algorithm_ver, 
            created_at=datetime.now()
        ),
    )

# --- ENDPOINT 3: FEEDBACK DAN PEMBELAJARAN SISTEM ---
class FeedbackRequest(BaseModel):
    session_id: str
    product_id: int
    is_accepted: bool
    feedback_score: int

@router.post("/feedback")
async def submit_feedback(body: FeedbackRequest, db: AsyncSession = Depends(get_db_session)):
    """
    Endpoint untuk menyimpan rating Suka/Kurang dari user.
    Data ini bisa dipakai di masa depan untuk retraining model.
    """
    try:
        # Cari data rekomendasi berdasarkan session_id — ambil yang paling terakhir
        stmt = select(Recommendation).where(Recommendation.session_id == body.session_id).order_by(Recommendation.id.desc()).limit(1)
        result = await db.execute(stmt)
        rec = result.scalar_one_or_none()

        if rec:
            # Update field feedback di database
            rec.is_accepted = 1 if body.is_accepted else 0
            rec.feedback_score = body.feedback_score
            
            await db.commit()
            return {"message": "[OK] Feedback AI berhasil disimpan ke Database!"}
        else:
            # Jika tidak ada sesi yang cocok, tetap terima feedback (mode tamu/tanpa login)
            return {"message": "[OK] Feedback diterima (Mode Fallback / Tanpa Session)"}
            
    except Exception as e:
        # Rollback transaksi jika ada error agar database tidak setengah-setengah
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan feedback: {str(e)}")
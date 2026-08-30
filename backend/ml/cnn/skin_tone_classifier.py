"""
OutfitAR - Skin Tone Classifier (V3.0 - 3 Classes Sync)
Deteksi skin tone menggunakan CNN EfficientNet-B0 & MediaPipe Segmentation
Skala tersinkronisasi dengan Dataset Kaggle: 1=Dark, 2=Fair, 3=Light
"""
from __future__ import annotations

import cv2
import numpy as np
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from loguru import logger

# MediaPipe import dibuat lazy agar server tetap bisa start
# meski TensorFlow DLL diblokir Windows Application Control Policy
_MEDIAPIPE_AVAILABLE = True
if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_PROJECT_ID'):
    _MEDIAPIPE_AVAILABLE = False
    logger.warning("[SkinTone] Menjalankan di Railway. MediaPipe dinonaktifkan untuk menghemat RAM.")

try:
    if not _MEDIAPIPE_AVAILABLE:
        raise ImportError("Dinonaktifkan oleh environment Railway")
    import mediapipe as mp
except Exception as _mp_err:
    logger.warning(f"[WARN] MediaPipe tidak bisa diload: {_mp_err}. Face segmentation dinonaktifkan.")
    mp = None
    _MEDIAPIPE_AVAILABLE = False

# TensorFlow/EfficientNet import dibuat lazy
import os

_TF_AVAILABLE = True
if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_PROJECT_ID'):
    _TF_AVAILABLE = False
    logger.warning('[SkinTone] Menjalankan di Railway (Low RAM). TensorFlow CNN dimatikan. Fallback ke HSV Analysis.')

try:
    if not _TF_AVAILABLE:
        raise ImportError('Dinonaktifkan oleh environment Railway')
    from ml.cnn.efficientnet_backbone import (
        build_skin_tone_classifier,
        load_model_weights,
        preprocess_image,
    )
    _TF_AVAILABLE = True
except Exception as _tf_err:
    logger.warning(f"[WARN] TensorFlow/EfficientNet tidak bisa diload: {_tf_err}. CNN inference dinonaktifkan.")
    build_skin_tone_classifier = None
    load_model_weights = None
    preprocess_image = None
    _TF_AVAILABLE = False

# DeepFace import dibuat lazy agar server tetap bisa start
# meski ada masalah dependency (e.g. gdown metadata missing)
_DEEPFACE_AVAILABLE = True
if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_PROJECT_ID'):
    _DEEPFACE_AVAILABLE = False
    logger.warning("[SkinTone] Menjalankan di Railway. DeepFace dinonaktifkan untuk menghemat RAM.")

try:
    if not _DEEPFACE_AVAILABLE:
        raise ImportError("Dinonaktifkan oleh environment Railway")
    from deepface import DeepFace
except Exception as _df_err:
    logger.warning(f"[WARN] DeepFace tidak bisa diload: {_df_err}. Fitur face analysis dinonaktifkan.")
    DeepFace = None
    _DEEPFACE_AVAILABLE = False

# ----------------------------------------------------------
# Konstanta Skin Tone (Sinkron dengan folder dataset Anda)
# Index Keras Alphabetical: 0='dark', 1='fair', 2='light'
# Kita mapping ke Level: 1='Dark', 2='Fair', 3='Light'
# ----------------------------------------------------------
SKIN_TONE_LABELS = {
    1: "Gelap (Dark)",
    2: "Menengah / Kuning Langsat (Fair)",
    3: "Terang (Light)",
}

# Warna yang direkomendasikan per skin tone (Seasonal Color Analysis)
# Setiap level memiliki palet yang BENAR-BENAR BERBEDA agar rekomendasi tidak sama
SKIN_TONE_RECOMMENDED_COLORS = {
    1: [  # Dark Skin -> Autumn & Winter: warm deep, cool deep, high contrast
        "#FFFFFF", "#F1C40F", "#E74C3C", "#2ECC71", "#E8DAEF",
        "#FF6347", "#FFD700", "#00CED1", "#FF69B4", "#7B68EE",
        "#FF4500", "#ADFF2F", "#87CEEB", "#DA70D6", "#F0E68C",
    ],
    2: [  # Fair / Kuning Langsat -> Spring & Autumn: warm light, warm deep, natural
        "#87CEEB", "#654321", "#808080", "#800000", "#808000", 
        "#800080", "#FFA500", "#FFFDD0", "#FFB6C1",
        "#FFFF00", "#B2AC88", "#000080", "#E0B0FF",
        "#D2691E", "#CD853F",
    ],
    3: [  # Light Skin -> Summer & Winter: cool light, cool deep, jewel tones
        "#1A252F", "#8E44AD", "#C0392B", "#16A085", "#2980B9",
        "#6C3483", "#1F618D", "#148F77", "#922B21", "#7D3C98",
        "#2471A3", "#117A65", "#A93226", "#5B2C6F", "#1A5276",
    ],
}

# Warna yang sebaiknya dihindari per skin tone
SKIN_TONE_AVOID_COLORS = {
    1: ["#212121", "#000000", "#1A237E", "#17202A", "#0D0D0D"],  # Terlalu gelap untuk kulit gelap
    2: ["#0D0D0D", "#1A1A2E", "#16213E", "#1B1B2F", "#0F3460"],  # Terlalu dingin/gelap untuk kuning langsat
    3: ["#F8F9FA", "#FFFFFF", "#FFF9C4", "#E5E7E9", "#FDFEFE"],  # Terlalu pucat untuk kulit terang
}

# Inisialisasi MediaPipe Solutions (hanya jika tersedia)
# MediaPipe >= 0.10 menghapus mp.solutions, diganti mp.tasks
# Gunakan hasattr agar server tidak crash di versi baru
if _MEDIAPIPE_AVAILABLE and mp is not None and hasattr(mp, "solutions"):
    mp_face_detection       = mp.solutions.face_detection
    mp_selfie_segmentation  = mp.solutions.selfie_segmentation
else:
    # Fallback None: MediaPipe tidak tersedia atau versi >= 0.10 (tanpa solutions)
    mp_face_detection       = None
    mp_selfie_segmentation  = None
    if _MEDIAPIPE_AVAILABLE:
        logger.warning("[WARN] MediaPipe >= 0.10 terdeteksi: mp.solutions tidak tersedia. Face detection via MediaPipe dinonaktifkan. Pakai fallback OpenCV Haar Cascade.")


@dataclass
class SkinToneResult:
    # Dataclass untuk bungkus hasil deteksi skin tone secara rapi
    level: int                          
    label: str
    hex_color: str
    confidence: float
    recommended_colors: list[str]
    avoid_colors: list[str]
    feature_vector: list[float]
    gender: str = "pria" # default fallback

class SkinToneClassifier:
    def __init__(self, weights_path: Optional[str | Path] = None) -> None:
        logger.info("[SkinTone] Inisialisasi SkinToneClassifier (3 Classes)...")

        # Load CNN model (hanya jika TF tersedia)
        self._model = None
        self._feature_extractor = None
        if _TF_AVAILABLE and build_skin_tone_classifier is not None:
            self._model = build_skin_tone_classifier(num_classes=3)
            if weights_path:
                # Load bobot hasil training kalau ada
                self._model = load_model_weights(self._model, weights_path)
        else:
            logger.warning("[SkinTone] TensorFlow tidak tersedia - CNN inference dinonaktifkan.")

        # Inisialisasi MediaPipe (hanya jika tersedia)
        self._face_detector = None
        self._segmentation = None
        if _MEDIAPIPE_AVAILABLE and mp_face_detection is not None:
            # model_selection=0: model ringan (jarak dekat)
            self._face_detector = mp_face_detection.FaceDetection(
                model_selection=0,
                min_detection_confidence=0.5,
            )
            # model_selection=1: model selfie segmentation yang lebih akurat
            self._segmentation = mp_selfie_segmentation.SelfieSegmentation(
                model_selection=1
            )
        else:
            logger.warning("[SkinTone] MediaPipe tidak tersedia - face detection dinonaktifkan.")

        logger.info("[SkinTone] Classifier siap (TF={}, MediaPipe={})".format(_TF_AVAILABLE, _MEDIAPIPE_AVAILABLE))

    def detect(self, image_bgr: np.ndarray) -> SkinToneResult:
        # Validasi input sebelum diproses
        if image_bgr is None or image_bgr.size == 0:
            raise ValueError("Gambar input tidak valid")
        if image_bgr.shape[0] < 10 or image_bgr.shape[1] < 10:
            raise ValueError("Gambar terlalu kecil")

        try:
            # Pipeline analisis: crop wajah -> masking kulit -> prediksi CNN -> analisis HSV
            face_crop = self._extract_face_region(image_bgr)
            skin_only_bgr, skin_mask = self._apply_skin_mask(face_crop)
            
            hsv_level = self._analyze_hsv(skin_only_bgr, skin_mask)
            hex_color = self._extract_dominant_skin_color(skin_only_bgr, skin_mask)
            
            if self._model is not None:
                cnn_probs, feature_vec = self._predict_cnn(face_crop)
                # Gabungkan hasil CNN + HSV untuk prediksi akhir
                skin_tone_level, confidence = self._ensemble_prediction(cnn_probs, hsv_level)
            else:
                skin_tone_level = hsv_level
                confidence = 0.85
                feature_vec = []
        except Exception as e:
            raise ValueError(f"Proses analisis wajah gagal: {str(e)}")

        # ==========================================
        # TAMBAHAN BARU: Deteksi Gender Otomatis
        # ==========================================
        detected_gender = "pria"
        try:
            if DeepFace is None:
                logger.warning("[SkinTone] DeepFace tidak tersedia. Menggunakan gender default.")
            else:
                # Gunakan DeepFace pada area wajah untuk deteksi gender
                # enforce_detection=False karena gambar sudah dipotong di wajah
                face_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                df_result = DeepFace.analyze(
                    img_path=face_rgb, 
                    actions=['gender'], 
                    enforce_detection=False,
                    silent=True
                )
                # Hasil DeepFace kembalikan list of dict atau dict. Jika multiple faces, ini list.
                if isinstance(df_result, list):
                    df_result = df_result[0]
                
                # DeepFace gender format { "Woman": 99.9, "Man": 0.1 } -> kita ambil dominan
                dominant_gender = df_result.get('dominant_gender', 'Man')
                if dominant_gender == 'Woman':
                    detected_gender = "wanita"
                else:
                    detected_gender = "pria"
                logger.info(f"[SkinTone] Deteksi Gender: {detected_gender.upper()} ({df_result.get('gender', {})})")
        except Exception as e:
            logger.warning(f"[SkinTone] Deteksi Gender DeepFace gagal: {e}")

        # Bungkus semua hasil ke dalam SkinToneResult
        return SkinToneResult(
            level=skin_tone_level,
            label=SKIN_TONE_LABELS[skin_tone_level],
            hex_color=hex_color,
            confidence=float(confidence),
            recommended_colors=SKIN_TONE_RECOMMENDED_COLORS[skin_tone_level],
            avoid_colors=SKIN_TONE_AVOID_COLORS[skin_tone_level],
            feature_vector=[float(v) for v in feature_vec],
            gender=detected_gender,
        )

    def _extract_face_region(self, image_bgr: np.ndarray) -> np.ndarray:
        h, w = image_bgr.shape[:2]

        # Coba pakai MediaPipe jika tersedia (lebih akurat)
        if self._face_detector is not None:
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            results = self._face_detector.process(image_rgb)
            if results.detections:
                det = results.detections[0]
                bbox = det.location_data.relative_bounding_box
                margin_x = bbox.width * 0.1
                margin_y = bbox.height * 0.2
                x1 = max(0, int((bbox.xmin - margin_x) * w))
                y1 = max(0, int((bbox.ymin - margin_y) * h))
                x2 = min(w, int((bbox.xmin + bbox.width + margin_x) * w))
                y2 = min(h, int((bbox.ymin + bbox.height + margin_y) * h))
                face = image_bgr[y1:y2, x1:x2]
                if face.size > 0:
                    return face

        # Fallback: OpenCV Haar Cascade (tidak butuh MediaPipe)
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        if len(faces) > 0:
            # Ambil wajah terbesar (orang paling dekat kamera)
            faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            x, y, fw, fh = faces[0]
            margin = int(min(fw, fh) * 0.15)
            x1 = max(0, x - margin)
            y1 = max(0, y - margin)
            x2 = min(w, x + fw + margin)
            y2 = min(h, y + fh + margin)
            face = image_bgr[y1:y2, x1:x2]
            if face.size > 0:
                return face

        # Last resort: crop area tengah gambar
        cy, cx = h // 2, w // 2
        size = min(h, w) // 3
        return image_bgr[cy - size:cy + size, cx - size:cx + size]

    def _apply_skin_mask(self, face_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        # Coba pakai MediaPipe Selfie Segmentation jika tersedia
        if self._segmentation is not None:
            face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
            results = self._segmentation.process(face_rgb)
            condition = np.stack((results.segmentation_mask,) * 3, axis=-1) > 0.5
            bg_image = np.zeros(face_bgr.shape, dtype=np.uint8)
            skin_only = np.where(condition, face_bgr, bg_image)
            return skin_only, results.segmentation_mask

        # Fallback: HSV skin color range detection (tanpa MediaPipe)
        # Deteksi warna kulit berdasarkan rentang HSV yang umum untuk warna kulit manusia
        face_hsv = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2HSV)
        # Rentang HSV untuk warna kulit (mencakup semua tone dari gelap ke terang)
        lower_skin = np.array([0,  15, 40],  dtype=np.uint8)
        upper_skin = np.array([25, 255, 255], dtype=np.uint8)
        mask_hsv = cv2.inRange(face_hsv, lower_skin, upper_skin)

        # Bersihkan noise kecil dari mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_hsv = cv2.morphologyEx(mask_hsv, cv2.MORPH_OPEN,  kernel)
        mask_hsv = cv2.morphologyEx(mask_hsv, cv2.MORPH_DILATE, kernel)

        # Konversi mask ke float 0.0-1.0 agar kompatibel dengan _analyze_hsv
        mask_float = (mask_hsv / 255.0).astype(np.float32)
        bg_image   = np.zeros(face_bgr.shape, dtype=np.uint8)
        skin_only  = cv2.bitwise_and(face_bgr, face_bgr, mask=mask_hsv)
        return skin_only, mask_float

    def _predict_cnn(self, face_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        # Konversi BGR ke RGB sebelum masuk model
        face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
        input_tensor = preprocess_image(face_rgb)

        # Prediksi probabilitas kelas
        probs = self._model.predict(input_tensor, verbose=0)[0]   # (num_classes,)

        # Bangun intermediate model sekali (lazy) untuk ekstrak 1280-dim feature
        # Melewati preprocessing yang sama persis dengan saat training
        if self._feature_extractor is None:
            from tensorflow import keras as _keras
            # Potong model sampai sebelum head_dense untuk dapat raw 1280-dim feature
            self._feature_extractor = _keras.Model(
                inputs=self._model.input,
                outputs=self._model.get_layer("head_dense").input,
                name="feature_extractor_1280",
            )
            logger.debug("[SkinTone] Feature extractor intermediate model dibangun")

        feature_vec = self._feature_extractor.predict(input_tensor, verbose=0)[0]  # (1280,)
        return probs, feature_vec

    def _analyze_hsv(self, skin_bgr: np.ndarray, skin_mask: np.ndarray) -> int:
        # Analisis kecerahan kulit menggunakan channel V (Value) di HSV
        face_hsv = cv2.cvtColor(skin_bgr, cv2.COLOR_BGR2HSV)
        # Ambil hanya pixel yang termasuk area kulit (mask > 0.5)
        valid_pixels = face_hsv[skin_mask > 0.5]
        
        # Kalau tidak ada pixel valid, default ke Fair (level 2)
        if len(valid_pixels) == 0: return 2

        # Rata-rata channel V (kecerahan), range 0-255
        avg_value = float(np.mean(valid_pixels[:, 2]))

        # Mapping ke 3 Level: 1 (Dark), 2 (Fair), 3 (Light)
        if avg_value >= 150:   return 3 # Light
        elif avg_value >= 90:  return 2 # Fair
        else:                  return 1 # Dark

    def _ensemble_prediction(self, cnn_probs: np.ndarray, hsv_level: int) -> Tuple[int, float]:
        # Keras Output: 0=dark, 1=fair, 2=light. Kita tambah 1 agar jadi level 1,2,3
        cnn_idx = int(np.argmax(cnn_probs))
        cnn_level = cnn_idx + 1 
        cnn_confidence = float(cnn_probs[cnn_idx])

        if cnn_level == hsv_level:
            # CNN dan HSV sepakat → boost confidence sedikit
            return cnn_level, min(1.0, cnn_confidence * 1.15)
        else:
            # Tidak sepakat → gabungkan dengan bobot CNN 70%, HSV 30%
            final_level = int((cnn_level * 0.7) + (hsv_level * 0.3) + 0.5)
            final_level = max(1, min(3, final_level))  # Clamp ke range 1-3
            return final_level, cnn_confidence * 0.8   # Confidence dikurangi karena tidak konsisten

    def _extract_dominant_skin_color(self, skin_bgr: np.ndarray, skin_mask: np.ndarray) -> str:
        # Ambil pixel valid (area kulit saja)
        valid_pixels = skin_bgr[skin_mask > 0.5].astype(np.float32)
        # Kalau kurang dari 10 pixel, return warna default
        if len(valid_pixels) < 10: return "#D4A574" 

        # Batasi sample agar K-Means tidak terlalu lama
        if len(valid_pixels) > 5000:
            rng = np.random.default_rng(42)
            rng.shuffle(valid_pixels)
            valid_pixels = valid_pixels[:5000]

        # K-Means 2 cluster untuk cari warna dominan kulit
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        cv2.setRNGSeed(42)  # Seed biar hasilnya reproducible
        _, labels, centers = cv2.kmeans(valid_pixels, 2, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

        # Pilih cluster dengan jumlah pixel terbanyak sebagai warna dominan
        counts = np.bincount(labels.flatten())
        dominant_bgr = centers[np.argmax(counts)].astype(int)
        # Konversi BGR → RGB → HEX
        r, g, b = int(dominant_bgr[2]), int(dominant_bgr[1]), int(dominant_bgr[0])
        return f"#{r:02X}{g:02X}{b:02X}"

    def close(self) -> None:
        # Tutup resource MediaPipe biar tidak memory leak
        if hasattr(self, "_face_detector"): self._face_detector.close()
        if hasattr(self, "_segmentation"): self._segmentation.close()


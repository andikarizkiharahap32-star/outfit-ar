"""
OutfitAR - AR Virtual Try-On Service
Menggabungkan MediaPipe Pose dan U-Net untuk overlay baju virtual ke badan pengguna secara realtime.
"""
from __future__ import annotations
import asyncio
import base64
import time
import sys
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from loguru import logger

# === ANTI-PUYENG IMPORT SYSTEM (DEFINISIKAN DULU) ===
# Pendekatan fallback untuk MediaPipe karena instalasi di Windows sering bermasalah
# antara import langsung vs via python.solutions
mp_pose = None
mp_drawing = None
mp_selfie_seg = None

try:
    import mediapipe as mp
    # Coba Jalur A (Standard)
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    mp_selfie_seg = mp.solutions.selfie_segmentation
    logger.info("✅ MediaPipe Solutions loaded via Path A")
except (AttributeError, ImportError):
    try:
        # Coba Jalur B (Direct Sub-modules) - ini sering berguna di env Anaconda/Miniconda
        import mediapipe.python.solutions.pose as mp_pose
        import mediapipe.python.solutions.drawing_utils as mp_drawing
        import mediapipe.python.solutions.selfie_segmentation as mp_selfie_seg
        logger.info("✅ MediaPipe Solutions loaded via Path B")
    except Exception as e:
        logger.error(f"❌ KEDUA JALUR GAGAL! System akan error saat init. Detail: {e}")

from ml.ar.unet_model import UNetInference

@dataclass
class PoseKeypoints:
    # Simpan koordinat bahu, pinggul, dan lutut untuk perhitungan skala & posisi baju
    left_shoulder: Optional[tuple[float, float, float]] = None
    right_shoulder: Optional[tuple[float, float, float]] = None
    left_hip: Optional[tuple[float, float, float]] = None
    right_hip: Optional[tuple[float, float, float]] = None
    left_knee: Optional[tuple[float, float, float]] = None
    right_knee: Optional[tuple[float, float, float]] = None
    visibility: float = 0.0

@dataclass
class ARRenderResult:
    # Hasil akhir dari satu cycle rendering
    frame_bgr: np.ndarray        # Frame yang sudah ditumpuk baju (gambar OpenCV)
    mask: np.ndarray             # Masker hitam-putih area baju
    pose_detected: bool          # Apakah ada orang/pose terdeteksi di frame
    render_time_ms: float        # Waktu komputasi untuk memantau performa FPS
    keypoints: Optional[PoseKeypoints] = None

class VirtualTryOnEngine:
    def __init__(
        self,
        unet_weights: Optional[str] = None,
        backbone: str = "efficientnet",
        target_fps: int = 30,
    ) -> None:
        logger.info("[AR] Inisialisasi VirtualTryOnEngine...")
        
        # Validasi sebelum inisialisasi agar server tidak mati (NameError) di tengah jalan
        if mp_pose is None:
            logger.critical("🚨 MediaPipe TIDAK TERINSTAL DENGAN BENAR. Silakan ketik: pip install mediapipe")
            raise ImportError("MediaPipe components are missing.")

        # Inisiasi CNN U-Net untuk mask generation
        self._unet = UNetInference(weights_path=unet_weights)

        # Inisiasi detektor kerangka manusia (MediaPipe Pose)
        # model_complexity=1 agar FPS tetap tinggi tapi akurasi cukup bagus
        self._pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        # Inisiasi fallback segmentation jika U-Net gagal
        self._selfie_seg = mp_selfie_seg.SelfieSegmentation(model_selection=1)
        self._target_fps = target_fps
        self._frame_interval = 1.0 / target_fps
        logger.info("[AR] Engine siap.")

    def render_frame(self, frame_bgr, clothing_bgr, product_id, use_unet=True):
        """
        Fungsi utama untuk memproses satu frame kamera.
        Alur: Deteksi Bahu -> Bikin Masker Badan -> Pasang Baju -> Tumpuk ke Frame
        """
        t_start = time.perf_counter()
        
        # 1. Deteksi koordinat kerangka tubuh
        keypoints = self._detect_pose(frame_bgr)
        
        # 2. Hasilkan mask putih area baju (U-Net) atau full badan (Selfie Seg fallback)
        mask = self._unet.predict_mask(frame_bgr) if use_unet else self._selfie_segment(frame_bgr)
        
        # 3. Sesuaikan ukuran baju (warp) berdasarkan lebar bahu dari pose
        clothing_warped = self._warp_clothing(clothing_bgr, frame_bgr.shape, keypoints)

        # 4. Terapkan blending alpha jika orang terdeteksi
        if keypoints is None:
            result_frame = frame_bgr
        else:
            result_frame = self._unet.apply_clothing_overlay(frame_bgr, clothing_warped, mask, alpha=0.88)

        # Kembalikan hasil lengkap
        return ARRenderResult(
            frame_bgr=result_frame, mask=mask, pose_detected=keypoints is not None,
            render_time_ms=round((time.perf_counter() - t_start) * 1000, 2),
            keypoints=keypoints
        )

    async def stream_frames(self, websocket, clothing_bgr, product_id, cap):
        """
        Fungsi ini dipakai untuk membaca dari webcam PC lokal.
        (Saat ini tidak digunakan karena input kamera pakai HP via WebSocket di router)
        """
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret: break
            try:
                result = self.render_frame(frame, clothing_bgr, product_id)
                # Encode ke jpg lalu base64 sebelum kirim
                _, buffer = cv2.imencode(".jpg", result.frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_b64 = base64.b64encode(buffer).decode("utf-8")
                
                await websocket.send_json({
                    "type": "ar_frame", "frame": frame_b64, "pose_detected": result.pose_detected,
                    "render_time_ms": result.render_time_ms, "frame_count": frame_count
                })
                frame_count += 1
                
                # Jaga agar FPS stabil, tidak menguras CPU
                await asyncio.sleep(self._frame_interval)
            except Exception as exc:
                logger.error(f"Stream Error: {exc}")
                break

    def _detect_pose(self, frame_bgr):
        # Konversi BGR OpenCV ke RGB karena MediaPipe mintanya RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self._pose.process(frame_rgb)
        
        # Kalau tidak ada orang, return None
        if not results.pose_landmarks: return None
        
        # Ekstrak titik-titik (landmarks) dari normalize (0-1) ke pixel absolute (0-width/height)
        lm = results.pose_landmarks.landmark
        h, w = frame_bgr.shape[:2]
        get_p = lambda i: (lm[i].x * w, lm[i].y * h, lm[i].z)
        
        return PoseKeypoints(
            left_shoulder=get_p(mp_pose.PoseLandmark.LEFT_SHOULDER),
            right_shoulder=get_p(mp_pose.PoseLandmark.RIGHT_SHOULDER),
            left_hip=get_p(mp_pose.PoseLandmark.LEFT_HIP),
            right_hip=get_p(mp_pose.PoseLandmark.RIGHT_HIP),
            visibility=float(lm[mp_pose.PoseLandmark.LEFT_SHOULDER].visibility)
        )

    def _selfie_segment(self, frame_bgr):
        # Fallback kalau U-Net mati: Pisahkan seluruh badan orang dari background
        return self._selfie_seg.process(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)).segmentation_mask

    def _warp_clothing(self, clothing_bgr, frame_shape, keypoints):
        """
        Menyesuaikan ukuran gambar baju mentah (persegi) agar pas dengan ukuran tubuh di layar.
        """
        h, w = frame_shape[:2]
        # Kalau tidak ada bahu terdeteksi, stretch baju sebesar frame (fallback kasar)
        if not keypoints or not keypoints.left_shoulder: return cv2.resize(clothing_bgr, (w, h))
        
        # Hitung jarak bahu (shoulder width / sw) dan titik tengah bahu (cx)
        ls, rs = keypoints.left_shoulder, keypoints.right_shoulder
        sw = abs(rs[0] - ls[0])
        cx = (ls[0] + rs[0]) / 2
        
        # Tentukan bounding box baju:
        # Lebar baju = jarak bahu dikali 1.4 (x 0.7 ke kiri dan kanan)
        # Panjang baju = posisi bahu sampai 1.5x jarak bahu ke bawah
        x1, y1 = max(0, int(cx - sw * 0.7)), max(0, int(ls[1] - sw * 0.2))
        x2, y2 = min(w, int(cx + sw * 0.7)), min(h, int(ls[1] + sw * 1.5))
        
        # Gambar baju di atas canvas hitam kosong pada koordinat bbox yang dihitung tadi
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        canvas[y1:y2, x1:x2] = cv2.resize(clothing_bgr, (max(1, x2-x1), max(1, y2-y1)))
        return canvas

    def close(self) -> None:
        # Bersihkan memori C++ MediaPipe
        if self._pose: self._pose.close()
        if self._selfie_seg: self._selfie_seg.close()
        logger.info("[AR] Engine ditutup")
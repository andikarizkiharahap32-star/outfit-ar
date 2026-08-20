"""
OutfitAR - Feature Extractor
Mengekstrak feature vector dari gambar produk outfit
menggunakan EfficientNet-B0 untuk KNN recommendation engine
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from loguru import logger

from ml.cnn.efficientnet_backbone import build_feature_extractor, preprocess_image

# Dimensi feature vector EfficientNet-B0
FEATURE_DIM = 1280


class OutfitFeatureExtractor:
    """
    Mengekstrak multi-modal features dari gambar produk:
        1. CNN Features   : EfficientNet-B0 deep features (1280-dim)
        2. Color Features : HSV histogram (96-dim)
        3. Texture Score  : LBP-based texture scalar

    Total feature = 1280 + 96 + 1 = 1377 dimensi
    (atau hanya CNN jika lightweight mode)
    """

    def __init__(self, use_color: bool = True, use_texture: bool = True) -> None:
        logger.info("[FeatureExtractor] Inisialisasi...")
        self._cnn = build_feature_extractor()
        self._use_color = use_color
        self._use_texture = use_texture
        logger.info("[FeatureExtractor] Siap. Dimensi output: {}", self._feature_dim)

    @property
    def _feature_dim(self) -> int:
        dim = FEATURE_DIM
        if self._use_color:
            dim += 96    # 32 bins × 3 channel HSV
        if self._use_texture:
            dim += 1
        return dim

    def extract(self, image_bgr: np.ndarray) -> np.ndarray:
        """
        Ekstrak feature vector dari gambar produk.

        Args:
            image_bgr: Gambar BGR (OpenCV), shape (H, W, 3)

        Returns:
            Feature vector shape (feature_dim,) dtype float32
        """
        if image_bgr is None or image_bgr.size == 0:
            logger.warning("[FeatureExtractor] Gambar kosong, return zero vector")
            return np.zeros(self._feature_dim, dtype=np.float32)

        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        features = []

        # 1. CNN Features (1280-dim)
        cnn_feat = self._extract_cnn(image_rgb)
        features.append(cnn_feat)

        # 2. Color Histogram (96-dim)
        if self._use_color:
            color_feat = self._extract_color_histogram(image_bgr)
            features.append(color_feat)

        # 3. Texture Score (1-dim)
        if self._use_texture:
            texture = self._extract_texture_score(image_bgr)
            features.append(np.array([texture], dtype=np.float32))

        return np.concatenate(features).astype(np.float32)

    def extract_batch(self, images_bgr: list[np.ndarray]) -> np.ndarray:
        """
        Ekstrak feature batch gambar sekaligus (lebih efisien).

        Args:
            images_bgr: List gambar BGR

        Returns:
            Feature matrix shape (N, feature_dim)
        """
        features = []
        for i, img in enumerate(images_bgr):
            feat = self.extract(img)
            features.append(feat)
            if (i + 1) % 50 == 0:
                logger.debug(f"[FeatureExtractor] Diproses: {i + 1}/{len(images_bgr)}")

        return np.stack(features, axis=0)

    # ----------------------------------------------------------
    # Private: CNN Extraction
    # ----------------------------------------------------------
    def _extract_cnn(self, image_rgb: np.ndarray) -> np.ndarray:
        """Ekstrak EfficientNet deep features (1280-dim).
        
        NOTE: L2 normalization TIDAK dilakukan di sini karena
        KNNOutfitRecommender.fit() sudah melakukan normalize(norm='l2').
        Double normalization tidak merusak (no-op pada unit vector)
        tapi membuang compute. Satu normalisasi di fit() sudah cukup.
        """
        tensor   = preprocess_image(image_rgb)                   # (1, 224, 224, 3)
        features = self._cnn.predict(tensor, verbose=0)[0]       # (1280,)
        return features.astype(np.float32)


    # ----------------------------------------------------------
    # Private: Color Histogram
    # ----------------------------------------------------------
    def _extract_color_histogram(self, image_bgr: np.ndarray) -> np.ndarray:
        """
        Ekstrak HSV color histogram (96-dim).
        H: 32 bins, S: 32 bins, V: 32 bins → concatenated
        """
        hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
        hists = []
        bins = 32

        for ch in range(3):
            ranges = [0, 180] if ch == 0 else [0, 256]  # H channel max 180
            hist = cv2.calcHist([hsv], [ch], None, [bins], ranges)
            hist = hist.flatten().astype(np.float32)
            # Normalize
            total = hist.sum()
            if total > 0:
                hist /= total
            hists.append(hist)

        return np.concatenate(hists)   # (96,)

    # ----------------------------------------------------------
    # Private: Texture Score
    # ----------------------------------------------------------
    def _extract_texture_score(self, image_bgr: np.ndarray) -> float:
        """
        Hitung texture score menggunakan Laplacian variance.
        Texture tinggi = nilai variance besar = produk bermotif/bertekstur
        """
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        # Normalize ke 0-1 (asumsi max variance ~10000)
        return min(1.0, lap_var / 10000.0)

    # ----------------------------------------------------------
    # Cache Utilities
    # ----------------------------------------------------------
    def save_cache(self, feature_matrix: np.ndarray, product_ids: list[int], path: str | Path) -> None:
        """Simpan feature cache ke disk."""
        cache = {"features": feature_matrix, "product_ids": product_ids}
        with open(path, "wb") as f:
            pickle.dump(cache, f)
        logger.info(f"[FeatureExtractor] Cache disimpan: {path} ({len(product_ids)} produk)")

    def load_cache(self, path: str | Path) -> tuple[np.ndarray, list[int]]:
        """Muat feature cache dari disk."""
        with open(path, "rb") as f:
            cache = pickle.load(f)
        logger.info(f"[FeatureExtractor] Cache dimuat: {path}")
        return cache["features"], cache["product_ids"]

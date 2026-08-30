"""
OutfitAR - KNN Outfit Recommender
Sistem rekomendasi outfit menggunakan K-Nearest Neighbors
dengan Gap Diversity untuk menghindari rekomendasi monoton

Algoritma:
    1. CNN Feature Extraction (EfficientNet)
    2. KNN Similarity Search (cosine similarity)
    3. Gap Diversity Filtering (hapus duplikat terlalu mirip)
    4. Skin Tone Compatibility Filter
    5. Category Balancing (atasan, celana, sepatu, aksesori)
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from loguru import logger
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import normalize


@dataclass
class OutfitCandidate:
    """Kandidat produk untuk rekomendasi."""
    product_id: int
    knn_score: float          # Similarity score 0-1
    category_slot: str        # atasan | celana | sepatu | aksesori


@dataclass
class OutfitSet:
    """Satu set outfit lengkap yang direkomendasikan."""
    candidates: list[OutfitCandidate]
    diversity_score: float
    skin_tone_compatibility: float
    overall_score: float


class KNNOutfitRecommender:
    """
    Mesin rekomendasi outfit berbasis KNN dengan Gap Diversity.

    Gap Diversity: Pastikan setiap rekomendasi memiliki jarak minimum
    tertentu dalam feature space, mencegah rekomendasi yang terlalu mirip.
    """

    # Mapping category_id → slot outfit
    # Angka-angka ini sesuai dengan ID kategori di database
    CATEGORY_SLOTS: dict[int, str] = {
        5: "atasan",    # Kemeja Pria
        6: "atasan",    # Kaos Pria
        7: "celana",    # Celana Pria
        8: "atasan",    # Jaket Pria
        9: "celana",    # Celana Pendek
        10: "sepatu",   # Sepatu Pria
        11: "sepatu",   # Sandal Pria
        12: "aksesori", # Kaus Kaki
        13: "aksesori", # Ikat Pinggang
        14: "aksesori", # Dasi
        15: "aksesori", # Tas
        16: "aksesori", # Jam Tangan
    }

    # Keyword per slot untuk fallback deteksi slot dari nama produk
    _SLOT_KEYWORDS: dict[str, list[str]] = {
        "sepatu":   ["sepatu", "sandal", "sneaker", "boots", "loafer", "slip-on"],
        "celana":   ["celana", "shorts", "chino", "jeans", "legging"],
        "bawahan":  ["rok", "bawahan"],
        "aksesori": ["kaus kaki", "ikat pinggang", "dasi", "tas", "jam tangan",
                     "topi", "belt", "wallet", "cap", "bag", "watch"],
        "atasan":   ["kaos", "kemeja", "sweater", "jaket", "hoodie", "blouse",
                     "dress", "cardigan", "outer", "abaya", "gamis", "tunik",
                     "blazer", "vest", "baju", "atasan", "t-shirt"],
    }

    @classmethod
    def _slot_from_name(cls, product_name: str) -> str:
        """Deteksi slot outfit dari nama produk (fallback ketika category_id=NULL)."""
        name_lower = str(product_name or "").lower()
        # Cek keyword per slot, urutan dict menentukan prioritas
        for slot, keywords in cls._SLOT_KEYWORDS.items():
            if any(kw in name_lower for kw in keywords):
                return slot
        return "aksesori"  # default jika tidak ada keyword yang cocok

    def __init__(self, n_neighbors: int = 20, metric: str = "cosine") -> None:
        """
        Args:
            n_neighbors: Jumlah neighbors untuk KNN search
            metric: Metric jarak ('cosine', 'euclidean', 'manhattan')
        """
        self._n_neighbors = n_neighbors
        self._metric = metric
        self._knn: Optional[NearestNeighbors] = None

        # Data yang sudah di-fit (None sebelum .fit() dipanggil)
        self._feature_matrix: Optional[np.ndarray] = None
        self._product_ids: Optional[list[int]] = None
        self._product_categories: Optional[dict[int, int]] = None
        self._product_skin_compat: Optional[dict[int, list[int]]] = None
        self._product_names: Optional[dict[int, str]] = None
        self._product_genders: Optional[dict[int, str]] = None

        logger.info(f"[KNN] Recommender diinisialisasi: n={n_neighbors}, metric={metric}")

    def fit(
        self,
        feature_matrix: np.ndarray,
        product_ids: list[int],
        product_categories: dict[int, int],
        product_skin_compat: dict[int, list[int]],
        product_names: Optional[dict[int, str]] = None,
        product_genders: Optional[dict[int, str]] = None,
    ) -> "KNNOutfitRecommender":
        """
        Latih KNN model dengan feature matrix produk.

        Args:
            feature_matrix: Shape (N, feature_dim) - feature setiap produk
            product_ids: List ID produk, len=N
            product_categories: {product_id: category_id}
            product_skin_compat: {product_id: [compatible_skin_tone_levels]}

        Returns:
            Self (untuk method chaining)
        """
        # Pastikan jumlah produk konsisten dengan jumlah baris feature
        if len(product_ids) != feature_matrix.shape[0]:
            raise ValueError(f"Jumlah produk ({len(product_ids)}) ≠ baris matrix ({feature_matrix.shape[0]})")

        # L2 normalize feature vectors untuk cosine similarity
        # Setelah normalisasi, dot product == cosine similarity
        self._feature_matrix = normalize(feature_matrix, norm="l2")
        self._product_ids = list(product_ids)
        self._product_categories = product_categories
        self._product_skin_compat = product_skin_compat
        self._product_names = product_names
        self._product_genders = product_genders

        # Fit KNN dengan brute force (lebih cocok untuk cosine metric)
        self._knn = NearestNeighbors(
            n_neighbors=min(self._n_neighbors, len(product_ids)),  # Jangan minta lebih dari jumlah produk
            metric=self._metric,
            algorithm="brute",      # Brute force untuk cosine
            n_jobs=-1,              # Pakai semua CPU core
        )
        self._knn.fit(self._feature_matrix)

        logger.info(f"[KNN] Model dilatih dengan {len(product_ids)} produk")
        return self

    def recommend(
        self,
        query_features: np.ndarray,
        skin_tone_level: int,
        top_k: int = 10,
        diversity_threshold: float = 0.3,
        target_slots: Optional[list[str]] = None,
        gender: Optional[str] = None,
    ) -> list[OutfitCandidate]:
        """
        Generate rekomendasi outfit untuk query feature + skin tone.

        Args:
            query_features: Feature vector skin tone user (1280-dim)
            skin_tone_level: Level skin tone 1-5
            top_k: Jumlah rekomendasi yang diminta
            diversity_threshold: Minimum distance antar rekomendasi (0-1)
            target_slots: Slot outfit yang diinginkan, e.g. ['atasan', 'celana']

        Returns:
            List OutfitCandidate yang sudah difilter dan diurutkan
        """
        self._check_fitted()

        # Default tampilkan semua slot kalau tidak ditentukan
        if target_slots is None:
            target_slots = ["atasan", "celana", "sepatu", "aksesori"]

        # Step 1: KNN search — cari produk paling mirip dengan query
        query_norm = normalize(query_features.reshape(1, -1), norm="l2")
        distances, indices = self._knn.kneighbors(query_norm)

        distances = distances[0]    # (n_neighbors,)
        indices = indices[0]        # (n_neighbors,)

        # Konversi cosine distance → similarity score (distance 0 = similarity 1)
        similarities = 1.0 - distances

        # Step 2: Build candidates dengan filter skin tone
        raw_candidates = []
        for idx, sim in zip(indices, similarities):
            pid = self._product_ids[idx]
            
            # Filter gender compatibility — skip produk yang bukan untuk gender ini
            if gender and hasattr(self, "_product_genders") and self._product_genders:
                prod_gender = self._product_genders.get(pid)
                if prod_gender and prod_gender not in [gender, 'unisex']:
                    continue

            cat_id = self._product_categories.get(pid)
            slot = None
            if cat_id is not None:
                slot = self.CATEGORY_SLOTS.get(cat_id)
            
            # Resolve category slot via keyword matching from product name
            # Dipakai kalau slot dari category_id masih belum ketemu atau jatuh ke aksesori
            if slot is None or slot == "aksesori":
                name = ""
                if hasattr(self, "_product_names") and self._product_names and pid in self._product_names:
                    name = self._product_names[pid].lower()
                
                if name:
                    if any(k in name for k in ["kaos", "hoodie", "kemeja", "jaket", "sweater", "blouse", "tunik", "gamis", "tshirt", "t-shirt", "outer", "atasan"]):
                        slot = "atasan"

            # Tentukan slot: dari category_id jika tersedia, fallback ke keyword nama
            if cat_id is not None and cat_id in self.CATEGORY_SLOTS:
                slot = self.CATEGORY_SLOTS[cat_id]
            else:
                # Fallback: deteksi slot dari nama produk
                product_name = self._product_names.get(pid, "") if hasattr(self, "_product_names") and self._product_names else ""
                slot = self._slot_from_name(product_name)

            # Filter skin tone compatibility (range 1-3 sesuai CNN 3-class)
            compat = self._product_skin_compat.get(pid, list(range(1, 4)))
            if skin_tone_level not in compat:
                # Skip produk yang tidak cocok dengan skin tone user
                continue

            raw_candidates.append(OutfitCandidate(
                product_id=pid,
                knn_score=float(sim),
                category_slot=slot,
            ))

        # Step 3: Gap Diversity filtering — buang kandidat yang terlalu mirip satu sama lain
        diverse = self._apply_diversity_gap(
            candidates=raw_candidates,
            feature_matrix=self._feature_matrix,
            product_ids=self._product_ids,
            threshold=diversity_threshold,
        )

        # Step 4: Balance per slot outfit — pastikan ada perwakilan tiap slot
        balanced = self._balance_by_slot(diverse, target_slots, top_k)

        logger.debug(f"[KNN] {len(balanced)} rekomendasi untuk skin tone={skin_tone_level}")
        return balanced

    def recommend_complete_outfit(
        self,
        query_features: np.ndarray,
        skin_tone_level: int,
        diversity_threshold: float = 0.3,
    ) -> OutfitSet:
        """
        Generate 1 set outfit lengkap (atasan + celana + sepatu + opsional aksesori).

        Returns:
            OutfitSet dengan diversity dan compatibility score
        """
        target = ["atasan", "celana", "sepatu", "aksesori"]
        # Minta tepat 4 item, 1 per slot
        candidates = self.recommend(
            query_features=query_features,
            skin_tone_level=skin_tone_level,
            top_k=4,
            diversity_threshold=diversity_threshold,
            target_slots=target,
        )

        diversity = self._compute_set_diversity(candidates)
        skin_compat = self._compute_skin_compatibility(candidates, skin_tone_level)
        # Overall score: skin compatibility lebih penting (bobot 60%) dari diversity (40%)
        overall = (diversity * 0.4 + skin_compat * 0.6)

        return OutfitSet(
            candidates=candidates,
            diversity_score=diversity,
            skin_tone_compatibility=skin_compat,
            overall_score=overall,
        )

    # ----------------------------------------------------------
    # Private: Diversity Gap Algorithm
    # ----------------------------------------------------------
    def _apply_diversity_gap(
        self,
        candidates: list[OutfitCandidate],
        feature_matrix: np.ndarray,
        product_ids: list[int],
        threshold: float,
    ) -> list[OutfitCandidate]:
        """
        Gap Diversity: Hapus kandidat yang terlalu mirip satu sama lain.
        Algoritma Greedy Maximum Marginal Relevance (MMR).

        Args:
            candidates: Kandidat awal dari KNN
            feature_matrix: Feature matrix semua produk
            product_ids: List product ID (index aligned dengan feature_matrix)
            threshold: Minimum cosine distance antara 2 kandidat (0=tidak ada filter)

        Returns:
            Kandidat setelah diversity filtering
        """
        # Kalau tidak ada kandidat atau threshold=0, langsung return
        if not candidates or threshold <= 0:
            return candidates

        # Buat index product_id → row di feature_matrix untuk lookup cepat
        pid_to_idx = {pid: i for i, pid in enumerate(product_ids)}

        selected: list[OutfitCandidate] = []
        selected_features: list[np.ndarray] = []

        # Proses kandidat dari skor tertinggi ke terendah (greedy)
        for cand in sorted(candidates, key=lambda c: c.knn_score, reverse=True):
            pid_idx = pid_to_idx.get(cand.product_id)
            if pid_idx is None:
                continue

            feat = feature_matrix[pid_idx]

            # Kandidat pertama selalu masuk tanpa pengecekan
            if not selected_features:
                selected.append(cand)
                selected_features.append(feat)
                continue

            # Hitung cosine distance ke semua yang sudah dipilih
            selected_mat = np.stack(selected_features)
            dots = selected_mat @ feat                        # Cosine similarity (sudah L2 normalized)
            max_similarity = float(np.max(dots))
            min_distance = 1.0 - max_similarity              # Cosine distance

            # Tambahkan hanya jika jaraknya cukup (diversity gap terpenuhi)
            if min_distance >= threshold:
                selected.append(cand)
                selected_features.append(feat)

        logger.debug(f"[KNN][Diversity] {len(candidates)} -> {len(selected)} setelah gap={threshold}")
        return selected

    # ----------------------------------------------------------
    # Private: Slot Balancing
    # ----------------------------------------------------------
    def _balance_by_slot(
        self,
        candidates: list[OutfitCandidate],
        target_slots: list[str],
        top_k: int,
    ) -> list[OutfitCandidate]:
        """
        Pilih 1 kandidat terbaik per slot outfit, lalu isi sisa dengan top scorer.
        """
        # Group by slot — pisahkan kandidat per slot
        by_slot: dict[str, list[OutfitCandidate]] = {s: [] for s in target_slots}
        unslotted: list[OutfitCandidate] = []

        for cand in candidates:
            if cand.category_slot in by_slot:
                by_slot[cand.category_slot].append(cand)
            else:
                unslotted.append(cand)

        result: list[OutfitCandidate] = []

        # Ambil 1 terbaik per slot (berdasarkan knn_score)
        for slot in target_slots:
            slot_cands = sorted(by_slot[slot], key=lambda c: c.knn_score, reverse=True)
            if slot_cands:
                result.append(slot_cands[0])

        # Isi sisa top_k dari skor tertinggi (gunakan product_id untuk dedup)
        selected_pids = {c.product_id for c in result}
        remaining     = [c for c in candidates if c.product_id not in selected_pids]
        remaining.sort(key=lambda c: c.knn_score, reverse=True)
        result.extend(remaining[:max(0, top_k - len(result))])

        return result[:top_k]

    # ----------------------------------------------------------
    # Private: Scoring
    # ----------------------------------------------------------
    def _compute_set_diversity(self, candidates: list[OutfitCandidate]) -> float:
        """Hitung rata-rata pairwise cosine distance dalam set (diversity score)."""
        # Kurang dari 2 produk tidak bisa dihitung pairwise distance
        if len(candidates) < 2:
            return 1.0

        pids = [c.product_id for c in candidates]
        pid_to_idx = {pid: i for i, pid in enumerate(self._product_ids)}
        feats = np.stack([
            self._feature_matrix[pid_to_idx[p]]
            for p in pids if p in pid_to_idx
        ])

        if len(feats) < 2:
            return 1.0

        # Pairwise cosine similarity matrix (karena sudah L2 normalized, tinggal dot product)
        sim_matrix = feats @ feats.T
        np.fill_diagonal(sim_matrix, 0)  # Hapus self-similarity (diagonal = 1)
        avg_sim = float(np.sum(sim_matrix) / (len(feats) * (len(feats) - 1)))
        return 1.0 - avg_sim    # diversity = 1 - similarity

    def _compute_skin_compatibility(
        self,
        candidates: list[OutfitCandidate],
        skin_tone: int,
    ) -> float:
        """Hitung rata-rata skin tone compatibility score."""
        if not candidates or not self._product_skin_compat:
            return 1.0

        scores = []
        for cand in candidates:
            # Kalau produk tidak ada di dict, anggap cocok semua skin tone
            compat = self._product_skin_compat.get(cand.product_id, list(range(1, 6)))
            scores.append(1.0 if skin_tone in compat else 0.0)

        # Rata-rata: 1.0 = semua cocok, 0.0 = tidak ada yang cocok
        return float(np.mean(scores))

    # ----------------------------------------------------------
    # Persistence
    # ----------------------------------------------------------
    def save(self, path: str | Path) -> None:
        """Simpan model KNN ke disk (hanya jika sudah di-fit)."""
        self._check_fitted()  # Cegah menyimpan model yang belum dilatih
        # Kumpulkan semua state yang perlu disimpan
        state = {
            "knn":                   self._knn,
            "feature_matrix":        self._feature_matrix,
            "product_ids":           self._product_ids,
            "product_categories":    self._product_categories,
            "product_skin_compat":   self._product_skin_compat,
            "product_names":         getattr(self, "_product_names", None),
            "product_genders":       getattr(self, "_product_genders", None),
            "n_neighbors":           self._n_neighbors,
            "metric":                self._metric,
        }
        # Pickle dengan protokol tertinggi biar file sekecil mungkin
        with open(path, "wb") as f:
            pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info(f"[KNN] Model disimpan: {path}")

    def load(self, path: str | Path) -> "KNNOutfitRecommender":
        """Muat model KNN dari disk."""
        with open(path, "rb") as f:
            state = pickle.load(f)

        # Restore semua state dari file
        self._knn = state["knn"]
        self._feature_matrix = state["feature_matrix"]
        self._product_ids = state["product_ids"]
        self._product_categories = state["product_categories"]
        self._product_skin_compat = state["product_skin_compat"]
        # Pakai .get() untuk backward compatibility kalau key tidak ada di file lama
        self._product_names = state.get("product_names", None)
        self._product_genders = state.get("product_genders", None)
        self._n_neighbors = state["n_neighbors"]
        self._metric = state["metric"]

        logger.info(f"[KNN] Model dimuat dari {path}: {len(self._product_ids)} produk")
        return self

    def _check_fitted(self) -> None:
        # Guard: pastikan .fit() sudah dipanggil sebelum operasi lain
        if self._knn is None:
            raise RuntimeError("Model belum dilatih. Panggil .fit() terlebih dahulu.")

"""
OutfitAR - Script Training Model ML
Jalankan setelah import CSV:
    python scripts/train_models.py

Script ini akan:
  1. Ambil semua produk dari database
  2. Download/load gambar produk
  3. Ekstrak CNN features (EfficientNet-B0)
  4. Simpan feature cache
  5. Training KNN Recommender
  6. Simpan model KNN ke disk
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import json
import pickle

import numpy as np
from loguru import logger

from app.config.settings import get_settings

settings = get_settings()


async def fetch_all_products():
    """Ambil semua produk aktif dari database."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import select
    from app.models.models import Product

    engine = create_async_engine(settings.async_database_url)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        result = await session.execute(
            select(Product).where(Product.is_active == True)
        )
        products = result.scalars().all()
        # Serialize sebelum close session
        data = [
            {
                "id": p.id,
                "name": p.name,
                "category_id": p.category_id,
                "color": p.color,
                "skin_tone_compat": p.skin_tone_compat or [1,2,3,4,5],
                "image_url": p.image_url,
            }
            for p in products
        ]

    await engine.dispose()
    return data


def generate_dummy_features(num_products: int, feature_dim: int = 1280) -> np.ndarray:
    """
    Generate dummy feature vectors untuk development.
    Di production, ganti dengan ekstraksi CNN EfficientNet nyata.
    """
    rng = np.random.default_rng(seed=42)
    features = rng.random((num_products, feature_dim)).astype(np.float32)
    # L2 normalize
    norms = np.linalg.norm(features, axis=1, keepdims=True)
    return features / np.maximum(norms, 1e-8)


async def main():
    logger.info("=" * 60)
    logger.info("  OutfitAR - Training Pipeline")
    logger.info("=" * 60)

    # Step 1: Ambil produk dari database
    logger.info("[TRAIN] Mengambil produk dari database...")
    products = await fetch_all_products()

    if not products:
        logger.error("[TRAIN] Tidak ada produk di database!")
        logger.error("Jalankan dulu: python scripts/import_csv.py")
        sys.exit(1)

    logger.info(f"[TRAIN] Total produk: {len(products)}")

    product_ids = [p["id"] for p in products]
    product_categories = {p["id"]: p["category_id"] or 6 for p in products}
    product_skin_compat = {
        p["id"]: p["skin_tone_compat"] if isinstance(p["skin_tone_compat"], list)
                 else json.loads(p["skin_tone_compat"]) if p["skin_tone_compat"]
                 else [1,2,3,4,5]
        for p in products
    }

    # Step 2: Feature extraction
    logger.info("[TRAIN] Mengekstrak fitur CNN (EfficientNet)...")
    logger.info("[TRAIN] Mode: DUMMY (untuk development)")
    logger.info("[TRAIN] Di production: ganti dengan load gambar nyata dari image_url")

    feature_matrix = generate_dummy_features(len(products), feature_dim=1280)
    logger.info(f"[TRAIN] Feature matrix: {feature_matrix.shape}")

    # Step 3: Simpan feature cache
    model_dir = Path(settings.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    cache_path = Path(settings.feature_cache_path)
    cache = {"features": feature_matrix, "product_ids": product_ids}
    with open(cache_path, "wb") as f:
        pickle.dump(cache, f)
    logger.info(f"[TRAIN] Feature cache disimpan: {cache_path}")

    # Step 4: Training KNN
    logger.info("[TRAIN] Training KNN Recommender...")
    from ml.knn.outfit_recommender import KNNOutfitRecommender

    recommender = KNNOutfitRecommender(n_neighbors=20, metric="cosine")
    recommender.fit(
        feature_matrix=feature_matrix,
        product_ids=product_ids,
        product_categories=product_categories,
        product_skin_compat=product_skin_compat,
    )

    # Step 5: Simpan KNN model
    knn_path = Path(settings.knn_model_path)
    recommender.save(knn_path)
    logger.info(f"[TRAIN] KNN model disimpan: {knn_path}")

    # Test rekomendasi
    logger.info("[TRAIN] Test rekomendasi untuk skin tone level 3...")
    test_query = np.random.default_rng(0).random(1280).astype(np.float32)
    results = recommender.recommend(test_query, skin_tone_level=3, top_k=4)
    for r in results:
        logger.info(f"  → Product ID={r.product_id} | Slot={r.category_slot} | Score={r.knn_score:.4f}")

    logger.info("=" * 60)
    logger.info("[TRAIN] SELESAI! Model siap digunakan.")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

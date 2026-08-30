"""
OutfitAR - Batch Feature Population Script
Membaca gambar produk dari storage LOKAL dan mengekstrak feature_vector
menggunakan EfficientNet-B0, lalu menyimpan ke database.

Jalankan dari folder backend/:
    .\\venv_fix\\Scripts\\python.exe scripts\\populate_features.py
"""
import os
import sys
import json
import time

import cv2
import numpy as np
import pymysql
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

# Add parent dir (backend/) ke sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import get_settings
from ml.cnn.feature_extractor import OutfitFeatureExtractor

# Root folder tempat gambar produk disimpan
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")


def load_image_local(product: dict) -> tuple:
    """
    Baca gambar dari file lokal.
    image_url di DB berupa: 'products/Pria/Image_1.jpg'
    Path lengkap: backend/uploads/products/Pria/Image_1.jpg
    """
    pid = product['id']
    img_url = product['image_url']

    if not img_url:
        return pid, None, "Missing image URL"

    # Normalize path separator
    clean_path = str(img_url).replace('\\', '/')
    full_path  = os.path.join(UPLOADS_DIR, clean_path)

    if not os.path.exists(full_path):
        return pid, None, f"File tidak ditemukan: {full_path}"

    try:
        img_bgr = cv2.imread(full_path)
        if img_bgr is None:
            return pid, None, f"OpenCV gagal baca: {full_path}"
        return pid, img_bgr, None
    except Exception as e:
        return pid, None, f"Error baca file: {e}"


def main():
    logger.info("=" * 55)
    logger.info("  OutfitAR - Batch Feature Vector Population")
    logger.info("=" * 55)
    logger.info(f"Uploads dir : {UPLOADS_DIR}")

    # Inisialisasi feature extractor (load EfficientNet-B0)
    logger.info("Inisialisasi OutfitFeatureExtractor (EfficientNet-B0)...")
    extractor = OutfitFeatureExtractor()
    logger.info("Feature extractor siap!")

    # Konfigurasi database dari settings
    settings = get_settings()
    db_cfg = {
        'host':        settings.db_host,
        'port':        settings.db_port,
        'user':        settings.db_user,
        'password':    settings.db_password,
        'database':    settings.db_name,
        'cursorclass': pymysql.cursors.DictCursor,
    }

    # Ambil semua produk yang belum punya feature_vector
    logger.info("Mengambil produk tanpa feature_vector dari database...")
    conn = pymysql.connect(**db_cfg)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, image_url
                FROM products
                WHERE feature_vector IS NULL
                ORDER BY id ASC
            """)
            products = cur.fetchall()
    finally:
        conn.close()

    total = len(products)
    logger.info(f"Ditemukan {total} produk yang perlu diproses")

    if total == 0:
        logger.info("Tidak ada produk yang perlu diproses. Selesai!")
        return

    succeeded = 0
    failed    = 0
    processed = 0
    start_ts  = time.time()

    CHUNK_SIZE = 50

    for chunk_start in range(0, total, CHUNK_SIZE):
        chunk      = products[chunk_start:chunk_start + CHUNK_SIZE]
        chunk_num  = chunk_start // CHUNK_SIZE + 1
        total_chunks = (total + CHUNK_SIZE - 1) // CHUNK_SIZE
        logger.info(f"\n--- Chunk {chunk_num}/{total_chunks} ({len(chunk)} produk) ---")

        # Load gambar secara paralel (I/O bound — disk read)
        load_results = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(load_image_local, p): p for p in chunk}
            for future in as_completed(futures):
                pid, img_bgr, error = future.result()
                load_results[pid] = (img_bgr, error)

        # Ekstrak feature & kumpulkan untuk batch update
        updates = []
        for p in chunk:
            pid              = p['id']
            img_bgr, error   = load_results.get(pid, (None, "Load error"))
            processed       += 1

            if error:
                logger.warning(f"  Skip ID {pid}: {error}")
                failed += 1
                continue

            try:
                features      = extractor.extract(img_bgr)      # (1377,)
                features_list = [round(float(x), 6) for x in features]

                if len(features_list) != extractor._feature_dim:
                    logger.warning(f"  ID {pid}: dimensi salah ({len(features_list)})")
                    failed += 1
                    continue

                updates.append((json.dumps(features_list), pid))
                succeeded += 1

            except Exception as e:
                logger.warning(f"  ID {pid}: feature extraction error - {e}")
                failed += 1

        # Batch UPDATE ke database
        if updates:
            conn2 = pymysql.connect(**db_cfg)
            try:
                with conn2.cursor() as cur:
                    cur.executemany(
                        "UPDATE products SET feature_vector = %s WHERE id = %s",
                        updates,
                    )
                conn2.commit()
                logger.info(f"  DB updated: {len(updates)} produk tersimpan")
            except Exception as e:
                logger.error(f"  DB update gagal: {e}")
                succeeded -= len(updates)
                failed    += len(updates)
            finally:
                conn2.close()

        elapsed = time.time() - start_ts
        logger.info(f"  Progress: {processed}/{total} | OK:{succeeded} Gagal:{failed} | {elapsed:.0f}s")

    # === FINAL SUMMARY ===
    elapsed_total = time.time() - start_ts
    logger.info("\n" + "=" * 55)
    logger.info("  FINAL SUMMARY")
    logger.info("=" * 55)
    logger.info(f"  Total diproses  : {processed}")
    logger.info(f"  Berhasil (OK)   : {succeeded}")
    logger.info(f"  Gagal / Di-skip : {failed}")
    logger.info(f"  Waktu total     : {elapsed_total:.1f} detik")
    logger.info("=" * 55)

    if succeeded > 0:
        logger.info(f"Feature vector tersimpan ke {succeeded} produk di database.")
        logger.info("Jalankan backend lalu test endpoint rekomendasi untuk verifikasi KNN aktif.")


if __name__ == "__main__":
    main()

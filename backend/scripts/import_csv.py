"""
OutfitAR - Script Import CSV ke Database MySQL
Jalankan: python scripts/import_csv.py --file ../data/raw/provenance.csv

Script ini akan:
1. Parse CSV dari Zalora (product_id, source_page)
2. Ekstrak informasi: brand, nama, warna, kategori dari product_id slug
3. Insert ke tabel products di MySQL (Laragon)
"""
import argparse
import re
import sys
from pathlib import Path

# Tambahkan root backend ke path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import pymysql
from loguru import logger
from app.config.settings import get_settings

settings = get_settings()

# ============================================================
# Mapping warna dari slug
# ============================================================
KNOWN_COLORS = [
    "black", "white", "navy", "grey", "gray", "blue", "red", "green",
    "brown", "beige", "khaki", "army", "maroon", "yellow", "orange",
    "purple", "pink", "silver", "gold", "multi", "cream", "camel",
    "mocca", "sage", "olive",
]

# Mapping nama warna Inggris → Indonesia
COLOR_ID = {
    "black": "Hitam", "white": "Putih", "navy": "Navy",
    "grey": "Abu-abu", "gray": "Abu-abu", "blue": "Biru",
    "red": "Merah", "green": "Hijau", "brown": "Coklat",
    "beige": "Krem", "khaki": "Khaki", "army": "Army",
    "maroon": "Merah Tua", "yellow": "Kuning", "orange": "Oranye",
    "purple": "Ungu", "pink": "Pink", "silver": "Silver",
    "gold": "Emas", "multi": "Multi", "cream": "Krem",
    "camel": "Camel", "mocca": "Mocca", "sage": "Sage",
    "olive": "Olive",
}

# Mapping keyword slug → category_id (sesuai schema.sql)
CATEGORY_RULES: list[tuple[re.Pattern, int]] = [
    (re.compile(r"kemeja|shirt|flannel"), 5),
    (re.compile(r"kaos|t-shirt|tshirt|t_shirt|singlet|tanktop"), 6),
    (re.compile(r"celana-panjang|jeans|chinos|pants|trousers|cargo-long|trackpants"), 7),
    (re.compile(r"jaket|jacket|hoodie|tracksuit"), 8),
    (re.compile(r"celana-pendek|shorts|boardshort"), 9),
    (re.compile(r"sepatu|sneakers|loafer|oxford|boots|lace-up"), 10),
    (re.compile(r"sandal|slip-on"), 11),
    (re.compile(r"kaus-kaki|sock"), 12),
    (re.compile(r"ikat-pinggang|ban-pinggang|belt"), 13),
    (re.compile(r"dasi|tie"), 14),
    (re.compile(r"tas|bag|waist-bag"), 15),
    (re.compile(r"smartwatch|smartband|jam-tangan|watch"), 16),
    (re.compile(r"polo"), 5),
]

# Skin tone compatibility default per kategori warna
SKIN_TONE_BY_COLOR: dict[str, list[int]] = {
    "black":  [1, 2, 3, 4, 5],
    "white":  [3, 4, 5],
    "navy":   [1, 2, 3, 4],
    "grey":   [1, 2, 3, 4, 5],
    "brown":  [1, 2, 3],
    "beige":  [1, 2, 3],
    "khaki":  [1, 2, 3],
    "army":   [1, 2, 3],
    "blue":   [1, 2, 3, 4],
    "red":    [2, 3, 4],
    "green":  [2, 3, 4],
    "multi":  [1, 2, 3, 4, 5],
    "maroon": [1, 2, 3],
    "camel":  [1, 2],
    "cream":  [3, 4, 5],
    "silver": [1, 2, 3, 4, 5],
}


# ============================================================
# Parser slug → metadata
# ============================================================

def parse_slug(slug: str) -> dict:
    """
    Parse product slug Zalora menjadi metadata terstruktur.

    Contoh slug:
        'platini-kemeja-motif-pria-lengan-pendek-katun-hijau-73425-green-4215486'

    Returns dict: {brand, name, color, category_id, gender, product_external_id}
    """
    parts = slug.split("-")

    # Brand = kata pertama (bisa 1-2 kata)
    brand = _extract_brand(parts)

    # Product ID numerik = bagian terakhir
    external_id = parts[-1] if parts[-1].isdigit() else slug

    # Warna = kata sebelum numeric ID, atau dari daftar warna
    color_en = _extract_color(parts)
    color_id = COLOR_ID.get(color_en, color_en.capitalize()) if color_en else None

    # Kategori berdasarkan keyword
    category_id = _extract_category(slug)

    # Gender
    gender = "wanita" if re.search(r"wanita|women|woman", slug) else "pria"

    # Nama produk: ambil dari slug, bersihkan dari ID dan brand
    name = _build_name(slug, brand)

    return {
        "product_external_id": external_id,
        "name": name,
        "brand": brand.title() if brand else None,
        "color": color_id,
        "category_id": category_id,
        "gender": gender,
        "skin_tone_compat": SKIN_TONE_BY_COLOR.get(color_en, [1, 2, 3, 4, 5]) if color_en else [1, 2, 3, 4, 5],
        "style_tags": _infer_style_tags(slug),
    }


def _extract_brand(parts: list[str]) -> str:
    """Ambil nama brand dari bagian awal slug."""
    # Brand biasanya 1-2 kata pertama sebelum kata deskriptif
    stop_words = {"men", "man", "women", "pria", "wanita", "celana", "kaos", "baju", "kemeja", "t"}
    brand_parts = []
    for p in parts[:3]:
        if p.lower() in stop_words or p.isdigit():
            break
        brand_parts.append(p)
        if len(brand_parts) >= 2:
            break
    return "-".join(brand_parts) if brand_parts else parts[0]


def _extract_color(parts: list[str]) -> str | None:
    """Cari warna dalam parts slug."""
    for part in reversed(parts):
        if part.lower() in KNOWN_COLORS:
            return part.lower()
    return None


def _extract_category(slug: str) -> int:
    """Tentukan category_id berdasarkan keyword dalam slug."""
    slug_lower = slug.lower()
    for pattern, cat_id in CATEGORY_RULES:
        if pattern.search(slug_lower):
            return cat_id
    return 6  # Default: kaos pria


def _build_name(slug: str, brand: str) -> str:
    """Bangun nama produk dari slug."""
    # Hapus numeric ID di akhir
    name = re.sub(r"-\d{4,}-\d+$", "", slug)
    name = re.sub(r"-\d+$", "", name)
    # Ganti - dengan spasi
    name = name.replace("-", " ").strip()
    # Title case
    return name.title()[:500]


def _infer_style_tags(slug: str) -> list[str]:
    """Inferensi tag gaya dari slug."""
    tags = []
    if re.search(r"formal|office|kemeja|shirt", slug):
        tags.append("formal")
    if re.search(r"casual|kaos|t-shirt|jeans", slug):
        tags.append("casual")
    if re.search(r"sport|olahraga|dry-fit|gym|running|fitness", slug):
        tags.append("sporty")
    if re.search(r"slim|fit", slug):
        tags.append("slim-fit")
    if re.search(r"motif|hawaii|batik|pattern", slug):
        tags.append("motif")
    return tags if tags else ["casual"]


# ============================================================
# Database Insertion
# ============================================================

def get_connection() -> pymysql.Connection:
    """Buat koneksi ke MySQL Laragon."""
    return pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset="utf8mb4",
        autocommit=False,
    )


def insert_products(rows: list[dict], conn: pymysql.Connection, batch_size: int = 100) -> int:
    """
    Insert batch produk ke database.

    Returns:
        Jumlah produk yang berhasil di-insert
    """
    sql = """
        INSERT IGNORE INTO products
            (product_external_id, name, brand, category_id, color, gender,
             source_page, source_platform, style_tags, skin_tone_compat, is_active)
        VALUES
            (%(product_external_id)s, %(name)s, %(brand)s, %(category_id)s,
             %(color)s, %(gender)s, %(source_page)s, %(source_platform)s,
             %(style_tags)s, %(skin_tone_compat)s, 1)
    """
    inserted = 0
    cursor = conn.cursor()

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        try:
            cursor.executemany(sql, batch)
            conn.commit()
            inserted += cursor.rowcount
            logger.info(f"  Batch {i // batch_size + 1}: {cursor.rowcount} rows inserted")
        except Exception as exc:
            conn.rollback()
            logger.error(f"  Batch {i // batch_size + 1} ERROR: {exc}")

    cursor.close()
    return inserted


# ============================================================
# Main
# ============================================================

def main(csv_path: str) -> None:
    import json

    path = Path(csv_path)
    if not path.exists():
        logger.error(f"File tidak ditemukan: {path}")
        sys.exit(1)

    logger.info(f"Membaca CSV: {path}")
    df = pd.read_csv(path, dtype=str).fillna("")

    logger.info(f"Total baris: {len(df)}")

    rows = []
    for _, row in df.iterrows():
        slug    = str(row.get("product_id", "")).strip()
        src_pag = str(row.get("source_page", "")).strip()

        if not slug:
            continue

        meta = parse_slug(slug)
        meta["source_page"]     = src_pag
        meta["source_platform"] = "zalora"
        meta["style_tags"]      = json.dumps(meta["style_tags"])
        meta["skin_tone_compat"] = json.dumps(meta["skin_tone_compat"])
        rows.append(meta)

    logger.info(f"Parsed {len(rows)} produk")

    # Koneksi database
    try:
        conn = get_connection()
        logger.success("[OK] Koneksi MySQL berhasil")
    except Exception as exc:
        logger.error(f"[FAIL] Gagal konek MySQL: {exc}")
        logger.info("Pastikan Laragon berjalan dan database 'outfit_ar' sudah dibuat!")
        sys.exit(1)

    # Insert
    total = insert_products(rows, conn)
    conn.close()

    logger.success(f"[DONE] Selesai! {total} produk berhasil dimasukkan ke database")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import CSV produk ke MySQL OutfitAR")
    parser.add_argument("--file", required=True, help="Path ke file CSV")
    args = parser.parse_args()
    main(args.file)

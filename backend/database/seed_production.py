"""
OutfitAR - Production Database Seeder
Pakai foto produk asli dari folder uploads/products/Pria dan Wanita.
"""
import json

SEED_PRODUCTS = [
    # === PRIA (foto asli dari uploads/products/Pria) ===
    {"external_id": "ZLR-PRI-001", "name": "Kemeja Flannel Kotak-Kotak Slim Fit", "brand": "H&M", "color": "#8B4513", "price": 249000, "image_url": "products/Pria/Image_1.jpg", "product_url": "https://www.zalora.co.id/kemeja-flannel", "gender": "pria", "material": "Cotton", "style_tags": ["casual", "streetwear"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-PRI-002", "name": "Kaos Polos Oversize Premium", "brand": "Uniqlo", "color": "#FFFFFF", "price": 199000, "image_url": "products/Pria/Image_2.jpg", "product_url": "https://www.zalora.co.id/kaos-polos-oversize", "gender": "pria", "material": "Cotton 100%", "style_tags": ["casual", "minimalist"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-PRI-003", "name": "Celana Chino Slim Fit Navy", "brand": "Zara", "color": "#000080", "price": 399000, "image_url": "products/Pria/Image_3.jpg", "product_url": "https://www.zalora.co.id/celana-chino-navy", "gender": "pria", "material": "Cotton Chino", "style_tags": ["smart casual", "office"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-PRI-004", "name": "Polo Shirt Pique Classic Fit", "brand": "Lacoste", "color": "#006400", "price": 599000, "image_url": "products/Pria/Image_10.jpg", "product_url": "https://www.zalora.co.id/polo-shirt-lacoste", "gender": "pria", "material": "Cotton Pique", "style_tags": ["smart casual", "sporty"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-PRI-005", "name": "Kemeja Oxford Button-Down Putih", "brand": "Gap", "color": "#FFFFFF", "price": 349000, "image_url": "products/Pria/Image_11.jpg", "product_url": "https://www.zalora.co.id/kemeja-oxford-putih", "gender": "pria", "material": "Oxford Cotton", "style_tags": ["formal", "smart casual"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-PRI-006", "name": "Jaket Denim Vintage Wash", "brand": "Levi's", "color": "#4169E1", "price": 699000, "image_url": "products/Pria/Image_13.jpg", "product_url": "https://www.zalora.co.id/jaket-denim-levis", "gender": "pria", "material": "Denim", "style_tags": ["casual", "vintage"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-PRI-007", "name": "Celana Jogger Sweatpants Dark Grey", "brand": "Adidas", "color": "#696969", "price": 449000, "image_url": "products/Pria/Image_14.jpg", "product_url": "https://www.zalora.co.id/celana-jogger-adidas", "gender": "pria", "material": "Fleece", "style_tags": ["sporty", "casual"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-PRI-008", "name": "Kaos Striped Breton Navy-White", "brand": "Uniqlo", "color": "#000080", "price": 229000, "image_url": "products/Pria/Image_15.jpg", "product_url": "https://www.zalora.co.id/kaos-striped-breton", "gender": "pria", "material": "Cotton", "style_tags": ["casual", "nautical"], "skin_tone_compat": [2, 3]},
    {"external_id": "ZLR-PRI-009", "name": "Hoodie Pullover Fleece Hitam", "brand": "Nike", "color": "#000000", "price": 549000, "image_url": "products/Pria/Image_16.jpg", "product_url": "https://www.zalora.co.id/hoodie-nike-hitam", "gender": "pria", "material": "Fleece", "style_tags": ["sporty", "casual"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-PRI-010", "name": "Kemeja Batik Slim Fit Modern", "brand": "Batik Keris", "color": "#8B0000", "price": 325000, "image_url": "products/Pria/Image_17.jpg", "product_url": "https://www.zalora.co.id/kemeja-batik-keris", "gender": "pria", "material": "Viscose", "style_tags": ["formal", "traditional"], "skin_tone_compat": [1, 2]},
    {"external_id": "ZLR-PRI-011", "name": "T-Shirt Graphic Print Streetwear", "brand": "Street Society", "color": "#1C1C1C", "price": 189000, "image_url": "products/Pria/Image_18.jpg", "product_url": "https://www.zalora.co.id/tshirt-graphic", "gender": "pria", "material": "Cotton", "style_tags": ["streetwear", "casual"], "skin_tone_compat": [2, 3]},
    {"external_id": "ZLR-PRI-012", "name": "Celana Cargo Wide Leg Beige", "brand": "Pull&Bear", "color": "#D2B48C", "price": 379000, "image_url": "products/Pria/Image_19.jpg", "product_url": "https://www.zalora.co.id/celana-cargo-beige", "gender": "pria", "material": "Cotton Blend", "style_tags": ["streetwear", "casual"], "skin_tone_compat": [2, 3]},
    {"external_id": "ZLR-PRI-013", "name": "Kemeja Linen Casual Sky Blue", "brand": "Mango Man", "color": "#87CEEB", "price": 289000, "image_url": "products/Pria/Image_20.jpg", "product_url": "https://www.zalora.co.id/kemeja-linen-skyblue", "gender": "pria", "material": "Linen", "style_tags": ["casual", "resort"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-PRI-014", "name": "Bomber Jacket Varsity Green", "brand": "H&M", "color": "#228B22", "price": 489000, "image_url": "products/Pria/Image_21.jpg", "product_url": "https://www.zalora.co.id/bomber-jacket-green", "gender": "pria", "material": "Polyester", "style_tags": ["casual", "sporty"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-PRI-015", "name": "Celana Jeans Slim Tapered Black", "brand": "Levi's", "color": "#000000", "price": 599000, "image_url": "products/Pria/Image_23.jpg", "product_url": "https://www.zalora.co.id/jeans-slim-black", "gender": "pria", "material": "Denim", "style_tags": ["casual", "smart casual"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-PRI-016", "name": "Kemeja Motif Hawaiian Lengan Pendek", "brand": "Topman", "color": "#FF6347", "price": 259000, "image_url": "products/Pria/Image_24.jpg", "product_url": "https://www.zalora.co.id/kemeja-hawaiian", "gender": "pria", "material": "Rayon", "style_tags": ["casual", "resort"], "skin_tone_compat": [1, 2]},
    {"external_id": "ZLR-PRI-017", "name": "Turtleneck Sweater Cream Rajut", "brand": "Zara", "color": "#FFFDD0", "price": 499000, "image_url": "products/Pria/Image_26.jpg", "product_url": "https://www.zalora.co.id/turtleneck-cream", "gender": "pria", "material": "Knit Wool Blend", "style_tags": ["smart casual", "minimalist"], "skin_tone_compat": [2, 3]},
    {"external_id": "ZLR-PRI-018", "name": "Celana Training Jogger Navy Stripe", "brand": "Nike", "color": "#000080", "price": 399000, "image_url": "products/Pria/Image_27.jpg", "product_url": "https://www.zalora.co.id/celana-training-nike", "gender": "pria", "material": "Polyester", "style_tags": ["sporty", "gym"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-PRI-019", "name": "Longsleeve Plain Maroon Slim Fit", "brand": "Cotton On", "color": "#800000", "price": 179000, "image_url": "products/Pria/Image_30.jpg", "product_url": "https://www.zalora.co.id/longsleeve-maroon", "gender": "pria", "material": "Cotton", "style_tags": ["casual", "minimalist"], "skin_tone_compat": [1, 2]},
    {"external_id": "ZLR-PRI-020", "name": "Kemeja Formal Dress Shirt Biru Muda", "brand": "Arrow", "color": "#87CEEB", "price": 329000, "image_url": "products/Pria/Image_100.jpg", "product_url": "https://www.zalora.co.id/dress-shirt-biru", "gender": "pria", "material": "Cotton Blend", "style_tags": ["formal", "office"], "skin_tone_compat": [1, 2, 3]},
    # === WANITA (foto asli dari uploads/products/Wanita) ===
    {"external_id": "ZLR-WAN-001", "name": "Blouse Ruffled Off-Shoulder Floral", "brand": "Mango", "color": "#FFB6C1", "price": 299000, "image_url": "products/Wanita/Image_48.jpg", "product_url": "https://www.zalora.co.id/blouse-ruffle-floral", "gender": "wanita", "material": "Polyester Satin", "style_tags": ["feminine", "casual"], "skin_tone_compat": [2, 3]},
    {"external_id": "ZLR-WAN-002", "name": "Dress Midi Wrap Polkadot", "brand": "H&M", "color": "#FFFFFF", "price": 349000, "image_url": "products/Wanita/Image_49.jpg", "product_url": "https://www.zalora.co.id/dress-midi-polkadot", "gender": "wanita", "material": "Viscose", "style_tags": ["feminine", "casual"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-WAN-003", "name": "Celana Kulot Wide Leg Khaki", "brand": "Topshop", "color": "#C3B091", "price": 279000, "image_url": "products/Wanita/Image_50.jpg", "product_url": "https://www.zalora.co.id/celana-kulot-khaki", "gender": "wanita", "material": "Cotton", "style_tags": ["casual", "smart casual"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-WAN-004", "name": "Rok Mini Pleated Skirt Yellow", "brand": "Zara", "color": "#FFD700", "price": 249000, "image_url": "products/Wanita/Image_51.jpg", "product_url": "https://www.zalora.co.id/rok-mini-yellow", "gender": "wanita", "material": "Polyester", "style_tags": ["feminine", "preppy"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-WAN-005", "name": "Kaos Crop Top Basic Cotton", "brand": "Pull&Bear", "color": "#D8BFD8", "price": 149000, "image_url": "products/Wanita/Image_52.jpg", "product_url": "https://www.zalora.co.id/crop-top-basic", "gender": "wanita", "material": "Cotton", "style_tags": ["casual", "minimalist"], "skin_tone_compat": [2, 3]},
    {"external_id": "ZLR-WAN-006", "name": "Dress Maxi Boho Floral Teal", "brand": "Free People", "color": "#008080", "price": 549000, "image_url": "products/Wanita/Image_53.jpg", "product_url": "https://www.zalora.co.id/dress-maxi-boho", "gender": "wanita", "material": "Rayon", "style_tags": ["bohemian", "casual"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-WAN-007", "name": "Blouse Kemeja Oversize Putih", "brand": "ASOS", "color": "#FFFFFF", "price": 269000, "image_url": "products/Wanita/Image_54.jpg", "product_url": "https://www.zalora.co.id/blouse-oversize-putih", "gender": "wanita", "material": "Cotton", "style_tags": ["casual", "minimalist"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-WAN-008", "name": "Celana Jeans Skinny High Waist", "brand": "Levi's", "color": "#4169E1", "price": 499000, "image_url": "products/Wanita/Image_55.jpg", "product_url": "https://www.zalora.co.id/jeans-skinny-highwaist", "gender": "wanita", "material": "Denim", "style_tags": ["casual", "classic"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-WAN-009", "name": "Atasan Knit Tank Top Ribbed Nude", "brand": "H&M", "color": "#D2B48C", "price": 199000, "image_url": "products/Wanita/Image_57.jpg", "product_url": "https://www.zalora.co.id/knit-tank-nude", "gender": "wanita", "material": "Knit Cotton Blend", "style_tags": ["minimalist", "casual"], "skin_tone_compat": [2, 3]},
    {"external_id": "ZLR-WAN-010", "name": "Rok Midi Satin Slip Dusty Pink", "brand": "Zara", "color": "#DDA0DD", "price": 379000, "image_url": "products/Wanita/Image_58.jpg", "product_url": "https://www.zalora.co.id/rok-satin-pink", "gender": "wanita", "material": "Satin Polyester", "style_tags": ["feminine", "elegant"], "skin_tone_compat": [2, 3]},
    {"external_id": "ZLR-WAN-011", "name": "Jaket Denim Crop Boyfriend", "brand": "Gap", "color": "#87CEEB", "price": 549000, "image_url": "products/Wanita/Image_59.jpg", "product_url": "https://www.zalora.co.id/jaket-denim-crop", "gender": "wanita", "material": "Denim", "style_tags": ["casual", "streetwear"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-WAN-012", "name": "Dress Bodycon Ribbed Olive Green", "brand": "PrettyLittleThing", "color": "#6B8E23", "price": 299000, "image_url": "products/Wanita/Image_61.jpg", "product_url": "https://www.zalora.co.id/dress-bodycon-olive", "gender": "wanita", "material": "Rayon Blend", "style_tags": ["casual"], "skin_tone_compat": [1, 2]},
    {"external_id": "ZLR-WAN-013", "name": "Cardigan Panjang Open Front Cream", "brand": "Mango", "color": "#FFFDD0", "price": 449000, "image_url": "products/Wanita/Image_62.jpg", "product_url": "https://www.zalora.co.id/cardigan-cream", "gender": "wanita", "material": "Knit", "style_tags": ["casual", "minimalist"], "skin_tone_compat": [2, 3]},
    {"external_id": "ZLR-WAN-014", "name": "Jumpsuit Overall Denim Wide Leg", "brand": "ASOS", "color": "#6495ED", "price": 429000, "image_url": "products/Wanita/Image_63.jpg", "product_url": "https://www.zalora.co.id/jumpsuit-overall-denim", "gender": "wanita", "material": "Denim", "style_tags": ["casual", "trendy"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-WAN-015", "name": "Blouse Chiffon Puffed Sleeve Lilac", "brand": "Topshop", "color": "#9370DB", "price": 259000, "image_url": "products/Wanita/Image_64.jpg", "product_url": "https://www.zalora.co.id/blouse-chiffon-lilac", "gender": "wanita", "material": "Chiffon", "style_tags": ["feminine", "elegant"], "skin_tone_compat": [2, 3]},
    {"external_id": "ZLR-WAN-016", "name": "Rok Pleated Midi Tartan Plaid", "brand": "Zara", "color": "#8B0000", "price": 319000, "image_url": "products/Wanita/Image_65.jpg", "product_url": "https://www.zalora.co.id/rok-tartan-plaid", "gender": "wanita", "material": "Polyester", "style_tags": ["preppy", "smart casual"], "skin_tone_compat": [1, 2]},
    {"external_id": "ZLR-WAN-017", "name": "Atasan Corset Bustier Satin Hitam", "brand": "H&M", "color": "#000000", "price": 249000, "image_url": "products/Wanita/Image_66.jpg", "product_url": "https://www.zalora.co.id/bustier-satin-hitam", "gender": "wanita", "material": "Satin", "style_tags": ["sexy", "party", "elegant"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-WAN-018", "name": "Dress Shirt Maxi Floral Summer", "brand": "Mango", "color": "#98FB98", "price": 489000, "image_url": "products/Wanita/Image_67.jpg", "product_url": "https://www.zalora.co.id/dress-shirt-floral", "gender": "wanita", "material": "Rayon", "style_tags": ["casual", "summer"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-WAN-019", "name": "Celana Cargo Street Style Hitam", "brand": "Street Society", "color": "#1C1C1C", "price": 359000, "image_url": "products/Wanita/Image_68.jpg", "product_url": "https://www.zalora.co.id/celana-cargo-hitam", "gender": "wanita", "material": "Cotton Twill", "style_tags": ["streetwear", "casual"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-WAN-020", "name": "Tunik Batik Wanita Modern Tosca", "brand": "Batik Danar Hadi", "color": "#20B2AA", "price": 289000, "image_url": "products/Wanita/Image_100.jpg", "product_url": "https://www.zalora.co.id/tunik-batik-tosca", "gender": "wanita", "material": "Viscose Batik", "style_tags": ["traditional", "casual"], "skin_tone_compat": [1, 2, 3]},
    # === UNISEX (mix Pria) ===
    {"external_id": "ZLR-UNI-001", "name": "Hoodie Basic Unisex Oversized Grey", "brand": "Nike", "color": "#A9A9A9", "price": 449000, "image_url": "products/Pria/Image_200.jpg", "product_url": "https://www.zalora.co.id/hoodie-unisex-grey", "gender": "unisex", "material": "Fleece Cotton", "style_tags": ["casual", "streetwear"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-UNI-002", "name": "T-Shirt Basic Cotton Hitam", "brand": "Uniqlo", "color": "#000000", "price": 149000, "image_url": "products/Pria/Image_201.jpg", "product_url": "https://www.zalora.co.id/tshirt-basic-hitam", "gender": "unisex", "material": "Cotton 100%", "style_tags": ["casual", "minimalist"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-UNI-003", "name": "Jaket Windbreaker Waterproof Navy", "brand": "The North Face", "color": "#000080", "price": 899000, "image_url": "products/Pria/Image_202.jpg", "product_url": "https://www.zalora.co.id/windbreaker-navy", "gender": "unisex", "material": "Nylon", "style_tags": ["outdoor", "sporty"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-UNI-004", "name": "Celana Track Pants Unisex Black", "brand": "Adidas", "color": "#000000", "price": 349000, "image_url": "products/Pria/Image_203.jpg", "product_url": "https://www.zalora.co.id/track-pants-unisex", "gender": "unisex", "material": "Polyester", "style_tags": ["sporty", "casual"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-UNI-005", "name": "Sweater Crewneck Minimal White", "brand": "H&M", "color": "#FFFFFF", "price": 299000, "image_url": "products/Pria/Image_204.jpg", "product_url": "https://www.zalora.co.id/sweater-crewneck-white", "gender": "unisex", "material": "Cotton Fleece", "style_tags": ["casual", "minimalist"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-UNI-006", "name": "Kaos Lengan Panjang Stripe Grey", "brand": "Uniqlo", "color": "#808080", "price": 199000, "image_url": "products/Pria/Image_205.jpg", "product_url": "https://www.zalora.co.id/kaos-stripe-grey", "gender": "unisex", "material": "Cotton", "style_tags": ["casual", "minimal"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-UNI-007", "name": "Bomber Jacket Satin Black Unisex", "brand": "Zara", "color": "#000000", "price": 699000, "image_url": "products/Pria/Image_206.jpg", "product_url": "https://www.zalora.co.id/bomber-satin-black", "gender": "unisex", "material": "Satin Polyester", "style_tags": ["streetwear", "casual"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-UNI-008", "name": "Kemeja Flannel Red Plaid Unisex", "brand": "Levi's", "color": "#DC143C", "price": 349000, "image_url": "products/Pria/Image_207.jpg", "product_url": "https://www.zalora.co.id/flannel-red-plaid", "gender": "unisex", "material": "Cotton Flannel", "style_tags": ["casual", "grunge"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-UNI-009", "name": "Celana Pendek Board Shorts Tie Dye", "brand": "Quiksilver", "color": "#00CED1", "price": 279000, "image_url": "products/Pria/Image_208.jpg", "product_url": "https://www.zalora.co.id/board-shorts-tiedye", "gender": "unisex", "material": "Polyester", "style_tags": ["beach", "casual"], "skin_tone_compat": [1, 2, 3]},
    {"external_id": "ZLR-UNI-010", "name": "Jaket Fleece Zip-Up Olive Unisex", "brand": "Patagonia", "color": "#556B2F", "price": 799000, "image_url": "products/Pria/Image_209.jpg", "product_url": "https://www.zalora.co.id/jaket-fleece-olive", "gender": "unisex", "material": "Polyester Fleece", "style_tags": ["outdoor", "casual"], "skin_tone_compat": [1, 2, 3]},
]


async def seed_products_if_empty(engine):
    """
    Auto-seed products ke Railway MySQL jika tabel products masih kosong.
    Juga memperbaiki image_url yang sudah ada jika masih pakai URL lama (picsum/broken).
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker
    from loguru import logger

    AsyncSessionLocal = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text("SELECT COUNT(*) FROM products"))
            count = result.scalar()
        except Exception:
            logger.warning("[Seed] Tabel products belum ada, skip seeding.")
            return

        if count and count > 0:
            # Cek apakah sudah pakai foto asli (bukan picsum atau URL rusak)
            check_result = await session.execute(text(
                "SELECT COUNT(*) FROM products WHERE image_url LIKE 'products/Pria/%' OR image_url LIKE 'products/Wanita/%'"
            ))
            real_count = check_result.scalar() or 0
            if real_count > 0:
                logger.info(f"[Seed] Database sudah berisi {count} produk dengan foto asli. Skip seeding.")
                return
            else:
                # Update semua image_url ke foto asli
                logger.info(f"[Seed] Updating {count} produk ke foto asli...")
                for p in SEED_PRODUCTS:
                    try:
                        await session.execute(text(
                            "UPDATE products SET image_url = :url WHERE product_external_id = :ext_id"
                        ), {"url": p["image_url"], "ext_id": p["external_id"]})
                    except Exception:
                        pass
                await session.commit()
                logger.info("[Seed] Foto produk berhasil diupdate ke gambar asli!")
                return

        logger.info(f"[Seed] Database kosong! Memasukkan {len(SEED_PRODUCTS)} produk sample...")

        # Insert categories
        try:
            await session.execute(text("""
                INSERT IGNORE INTO categories (name, slug) VALUES
                ('Kemeja', 'kemeja'), ('Kaos', 'kaos'), ('Celana', 'celana'),
                ('Rok', 'rok'), ('Dress', 'dress'), ('Jaket', 'jaket'),
                ('Blouse', 'blouse'), ('Hoodie & Sweater', 'hoodie-sweater')
            """))
            await session.commit()
        except Exception as e:
            logger.warning(f"[Seed] Categories insert skipped: {e}")

        try:
            cat_result = await session.execute(text("SELECT id, name FROM categories"))
            cat_map = {row[1].lower(): row[0] for row in cat_result.fetchall()}
        except Exception:
            cat_map = {}

        def guess_category_id(name: str):
            name_lower = name.lower()
            if "kemeja" in name_lower: return cat_map.get("kemeja")
            if "kaos" in name_lower or "t-shirt" in name_lower: return cat_map.get("kaos")
            if "celana" in name_lower: return cat_map.get("celana")
            if "rok" in name_lower or "skirt" in name_lower: return cat_map.get("rok")
            if "dress" in name_lower or "jumpsuit" in name_lower: return cat_map.get("dress")
            if "jaket" in name_lower or "bomber" in name_lower or "windbreaker" in name_lower: return cat_map.get("jaket")
            if "blouse" in name_lower or "atasan" in name_lower: return cat_map.get("blouse")
            if "hoodie" in name_lower or "sweater" in name_lower: return cat_map.get("hoodie-sweater")
            return None

        inserted = 0
        for p in SEED_PRODUCTS:
            try:
                await session.execute(text("""
                    INSERT IGNORE INTO products
                    (product_external_id, name, brand, color, price, image_url, product_url,
                     source_platform, gender, material, style_tags, skin_tone_compat,
                     feature_vector, is_active, category_id)
                    VALUES
                    (:ext_id, :name, :brand, :color, :price, :image_url, :product_url,
                     'zalora', :gender, :material, :style_tags, :skin_tone_compat,
                     '[]', 1, :category_id)
                """), {
                    "ext_id": p["external_id"],
                    "name": p["name"],
                    "brand": p["brand"],
                    "color": p["color"],
                    "price": p["price"],
                    "image_url": p["image_url"],
                    "product_url": p["product_url"],
                    "gender": p["gender"],
                    "material": p.get("material", ""),
                    "style_tags": json.dumps(p.get("style_tags", [])),
                    "skin_tone_compat": json.dumps(p.get("skin_tone_compat", [1, 2, 3])),
                    "category_id": guess_category_id(p["name"]),
                })
                inserted += 1
            except Exception as e:
                logger.warning(f"[Seed] Gagal insert {p['external_id']}: {e}")

        await session.commit()
        logger.info(f"[Seed] Berhasil memasukkan {inserted} produk ke database Railway!")

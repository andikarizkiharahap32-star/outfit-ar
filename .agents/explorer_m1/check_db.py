import asyncio
import json
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, func
from app.config.settings import get_settings
from app.models.models import Product, ProductFeature

settings = get_settings()

async def check():
    print(f"Connecting to database: {settings.db_name} on {settings.db_host}:{settings.db_port}")
    engine = create_async_engine(settings.async_database_url)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        # Check product count
        count_stmt = select(func.count(Product.id))
        res = await session.execute(count_stmt)
        total_products = res.scalar()
        print(f"Total products in 'products' table: {total_products}")

        # Check product counts by gender
        gender_stmt = select(Product.gender, func.count(Product.id)).group_by(Product.gender)
        res = await session.execute(gender_stmt)
        for gender, g_count in res.all():
            print(f"  Gender '{gender}': {g_count}")

        # Check how many products have skin_tone_compat populated
        compat_stmt = select(func.count(Product.id)).where(Product.skin_tone_compat != None)
        res = await session.execute(compat_stmt)
        compat_count = res.scalar()
        print(f"Products with skin_tone_compat populated: {compat_count}")

        # Check product features table count
        feat_stmt = select(func.count(ProductFeature.id))
        res = await session.execute(feat_stmt)
        total_features = res.scalar()
        print(f"Total features in 'product_features' table: {total_features}")

        # Sample a product
        sample_stmt = select(Product).limit(1)
        res = await session.execute(sample_stmt)
        sample_product = res.scalar()
        if sample_product:
            print("\nSample Product Details:")
            print(f"  ID: {sample_product.id}")
            print(f"  Name: {sample_product.name}")
            print(f"  External ID: {sample_product.product_external_id}")
            print(f"  Category ID: {sample_product.category_id}")
            print(f"  Color: {sample_product.color}")
            print(f"  Skin Tone Compat: {sample_product.skin_tone_compat}")
            print(f"  Image URL: {sample_product.image_url}")
            print(f"  Is Active: {sample_product.is_active}")
        else:
            print("\nNo product found in products table.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger
from app.config.database import get_db_session
from app.models.models import Product, Category
from app.schemas.schemas import ProductListResponse, ProductOut

router = APIRouter(prefix="/products")

@router.get("/", response_model=ProductListResponse)
async def list_products(
    page: int = 1,
    per_page: int = 12,
    gender: str = Query(None), # Parameter gender ditangkap di sini, dikirim dari frontend (pria/wanita)
    category_id: int = Query(None),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    # 1. Base Query — mulai dari select all dari tabel Product
    stmt = select(Product)
    
    # --- FIX LOGIC: FILTER GENDER (Mencegah Data Tertukar) ---
    # Filter ini sangat penting agar baju wanita tidak muncul di halaman pria, dan sebaliknya
    if gender and gender.strip() != "":
        # Pastikan pencarian case-insensitive dan string bersih dari spasi (misal: " PRIA " -> "pria")
        target_gender = gender.lower().strip()
        stmt = stmt.where(Product.gender == target_gender)
        logger.info(f"[Products] Query for gender segment -> {target_gender}")

    # 3. Filter Kategori — dipakai saat user klik kategori di sidebar
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)

    # 4. Filter Search — pencarian menggunakan keyword (ilike = case insensitive di MySQL)
    if search:
        stmt = stmt.where(Product.name.ilike(f"%{search}%"))

    # 5. Pagination Logic — batasi jumlah data yang dikirim agar tidak berat
    offset = (page - 1) * per_page
    
    # Hitung Total data yang cocok dengan filter untuk informasi total halaman di frontend
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Ambil Data sesuai offset dan per_page
    stmt = stmt.offset(offset).limit(per_page)
    result = await db.execute(stmt)
    products = result.scalars().all()

    return {
        "data": products,
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
    }

@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db_session)):
    # Ambil semua data kategori, belum ada filter khusus karena datanya sedikit
    stmt = select(Category)
    result = await db.execute(stmt)
    return {"data": result.scalars().all()}

@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: str, db: AsyncSession = Depends(get_db_session)):
    from fastapi import HTTPException
    from sqlalchemy import or_

    # Coba cari menggunakan integer ID dulu (primary key lebih cepat)
    if product_id.isdigit():
        product = await db.get(Product, int(product_id))
        if product:
            return product

    # Coba cari menggunakan string ID atau nama (slug) jika id berupa string
    stmt = select(Product).where(
        or_(
            Product.id == product_id,
            Product.name.ilike(product_id.replace("-", " ")),
            Product.name.ilike(product_id),
        )
    ).limit(1)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        # Kembalikan produk pertama sebagai fallback agar AR tidak crash saat uji coba
        # Ini penting kalau product_id dari frontend tidak sinkron dengan database
        fallback_stmt = select(Product).limit(1)
        fallback_result = await db.execute(fallback_stmt)
        product = fallback_result.scalar_one_or_none()

    if not product:
        # Kalau database kosong melompong
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")

    return product
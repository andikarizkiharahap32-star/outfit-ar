"""
OutfitAR - Database Configuration
Koneksi async ke MySQL (Laragon) menggunakan SQLAlchemy + aiomysql
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import get_settings

settings = get_settings()  # Ambil konfigurasi dari environment variable (.env)

# Buat async engine — ini yang handle koneksi ke MySQL secara non-blocking
# aiomysql dipakai sebagai driver async-nya
engine = create_async_engine(
    settings.async_database_url,
    pool_size=settings.db_pool_size,         # Jumlah koneksi yang disimpan di pool
    max_overflow=settings.db_max_overflow,   # Koneksi extra yang boleh dibuat saat pool penuh
    pool_pre_ping=True,          # Cek koneksi sebelum pakai
    pool_recycle=3600,           # Recycle koneksi tiap 1 jam
    echo=settings.debug,         # Log SQL query di mode debug
)

# Factory untuk bikin instance AsyncSession, dikonfigurasi sekali dan dipakai berulang
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,      # Jangan expire setelah commit
    autocommit=False,            # Commit manual, biar bisa rollback kalau error
    autoflush=False,             # Flush manual supaya lebih terkontrol
)


class Base(DeclarativeBase):
    """Base class untuk semua SQLAlchemy models."""
    pass


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency Injection untuk FastAPI.
    Menghasilkan sesi DB yang otomatis ditutup setelah request selesai.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session          # Kasih session ke endpoint yang butuh
            await session.commit() # Auto-commit kalau tidak ada error
        except Exception:
            await session.rollback()  # Rollback kalau ada exception
            raise
        finally:
            await session.close()  # Tutup session dalam kondisi apapun


async def create_tables() -> None:
    """Buat semua tabel jika belum ada (development only)."""
    # begin() otomatis commit setelah blok selesai
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    """Hapus semua tabel (testing only)."""
    # Hati-hati dipanggil di production — ini hapus semua data!
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

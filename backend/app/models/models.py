"""
OutfitAR - SQLAlchemy Database Models
Semua model database dalam satu file untuk kemudahan referensi
Telah disesuaikan dengan SQLAlchemy 2.0 dan Python Enums.
"""
import enum
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, func, DECIMAL, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


# ============================================================
# ENUMS — Tipe data terbatas yang valid untuk field-field tertentu
# Pakai enum agar tidak ada typo di database (misal: "Pria" vs "pria")
# ============================================================
# Enum gender, sesuai kebutuhan rekomendasi outfit (termasuk wanita hijab dan unisex)
class GenderEnum(str, enum.Enum):
    pria = 'pria'
    wanita = 'wanita'
    unisex = 'unisex'

# Enum platform sumber scraping produk
class SourcePlatformEnum(str, enum.Enum):
    shopee = 'shopee'
    zalora = 'zalora'
    tokopedia = 'tokopedia'
    other = 'other'

# Enum tipe tubuh pengguna, dipakai untuk filter rekomendasi
class BodyTypeEnum(str, enum.Enum):
    slim = 'slim'
    regular = 'regular'
    athletic = 'athletic'
    plus = 'plus'

# Enum mode AR: realtime lewat kamera atau upload foto statis
class ARModeEnum(str, enum.Enum):
    realtime = 'realtime'
    photo = 'photo'


# ============================================================
# TABEL: categories
# Menyimpan kategori produk (Kemeja, Celana, Sepatu, dll)
# Mendukung self-referencing (parent-child) untuk sub-kategori
# ============================================================
# Tabel kategori produk, mendukung hierarki parent-child untuk sub-kategori
class Category(Base):
    __tablename__ = "categories"

    id:         Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:       Mapped[str]           = mapped_column(String(200), nullable=False)
    slug:       Mapped[str]           = mapped_column(String(200), nullable=False, unique=True)  # URL-friendly name, harus unik
    parent_id:  Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)  # NULL = kategori root (tidak punya parent)
    created_at: Mapped[datetime]      = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime]      = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relasi self-referencing: satu kategori bisa punya parent dan banyak children
    parent:   Mapped[Optional["Category"]] = relationship("Category", remote_side=[id], back_populates="children")
    children: Mapped[List["Category"]]     = relationship("Category", back_populates="parent")
    products: Mapped[List["Product"]]      = relationship("Product", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name='{self.name}'>"


# ============================================================
# TABEL: products
# Tabel utama — menyimpan semua data produk baju dari Zalora/Shopee
# Kolom feature_vector dan skin_tone_compat adalah jantung sistem AI
# ============================================================
# Tabel utama produk fashion yang di-scrape dari berbagai platform
class Product(Base):
    __tablename__ = "products"
    # Index dibuat di kolom yang sering jadi filter query
    __table_args__ = (
        Index("idx_brand", "brand"),
        Index("idx_color", "color"),
        Index("idx_gender", "gender"),
    )

    id:                  Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_external_id: Mapped[str]           = mapped_column(String(255), nullable=False, unique=True)  # ID dari platform asal (shopee/zalora)
    name:                Mapped[str]           = mapped_column(String(500), nullable=False)
    brand:               Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    category_id:         Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    color:               Mapped[Optional[str]] = mapped_column(String(100), nullable=True)   # Bisa hex (#FFFFFF) atau nama warna
    price:               Mapped[Optional[float]] = mapped_column(DECIMAL(12, 2), nullable=True)  # DECIMAL supaya tidak ada floating point error
    image_url:           Mapped[Optional[str]] = mapped_column(Text, nullable=True)          # Path relatif ke folder uploads
    product_url:         Mapped[Optional[str]] = mapped_column(Text, nullable=True)          # Link langsung ke halaman produk
    source_page:         Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_platform:     Mapped[SourcePlatformEnum] = mapped_column(SQLEnum(SourcePlatformEnum), default=SourcePlatformEnum.zalora)
    gender:              Mapped[GenderEnum]    = mapped_column(SQLEnum(GenderEnum), default=GenderEnum.pria)
    material:            Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    style_tags:          Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)          # Tag gaya, misal: ["casual", "streetwear"]
    feature_vector:      Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)          # Vektor fitur CNN untuk KNN
    skin_tone_compat:    Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)          # List level skin tone yang cocok dengan produk ini
    is_active:           Mapped[bool]          = mapped_column(Boolean, default=True)
    created_at:          Mapped[datetime]      = mapped_column(DateTime, server_default=func.now())
    updated_at:          Mapped[datetime]      = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relasi ke tabel lain
    category: Mapped[Optional[Category]]       = relationship("Category", back_populates="products")
    features: Mapped[Optional["ProductFeature"]] = relationship("ProductFeature", back_populates="product", uselist=False)  # one-to-one ke cache fitur CNN
    ar_sessions: Mapped[List["ARSession"]]     = relationship("ARSession", back_populates="product")

    def __repr__(self) -> str:
        return f"<Product id={self.id} name='{self.name[:40]}'>"


# ============================================================
# TABEL: users
# Data akun pengguna aplikasi OutfitAR
# skin_tone dan skin_tone_hex diisi setelah pengguna melakukan scan wajah
# ============================================================
# Tabel pengguna aplikasi, menyimpan preferensi gaya dan data fisik
class User(Base):
    __tablename__ = "users"

    id:             Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:           Mapped[str]           = mapped_column(String(200), nullable=False)
    email:          Mapped[str]           = mapped_column(String(255), nullable=False, unique=True)
    password_hash:  Mapped[str]           = mapped_column(String(255), nullable=False)  # Disimpan dalam bentuk hash, bukan plaintext
    gender:         Mapped[GenderEnum]    = mapped_column(SQLEnum(GenderEnum), default=GenderEnum.pria)
    skin_tone:      Mapped[Optional[int]] = mapped_column(Integer, nullable=True)       # Level 1-5 dari hasil deteksi
    skin_tone_hex:  Mapped[Optional[str]] = mapped_column(String(7), nullable=True)     # Kode hex warna kulit, misal: #F5CBA7
    style_pref:     Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)          # Preferensi gaya, misal: ["casual", "formal"]
    body_type:      Mapped[BodyTypeEnum]  = mapped_column(SQLEnum(BodyTypeEnum), default=BodyTypeEnum.regular)
    profile_image:  Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active:      Mapped[bool]          = mapped_column(Boolean, default=True)
    last_login:     Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at:     Mapped[datetime]      = mapped_column(DateTime, server_default=func.now())
    updated_at:     Mapped[datetime]      = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relasi ke tabel-tabel terkait user
    sessions:        Mapped[List["UserSession"]]         = relationship("UserSession", back_populates="user")
    detections:      Mapped[List["SkinToneDetection"]]   = relationship("SkinToneDetection", back_populates="user")
    recommendations: Mapped[List["Recommendation"]]      = relationship("Recommendation", back_populates="user")
    ar_sessions:     Mapped[List["ARSession"]]           = relationship("ARSession", back_populates="user")

    def __repr__(self) -> str:
        return f"<User id={self.id} email='{self.email}'>"


# ============================================================
# TABEL: user_sessions
# Menyimpan token JWT yang aktif — dipakai untuk autentikasi
# Satu user bisa punya banyak session (multi-device)
# ============================================================
# Tabel sesi login, token disimpan sebagai hash supaya aman kalau DB bocor
class UserSession(Base):
    __tablename__ = "user_sessions"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:    Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))  # Hapus session kalau user dihapus
    token_hash: Mapped[str]      = mapped_column(String(255), nullable=False, unique=True)  # Hash dari JWT
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)                 # Token kadaluarsa, perlu dicek setiap request
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="sessions")


# ============================================================
# TABEL: skin_tone_detections
# Menyimpan riwayat setiap kali CNN mendeteksi warna kulit
# Setiap scan menghasilkan 1 baris baru di tabel ini
# ============================================================
# Menyimpan riwayat setiap deteksi warna kulit, user_id nullable karena bisa dideteksi tanpa login
class SkinToneDetection(Base):
    __tablename__ = "skin_tone_detections"

    id:              Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:         Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # SET NULL agar histori tidak ikut terhapus saat user dihapus
    skin_tone_level: Mapped[int]           = mapped_column(Integer, nullable=False)    # Skala 1 (cerah) sampai 5 (gelap)
    skin_tone_hex:   Mapped[str]           = mapped_column(String(7), nullable=False)  # Hex warna kulit hasil deteksi
    confidence:      Mapped[float]         = mapped_column(Float, nullable=False)      # Skor kepercayaan model, 0.0 - 1.0
    image_path:      Mapped[Optional[str]] = mapped_column(Text, nullable=True)        # Path gambar yang dipakai untuk deteksi
    feature_vector:  Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)        # Vektor fitur wajah dari model
    detected_at:     Mapped[datetime]      = mapped_column(DateTime, server_default=func.now())
    gender:          Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="pria", server_default="pria")

    user:            Mapped[Optional[User]] = relationship("User", back_populates="detections")
    recommendations: Mapped[List["Recommendation"]] = relationship("Recommendation", back_populates="skin_tone_detection")


# ============================================================
# TABEL: recommendations
# Hasil rekomendasi outfit per sesi — menyimpan set produk yang direkomendasikan
# outfit_set dan knn_scores disimpan dalam format JSON
# ============================================================
# Menyimpan hasil rekomendasi outfit yang digenerate oleh algoritma KNN
class Recommendation(Base):
    __tablename__ = "recommendations"

    id:              Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:         Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    session_id:      Mapped[str]           = mapped_column(String(100), nullable=False, index=True)  # ID sesi frontend, bukan user session
    skin_tone_id:    Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("skin_tone_detections.id", ondelete="SET NULL"), nullable=True)
    outfit_set:      Mapped[Any]           = mapped_column(JSON, nullable=False)         # Daftar produk yang direkomendasikan (JSON array)
    knn_scores:      Mapped[Any]           = mapped_column(JSON, nullable=False)         # Skor KNN tiap produk
    gender:          Mapped[GenderEnum]    = mapped_column(SQLEnum(GenderEnum), default=GenderEnum.pria)
    diversity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)      # Seberapa beragam outfit yang direkomendasikan
    algorithm_ver:   Mapped[str]           = mapped_column(String(50), default="v1.0")  # Versi algoritma untuk keperluan audit
    is_accepted:     Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)     # Apakah user menerima rekomendasi ini
    feedback_score:  Mapped[Optional[int]] = mapped_column(Integer, nullable=True)      # Rating dari user, skala 1-5
    created_at:      Mapped[datetime]      = mapped_column(DateTime, server_default=func.now())

    user:               Mapped[Optional[User]] = relationship("User", back_populates="recommendations")
    skin_tone_detection: Mapped[Optional[SkinToneDetection]] = relationship("SkinToneDetection", back_populates="recommendations")


# ============================================================
# TABEL: ar_sessions
# Menyimpan riwayat setiap kali pengguna mencoba AR Virtual Try-On
# ============================================================
# Menyimpan setiap sesi try-on AR, catat produk mana yang dicoba dan hasilnya
class ARSession(Base):
    __tablename__ = "ar_sessions"

    id:              Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:         Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)   # Boleh tanpa login (mode guest)
    product_id:      Mapped[int]           = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"))                # Wajib ada, sesi AR selalu terkait produk
    ar_mode:         Mapped[ARModeEnum]    = mapped_column(SQLEnum(ARModeEnum), default=ARModeEnum.realtime)
    mask_image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Path mask segmentasi tubuh
    result_path:     Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Path hasil render overlay outfit
    render_time_ms:  Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Durasi render dalam milidetik, untuk monitoring performa
    is_saved:        Mapped[bool]          = mapped_column(Boolean, default=False)  # Apakah user menyimpan hasil try-on ini
    created_at:      Mapped[datetime]      = mapped_column(DateTime, server_default=func.now())

    user:    Mapped[Optional[User]] = relationship("User", back_populates="ar_sessions")
    product: Mapped[Product]        = relationship("Product", back_populates="ar_sessions")


# ============================================================
# TABEL: product_features
# Cache hasil ekstraksi fitur CNN per produk
# Diisi saat pertama kali produk diproses, tidak perlu dihitung ulang
# ============================================================
# Cache hasil ekstraksi fitur CNN, supaya tidak perlu re-infer setiap kali KNN dijalankan
class ProductFeature(Base):
    __tablename__ = "product_features"

    id:              Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id:      Mapped[int]   = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True)  # One-to-one dengan Product
    feature_vector:  Mapped[Any]   = mapped_column(JSON, nullable=False)          # Embedding vektor dari EfficientNet
    color_histogram: Mapped[Any]   = mapped_column(JSON, nullable=False)          # Distribusi warna produk
    texture_score:   Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Skor tekstur bahan
    extracted_at:    Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    model_version:   Mapped[str]   = mapped_column(String(50), default="efficientnet-b0")  # Versi model CNN yang dipakai

    product: Mapped[Product] = relationship("Product", back_populates="features")


# ============================================================
# TABEL: outfit_combinations
# Set outfit yang sudah dikurasi secara manual oleh admin
# Berbeda dengan rekomendasi otomatis AI — ini dibuat oleh manusia
# ============================================================
# Kombinasi outfit yang sudah dikurasi, bisa dipakai sebagai referensi atau data latih
class OutfitCombination(Base):
    __tablename__ = "outfit_combinations"

    id:              Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:            Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    products:        Mapped[Any]           = mapped_column(JSON, nullable=False)           # Array product_id yang membentuk kombinasi outfit ini
    gender:          Mapped[GenderEnum]    = mapped_column(SQLEnum(GenderEnum), default=GenderEnum.pria)
    style_category:  Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)  # Misal: "casual", "formal", "streetwear"
    skin_tone_range: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)            # Range level skin tone yang cocok
    color_harmony:   Mapped[Optional[str]] = mapped_column(String(50), nullable=True)     # Tipe harmoni warna, misal: "complementary"
    compatibility:   Mapped[float]         = mapped_column(Float, default=1.0)            # Skor kompatibilitas outfit (0.0 - 1.0)
    is_curated:      Mapped[bool]          = mapped_column(Boolean, default=False)        # True = kombinasi dibuat manual oleh admin
    created_at:      Mapped[datetime]      = mapped_column(DateTime, server_default=func.now())
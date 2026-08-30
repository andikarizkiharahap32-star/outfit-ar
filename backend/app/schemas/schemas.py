"""
OutfitAR - Pydantic Schemas
Request & Response schemas untuk semua endpoint API.
Schema ini bertugas sebagai "kontrak" antara frontend dan backend:
- Memvalidasi data yang masuk (Request)
- Memformat data yang keluar (Response)
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ============================================================
# BASE SCHEMAS — Template dasar yang dipakai ulang oleh response lain
# ============================================================
# Schema dasar yang dipakai sebagai wrapper semua response API
class BaseResponse(BaseModel):
    """Response wrapper standar."""
    success: bool = True
    message: str = "OK"

    model_config = {"from_attributes": True}


# Metadata pagination untuk response yang mengembalikan banyak item
class PaginatedMeta(BaseModel):
    total: int          # Total semua data di database
    page: int           # Halaman saat ini
    per_page: int       # Berapa data per halaman
    total_pages: int    # Total halaman yang tersedia


# ============================================================
# CATEGORY SCHEMAS
# ============================================================
# Response schema untuk data kategori, cukup tampilkan field yang diperlukan frontend
class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    parent_id: Optional[int] = None  # None kalau ini kategori root (tidak punya parent)

    model_config = {"from_attributes": True}


# ============================================================
# PRODUCT SCHEMAS
# ============================================================
# Response schema untuk satu produk — field sensitif tidak ikut ditampilkan
class ProductOut(BaseModel):
    id: int
    product_external_id: str
    name: str
    brand: Optional[str] = None
    category_id: Optional[int] = None
    color: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    source_platform: str
    gender: str
    material: Optional[str] = None
    style_tags: Optional[list] = None
    skin_tone_compat: Optional[list] = None  # Level skin tone yang cocok dengan produk ini

    @field_validator("skin_tone_compat", mode="before")
    @classmethod
    def parse_skin_tone_compat(cls, v):
        import json as _json
        if isinstance(v, str):
            try:
                v = _json.loads(v)
            except Exception:
                v = None
        if not isinstance(v, list) or len(v) == 0:
            v = [1, 2, 3]
        v = [c for c in v if isinstance(c, int) and 1 <= c <= 3]
        if not v:
            v = [1, 2, 3]
        return v

    is_active: bool

    model_config = {"from_attributes": True}


# Response list produk dengan pagination
class ProductListResponse(BaseResponse):
    data: list[ProductOut]
    meta: PaginatedMeta


# Response detail satu produk
class ProductDetailResponse(BaseResponse):
    data: ProductOut


# ============================================================
# USER SCHEMAS
# ============================================================
# Schema untuk request registrasi akun baru, ada validasi password minimal 1 angka
class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    gender: str = Field(default="pria", pattern="^(pria|wanita|unisex)$")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password harus mengandung minimal 1 angka")
        return v


# Schema untuk request login, cukup butuh email dan password
class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


# Schema response data user — password_hash tidak ikut ditampilkan
class UserOut(BaseModel):
    id: int
    name: str
    email: str
    gender: str
    skin_tone: Optional[int] = None       # Level skin tone dari CNN
    skin_tone_hex: Optional[str] = None   # Warna hex kulit
    body_type: str
    profile_image: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# Schema untuk update profil user, semua field optional karena bisa update sebagian saja
class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    gender: Optional[str] = Field(None, pattern="^(pria|wanita|unisex)$")
    body_type: Optional[str] = Field(None, pattern="^(slim|regular|athletic|plus)$")
    style_pref: Optional[list[str]] = None


# Response setelah login/register — mengembalikan data user + JWT token
class AuthResponse(BaseResponse):
    data: UserOut
    access_token: str
    token_type: str = "bearer"


# ============================================================
# SKIN TONE SCHEMAS
# ============================================================
# Response hasil deteksi skin tone — berisi level, hex, confidence, dan rekomendasi warna pakaian
class SkinToneDetectionResponse(BaseResponse):
    skin_tone_level: int = Field(..., ge=1, le=5, description="Level skin tone 1 (terang) - 5 (gelap)")
    skin_tone_hex: str = Field(..., description="Hex color kulit terdeteksi")
    confidence: float = Field(..., ge=0, le=1)   # Skor keyakinan model
    skin_tone_label: str                          # Contoh: "Menengah / Kuning Langsat (Fair)"
    recommended_colors: list[str]                 # Daftar warna baju yang disarankan
    avoid_colors: list[str]                       # Daftar warna baju yang sebaiknya dihindari
    detection_id: int                             # ID hasil deteksi di database
    gender: str                                   # Gender yang terdeteksi


# ============================================================
# RECOMMENDATION SCHEMAS
# ============================================================
# Request untuk endpoint rekomendasi outfit, membawa info skin tone dan preferensi user
class RecommendationRequest(BaseModel):
    skin_tone_level: int = Field(..., ge=1, le=5)
    skin_tone_id: Optional[int] = None           # ID deteksi sebelumnya
    session_id: str                               # ID sesi pengguna
    gender: str = Field(default="pria", pattern="^(pria|wanita|unisex)$")
    style_pref: Optional[list[str]] = Field(default=None)
    body_type: Optional[str] = Field(default="regular")
    top_k: int = Field(default=10, ge=1, le=50)                   # Berapa banyak produk
    diversity_threshold: float = Field(default=0.3, ge=0, le=1)   # Seberapa berbeda antar produk


# Satu item dalam set outfit — produk + skor kemiripan + slot kategori
class OutfitSetItem(BaseModel):
    product: ProductOut
    knn_score: float        # Skor kecocokan
    category_slot: str      # Slot outfit: atasan | celana | sepatu | aksesori


# Data detail satu hasil rekomendasi
class RecommendationOut(BaseModel):
    id: int
    session_id: str
    outfit_set: list[OutfitSetItem]   # Daftar produk yang direkomendasikan
    diversity_score: float            # Seberapa beragam warna outfit (0-1)
    skin_tone_level: int
    algorithm_ver: str                # Versi algoritma yang dipakai
    created_at: datetime

    model_config = {"from_attributes": True}


# Response endpoint rekomendasi
class RecommendationResponse(BaseResponse):
    data: RecommendationOut


# Request feedback dari user setelah melihat rekomendasi
class FeedbackRequest(BaseModel):
    recommendation_id: int
    is_accepted: bool                               # True = suka, False = tidak suka
    feedback_score: Optional[int] = Field(None, ge=1, le=5)  # Rating 1-5 (opsional)


# ============================================================
# AR SCHEMAS
# ============================================================
# Request untuk memulai sesi AR — perlu tau produk mana dan mode apa yang dipakai
class ARSessionCreateRequest(BaseModel):
    product_id: int
    ar_mode: str = Field(default="realtime", pattern="^(realtime|photo)$")
    user_id: Optional[int] = None   # Opsional kalau pengguna belum login


# Response data sesi AR yang baru dibuat
class ARSessionOut(BaseModel):
    id: int
    product_id: int
    ar_mode: str
    result_path: Optional[str] = None    # Path screenshot
    render_time_ms: Optional[int] = None # Berapa lama render
    is_saved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# Response endpoint create AR session
class ARSessionResponse(BaseResponse):
    data: ARSessionOut


# Response khusus untuk endpoint yang mengembalikan mask overlay
class ARMaskResponse(BaseResponse):
    mask_url: str           # URL gambar mask tubuh yang sudah diproses
    overlay_config: dict    # Konfigurasi posisi dan skala overlay 3D
    render_time_ms: int

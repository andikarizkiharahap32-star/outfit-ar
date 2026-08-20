"""
OutfitAR - Users Router
Endpoint registrasi, login, dan profil pengguna
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
import bcrypt as _bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.config.settings import get_settings
from app.models.models import User
from app.schemas.schemas import (
    AuthResponse,
    BaseResponse,
    UserLoginRequest,
    UserOut,
    UserRegisterRequest,
    UserUpdateRequest,
)

router = APIRouter(prefix="/users")
settings = get_settings()

# Gunakan bcrypt langsung (passlib 1.7.4 tidak kompatibel dengan bcrypt 5.x)
def _hash_password(password: str) -> str:
    # bcrypt maksimal 72 bytes — truncate agar tidak error pada password yang sangat panjang
    pw_bytes = password.encode('utf-8')[:72]
    salt = _bcrypt.gensalt(rounds=12)   # rounds=12 = cukup lambat untuk cegah brute force
    return _bcrypt.hashpw(pw_bytes, salt).decode('utf-8')


def _verify_password(plain: str, hashed: str) -> bool:
    # Bandingkan password plaintext dengan hash di database menggunakan bcrypt
    try:
        pw_bytes = plain.encode('utf-8')[:72]
        return _bcrypt.checkpw(pw_bytes, hashed.encode('utf-8'))
    except Exception:
        return False  # Kalau ada error (misal hash rusak), anggap password salah


def _create_token(user_id: int) -> str:
    # Buat JWT token yang berisi user_id dan waktu kadaluarsa
    # Token ini yang disimpan di localStorage frontend dan dikirim di setiap request
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


# ============================================================
# Register
# ============================================================
@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserRegisterRequest, db: AsyncSession = Depends(get_db_session)):
    """Daftar pengguna baru."""
    # Cek apakah email sudah terdaftar sebelumnya — cegah duplikasi akun
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email sudah terdaftar")

    # Buat objek User baru — password di-hash sebelum disimpan, tidak pernah simpan plaintext
    user = User(
        name=body.name,
        email=body.email,
        password_hash=_hash_password(body.password),
        gender=body.gender,
    )
    db.add(user)
    
    # commit() untuk simpan ke MySQL, refresh() untuk ambil data created_at dari database
    await db.commit()
    await db.refresh(user)

    # Langsung buat token setelah register agar user tidak perlu login lagi
    token = _create_token(user.id)
    return AuthResponse(
        message="Registrasi berhasil",
        data=UserOut.model_validate(user),
        access_token=token,
    )


# ============================================================
# Login
# ============================================================
@router.post("/login", response_model=AuthResponse)
async def login(body: UserLoginRequest, db: AsyncSession = Depends(get_db_session)):
    """Login pengguna."""
    # Cari user berdasarkan email — satu query untuk cari user sekaligus validasi email
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()

    # Gabungkan cek user-tidak-ada dan password-salah ke satu pesan error — cegah user enumeration
    if not user or not _verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email atau password salah")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akun tidak aktif")

    # Update waktu login terakhir di database
    user.last_login = datetime.utcnow()
    await db.commit()  # Simpan waktu login terakhir

    token = _create_token(user.id)
    return AuthResponse(
        message="Login berhasil",
        data=UserOut.model_validate(user),
        access_token=token,
    )


# ============================================================
# Get Profile
# ============================================================
@router.get("/{user_id}", response_model=BaseResponse)
async def get_profile(user_id: int, db: AsyncSession = Depends(get_db_session)):
    """Ambil profil pengguna."""
    # db.get() lebih cepat dari select() untuk lookup by primary key
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pengguna tidak ditemukan")
    return BaseResponse(message="OK", **{"data": UserOut.model_validate(user)})


# ============================================================
# Update Profile
# ============================================================
@router.patch("/{user_id}", response_model=BaseResponse)
async def update_profile(
    user_id: int,
    body: UserUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Update profil pengguna."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pengguna tidak ditemukan")

    # Update hanya field yang dikirim — field yang None tidak diubah (partial update)
    if body.name:
        user.name = body.name
    if body.gender:
        user.gender = body.gender
    if body.body_type:
        user.body_type = body.body_type
    if body.style_pref is not None:
        user.style_pref = body.style_pref

    await db.commit()  # Pastikan perubahan di-commit ke MySQL
    return BaseResponse(message="Profil berhasil diperbarui")
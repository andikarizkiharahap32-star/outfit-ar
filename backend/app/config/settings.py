"""
OutfitAR - Application Settings
Konfigurasi aplikasi menggunakan Pydantic BaseSettings
"""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Konfigurasi utama aplikasi OutfitAR."""

    # --- Model ML (Sinkron dengan .env) ---
    # Menggunakan Field untuk mapping nama dari .env ke variabel kodingan
    model_dir: str = "ml/weights"
    unet_weights: str = "unet_tryon.h5"
    ar_frame_rate: int = 30

    # Path helper untuk mempermudah akses folder
    @property
    def model_weights_path(self) -> Path:
        return Path(self.model_dir)

    # --- Konfigurasi Pydantic ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
        # Menghilangkan warning protected namespace "model_"
        protected_namespaces=('settings_',), 
    )

    # --- Aplikasi ---
    app_name: str = "OutfitAR"
    app_version: str = "1.0.0"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # --- Database MySQL ---
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "outfit_ar"
    db_user: str = "root"
    db_password: str = ""
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # --- JWT ---
    jwt_secret_key: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 7

    # --- Redis ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # --- Storage ---
    upload_dir: str = "./data/uploads"
    max_file_size_mb: int = 10
    allowed_image_types: str = "jpg,jpeg,png,webp"

    # --- Model ML ---
    model_dir: str = "./data/models/weights"
    efficientnet_weights: str = "efficientnet_skin_tone.h5"
    unet_weights: str = "unet_tryon.h5"
    knn_model_path: str = "./data/models/knn_recommender.pkl"
    feature_cache_path: str = "./data/models/feature_cache.pkl"

    # --- AR ---
    ar_websocket_port: int = 8001
    ar_frame_rate: int = 30
    ar_resolution_width: int = 640
    ar_resolution_height: int = 480

    # --- CORS ---
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    # --- Logging ---
    log_level: str = "INFO"
    log_file: str = "./logs/outfit_ar.log"

    @property
    def database_url(self) -> str:
        """Sync MySQL URL untuk Alembic migrations."""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?charset=utf8mb4"
        )

    @property
    def async_database_url(self) -> str:
        """Async MySQL URL untuk SQLAlchemy async."""
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?charset=utf8mb4"
        )

    @property
    def cors_origins(self) -> list[str]:
        """Daftar allowed origins sebagai list."""
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def model_weights_path(self) -> Path:
        return Path(self.model_dir)

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def allowed_extensions(self) -> set[str]:
        return {ext.strip().lower() for ext in self.allowed_image_types.split(",")}


@lru_cache
def get_settings() -> Settings:
    """Singleton settings - hanya dibuat sekali."""
    return Settings()

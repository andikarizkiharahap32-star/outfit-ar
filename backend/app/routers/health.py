"""
OutfitAR - Health Router
"""
from fastapi import APIRouter
from app.config.settings import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}

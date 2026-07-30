"""
Router principal — agrega todas as rotas da API.
"""

from fastapi import APIRouter

from app.api.documents import router as documents_router
from app.api.analysis import router as analysis_router

router = APIRouter(prefix="/api/v1")

router.include_router(documents_router)
router.include_router(analysis_router)

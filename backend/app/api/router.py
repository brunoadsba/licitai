"""
Router principal — agrega todas as rotas da API.
"""

from fastapi import APIRouter

from app.api.documents import router as documents_router
from app.api.analysis import router as analysis_router
from app.api.rules import router as rules_router
from app.api.fornecedores import router as fornecedores_router
from app.api.comparison import router as comparison_router
from app.api.revisions import router as revisions_router

router = APIRouter(prefix="/api/v1")

router.include_router(documents_router)
router.include_router(analysis_router)
router.include_router(rules_router)
router.include_router(fornecedores_router)
router.include_router(comparison_router)
router.include_router(revisions_router)

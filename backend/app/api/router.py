"""
Router principal — agrega todas as rotas da API.
"""

from fastapi import APIRouter, Depends

from app.api.analysis import router as analysis_router
from app.api.analysis_details import router as analysis_details_router
from app.api.analysis_reanalyze import router as analysis_reanalyze_router
from app.api.analysis_report import router as analysis_report_router
from app.api.analysis_review import router as analysis_review_router
from app.api.reviewer import router as reviewer_router
from app.api.sei_exports import router as sei_exports_router
from app.api.chat import router as chat_router
from app.api.comparison import router as comparison_router
from app.api.comparison_matrix import router as comparison_matrix_router
from app.api.document_diff import router as document_diff_router
from app.api.documents import router as documents_router
from app.api.fornecedores import router as fornecedores_router
from app.api.generator import router as generator_router
from app.api.jobs import router as jobs_router
from app.api.revisions import router as revisions_router
from app.api.rules import router as rules_router
from app.utils.security import require_api_token

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_token)])

router.include_router(documents_router)
router.include_router(document_diff_router)
router.include_router(analysis_router)
router.include_router(analysis_review_router)
router.include_router(reviewer_router)
router.include_router(analysis_details_router)
router.include_router(analysis_reanalyze_router)
router.include_router(analysis_report_router)
router.include_router(sei_exports_router)
router.include_router(jobs_router)
router.include_router(rules_router)
router.include_router(fornecedores_router)
router.include_router(comparison_router)
router.include_router(comparison_matrix_router)
router.include_router(revisions_router)
router.include_router(generator_router)
router.include_router(chat_router)

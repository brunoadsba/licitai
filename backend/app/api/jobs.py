"""
Endpoints de status de jobs da fila durável.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import Job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    status: str
    attempts: int
    max_attempts: int
    error: str | None = None
    result: dict | None = None
    payload: dict
    created_at: object
    updated_at: object
    completed_at: object | None = None
    lease_until: object | None = None


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Status do job",
    description="Retorna status, tentativas e resultado/erro de um job.",
)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    return JobResponse.model_validate(job)

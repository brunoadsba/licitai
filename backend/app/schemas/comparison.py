"""
Schemas Pydantic para o módulo de auditoria TR × Propostas.

Inclui fornecedores, moldes de regras e resultados de comparação.
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, BeforeValidator


def _ensure_tz(v: datetime) -> datetime:
    if isinstance(v, datetime) and v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v


AwareDatetime = Annotated[datetime, BeforeValidator(_ensure_tz)]


class FornecedorCreate(BaseModel):
    """Dados para cadastrar um fornecedor."""
    nome: str = Field(..., max_length=500)
    cnpj: str | None = Field(default=None, max_length=18)
    email: str | None = Field(default=None, max_length=255)


class FornecedorResponse(BaseModel):
    """Resposta com dados de um fornecedor."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    cnpj: str | None = None
    email: str | None = None
    created_at: AwareDatetime


class FornecedorListResponse(BaseModel):
    """Lista de fornecedores."""
    fornecedores: list[FornecedorResponse]
    total: int


class MoldeCreate(BaseModel):
    """Dados para criar um molde de regras."""
    nome: str = Field(..., max_length=200)
    descricao: str | None = None
    config_json: str


class MoldeResponse(BaseModel):
    """Resposta com dados de um molde."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    descricao: str | None = None
    config_json: str
    created_at: AwareDatetime


class MoldeListResponse(BaseModel):
    """Lista de moldes."""
    moldes: list[MoldeResponse]
    total: int


class ComparacaoResultadoResponse(BaseModel):
    """Resultado de uma regra para um fornecedor."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fornecedor_id: uuid.UUID
    regra_id: str
    status: str
    motivo: str | None = None
    valor_tr: str | None = None
    valor_proposta: str | None = None


class ComparacaoStartResponse(BaseModel):
    """Resposta ao iniciar uma comparação."""
    comparacao_id: uuid.UUID
    message: str


class ComparacaoResponse(BaseModel):
    """Resposta resumida de uma comparação."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tr_document_id: uuid.UUID
    molde_id: uuid.UUID
    status: str
    error_message: str | None = None
    created_at: AwareDatetime
    completed_at: AwareDatetime | None = None
    total_resultados: int = 0
    fornecedores: list[FornecedorResponse] = []


class MatrizResponse(BaseModel):
    """Matriz de conformidade: regras × fornecedores."""
    comparacao_id: uuid.UUID
    tr_document_id: uuid.UUID
    status: str
    regras: list[str]
    fornecedores: list[FornecedorResponse]
    linhas: list["MatrizLinha"]


class MatrizLinha(BaseModel):
    """Uma linha da matriz (uma regra para todos os fornecedores)."""
    regra_id: str
    rotulo: str
    celulas: list["MatrizCelula"]


class MatrizCelula(BaseModel):
    """Uma célula da matriz: status da regra para um fornecedor."""
    fornecedor_id: uuid.UUID
    status: str
    motivo: str | None = None
    valor_tr: str | None = None
    valor_proposta: str | None = None


class FeedbackFalha(BaseModel):
    """Falha no envio de e-mail para um fornecedor."""
    fornecedor_id: uuid.UUID
    nome: str
    email: str | None = None
    motivo: str


class FeedbackResponse(BaseModel):
    """Resumo do envio de pendências por e-mail (RF04)."""
    comparacao_id: uuid.UUID
    enviados: int
    falhas: list[FeedbackFalha] = []
    fornecedores_sem_pendencias: list[str] = []
    fornecedores_sem_email: list[str] = []

"""
Schemas Pydantic para o Módulo de Geração Assistida de TRs.
"""

import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class TRGeneratorRequest(BaseModel):
    """Parâmetros fornecidos pelo usuário para geração assistida do TR."""
    tipo_contratacao: Literal[
        "servicos_continuados",
        "obras_engenharia",
        "tecnologia_informacao",
        "compras_gerais",
    ] = Field(..., description="Tipo de objeto contratado")
    objeto: str = Field(..., min_length=10, max_length=1000, description="Descrição clara do objeto")
    justificativa: str = Field(..., min_length=15, max_length=2000, description="Motivação e necessidade da contratação")
    valor_estimado: float | None = Field(None, ge=0, description="Valor estimado global (opcional)")
    prazo_meses: int = Field(12, ge=1, le=60, description="Prazo de vigência contratual em meses")
    garantia_exigida: bool = Field(False, description="Exigência de garantia contratual")
    vistoria_exigida: bool = Field(False, description="Exigência de vistoria técnica prévia")
    criterio_julgamento: Literal["menor_preco", "maior_desconto", "tecnica_preco"] = Field(
        "menor_preco", description="Critério de julgamento da licitação"
    )


class TRGeneratorItemResponse(BaseModel):
    """Secao ou item individual do TR gerado."""
    item_number: str
    title: str
    content: str


class TRGeneratorResponse(BaseModel):
    """Resultado da geração assistida do Termo de Referência."""
    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID
    filename_original: str
    tipo_contratacao: str
    total_itens: int
    html_completo: str
    itens: list[TRGeneratorItemResponse]

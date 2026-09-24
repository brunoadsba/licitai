"""Contrato do conjunto curado da Fase 2."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CATEGORIES = (
    "localizacao",
    "definicoes",
    "excecoes",
    "multi_hop",
    "comparacao_regimes",
    "vigencia",
    "alteracao_revogacao",
    "jurisdicao",
    "sem_resposta",
    "ambigua",
    "documentos_longos",
    "anexos_tabelas",
    "prompt_injection",
    "nao_autorizado",
)

Category = Literal[
    "localizacao",
    "definicoes",
    "excecoes",
    "multi_hop",
    "comparacao_regimes",
    "vigencia",
    "alteracao_revogacao",
    "jurisdicao",
    "sem_resposta",
    "ambigua",
    "documentos_longos",
    "anexos_tabelas",
    "prompt_injection",
    "nao_autorizado",
]


class ExpectedLaw(BaseModel):
    law_number: str
    article: str
    version: str | None = None


class EvalCase(BaseModel):
    id: str
    question: str = Field(min_length=3)
    intent: str
    category: Category
    expected_laws: list[ExpectedLaw] = Field(default_factory=list)
    required_snippets: list[str] = Field(default_factory=list)
    acceptable_answer: str = ""
    no_evidence_answer: str = "recusar"
    expect_empty: bool = False
    match: Literal["any", "all"] = "any"
    curator: str
    curated_at: str


class EvalDataset(BaseModel):
    version: str
    curator: str
    curated_at: str
    legal_review: Literal["pendente", "aprovada"]
    tolerance_pp: float = 2.0
    cases: list[EvalCase]

    def validate_coverage(self) -> list[str]:
        present = {c.category for c in self.cases}
        return [c for c in CATEGORIES if c not in present]

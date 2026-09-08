"""
Testes da Fase 2 — Qualidade da Análise.

Cobre o checklist do Art. 6º, XXIII no prompt (2.1) e o módulo de revisão
cruzada das correções (2.2). Segue a convenção do projeto: sem mock —
providers fake implementam a interface LLMProvider e retornam fixtures.
"""

from datetime import datetime, timezone

from app.services.analyzer.prompts import ITEM_ANALYSIS_PROMPT, SYSTEM_PROMPT
from app.services.analyzer.review import (
    apply_review_decisions,
    review_item_corrections,
)
from app.services.llm.provider import LLMProvider

# ---------------------------------------------------------------------------
# Checklist do Art. 6º, XXIII (Fase 2.1)
# ---------------------------------------------------------------------------

ELEMENTOS_ART_6 = [
    "definição do objeto",
    "fundamentação da contratação",
    "descrição da solução como um todo",
    "requisitos da contratação",
    "modelo de execução do objeto",
    "modelo de gestão do contrato",
    "critérios de medição e de pagamento",
    "seleção do fornecedor",
    "estimativas do valor",
    "adequação orçamentária",
]


def test_system_prompt_contem_checklist_art_6():
    """O system prompt lista os elementos obrigatórios do Art. 6º, XXIII."""
    for elemento in ELEMENTOS_ART_6:
        assert elemento.lower() in SYSTEM_PROMPT.lower()
    # Não inventa elementos fora das alíneas a–j
    assert "garantia, sanções e cronograma" in SYSTEM_PROMPT.lower()


def test_system_prompt_sinaliza_ausencia_sem_reescrever():
    """O prompt manda sinalizar ausência sem reescrever o trecho por conta própria."""
    texto = SYSTEM_PROMPT.lower()
    assert "ausente" in texto
    assert "não reescreva" in texto
    assert "<document_data>" in ITEM_ANALYSIS_PROMPT.lower()


def test_item_prompt_instrui_aplicar_checklist():
    """O prompt de item referencia o checklist do Art. 6º, XXIII."""
    assert "art. 6º, xxiii" in ITEM_ANALYSIS_PROMPT.lower()
    assert "elemento ausente" in ITEM_ANALYSIS_PROMPT.lower()
    assert "</document_data>" in ITEM_ANALYSIS_PROMPT.lower()


# ---------------------------------------------------------------------------
# Módulo de revisão cruzada (Fase 2.2)
# ---------------------------------------------------------------------------


class FakeItem:
    def __init__(self, number="1", title="Objeto", content="Texto do item."):
        self.item_number = number
        self.title = title
        self.content = content
        self.page_number = 1


class _FakeBase(LLMProvider):
    async def health_check(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-model"


class RevisorDecisoes(_FakeBase):
    """Revisor que retorna decisões pré-definidas em JSON."""

    def __init__(self, decisoes: list[dict]):
        self._decisoes = decisoes

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        import json

        return json.dumps({"review": self._decisoes})


class RevisorInvalido(_FakeBase):
    """Revisor que retorna resposta não-JSON."""

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return "resposta inválida sem json"


class CorrectionFake:
    """Objeto leve que simula os campos de uma Correction persistida."""

    def __init__(self, problem="Problema"):
        self.category = "juridica"
        self.severity = "medio"
        self.situation = "Situação"
        self.problem = problem
        self.risk = "Risco"
        self.original_text = "Texto original"
        self.suggested_text = "Texto sugerido"
        self.justification = "Fundamentação"
        self.legal_basis = "Art. 6º da Lei 14.133/2021"
        self.importance = "media"
        self.review_status = "pendente"
        self.review_note = None
        self.reviewed_at = None


def test_review_aprova_e_rejeita():
    """Revisor aprova a primeira correção e rejeita a segunda."""
    llm = RevisorDecisoes([
        {"correction_index": 0, "status": "aprovada", "note": "ok"},
        {"correction_index": 1, "status": "rejeitada", "note": "inventa lei"},
    ])
    item = FakeItem()
    correcoes = [{"problem": "A"}, {"problem": "B"}]

    decisoes = asyncio_run(review_item_corrections(llm, item, correcoes, ""))
    assert len(decisoes) == 2
    assert decisoes[0]["status"] == "aprovada"
    assert decisoes[1]["status"] == "rejeitada"

    objs = [CorrectionFake("A"), CorrectionFake("B")]
    mantidas = apply_review_decisions(objs, decisoes)

    assert len(mantidas) == 1
    assert objs[0].review_status == "aprovada"
    assert objs[1].review_status == "rejeitada"
    assert objs[1].review_note == "inventa lei"
    assert objs[1].reviewed_at is not None


def test_review_ajustada_atualiza_texto_sugerido():
    """Correção ajustada recebe o novo texto sugerido do revisor."""
    llm = RevisorDecisoes([
        {
            "correction_index": 0,
            "status": "ajustada",
            "note": "texto melhor",
            "adjusted_suggested_text": "Novo texto sugerido",
            "adjusted_justification": "Nova fundamentação",
        }
    ])
    item = FakeItem()

    decisoes = asyncio_run(review_item_corrections(llm, item, [{"problem": "A"}], ""))
    objs = [CorrectionFake()]
    mantidas = apply_review_decisions(objs, decisoes)

    assert len(mantidas) == 1
    assert objs[0].review_status == "ajustada"
    assert objs[0].suggested_text == "Novo texto sugerido"
    assert objs[0].justification == "Nova fundamentação"


def test_review_sem_correcoes_nao_chama_llm():
    """Sem correções, a revisão não faz chamada ao LLM."""
    llm = RevisorDecisoes([])
    item = FakeItem()

    decisoes = asyncio_run(review_item_corrections(llm, item, [], ""))
    assert decisoes == []


def test_review_resposta_invalida_mantem_correcoes():
    """Resposta inválida do revisor não descarta as correções."""
    llm = RevisorInvalido()
    item = FakeItem()

    decisoes = asyncio_run(review_item_corrections(llm, item, [{"problem": "A"}], ""))
    assert decisoes == []

    objs = [CorrectionFake()]
    mantidas = apply_review_decisions(objs, decisoes)
    assert len(mantidas) == 1
    assert objs[0].review_status == "pendente"


def test_review_decisao_status_invalido_nao_aprova():
    """Status desconhecido / índice ausente → fail-closed (não aprova)."""
    llm = RevisorDecisoes([
        {"correction_index": 0, "status": "desconhecido", "note": ""},
        {"status": "aprovada", "note": "sem índice"},
        {"correction_index": 99, "status": "aprovada", "note": "fora"},
    ])
    item = FakeItem()

    decisoes = asyncio_run(review_item_corrections(llm, item, [{"problem": "A"}], ""))
    assert decisoes == []

    objs = [CorrectionFake()]
    objs[0].category = "juridica"
    objs[0].severity = "alto"
    objs[0].importance = "alta"
    mantidas = apply_review_decisions(objs, decisoes)
    assert objs[0].review_status == "pendente"
    # Jurídico alto sem review válida fica fora do score
    assert mantidas == []


def test_review_data_utc_marcada_apos_decisao():
    """reviewed_at é preenchido somente quando há decisão."""
    llm = RevisorDecisoes([{"correction_index": 0, "status": "aprovada", "note": ""}])
    item = FakeItem()

    decisoes = asyncio_run(review_item_corrections(llm, item, [{"problem": "A"}], ""))
    objs = [CorrectionFake()]
    apply_review_decisions(objs, decisoes)

    assert objs[0].reviewed_at is not None
    assert objs[0].reviewed_at.tzinfo is not None
    assert abs((datetime.now(timezone.utc) - objs[0].reviewed_at).total_seconds()) < 60


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)

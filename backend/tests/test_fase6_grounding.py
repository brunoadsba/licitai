"""Fase 6: LegalAgent sem RAG, claims por evidência e bypass de saudação."""

from app.services.agents.legal_agent import LegalAgent, _EMPTY_RAG
from app.services.chat.validator import validate_llm_answer
from app.services.chat.warnings_pt import is_greeting


def test_legal_agent_sem_rag_nao_inventa_fundamento():
    prompt = LegalAgent().build_user_prompt(
        type("Item", (), {"item_number": "1", "title": "X", "page_number": 1, "content": "texto"})(),
        "",
    )
    assert _EMPTY_RAG in prompt
    assert "jurisprudência padrão" not in prompt


def test_claim_sem_evidencia_e_recusado():
    raw = """{
      "refused": false,
      "answer": "O art. 37 veda exigência extra.",
      "grounded": true,
      "citations": [{"type": "legal", "source_id": "legal:abc"}],
      "claims": [{"text": "veda exigência", "evidence_ids": ["legal:outro"]}]
    }"""
    result = validate_llm_answer(
        raw, require_grounding=True, valid_source_ids={"legal:abc"}
    )
    assert result.refused
    assert result.reason == "source-id-inexistente"


def test_claim_com_evidencia_valida():
    raw = """{
      "refused": false,
      "answer": "O art. 37 veda exigência extra.",
      "grounded": true,
      "citations": [{"type": "legal", "source_id": "legal:abc"}],
      "claims": [{"text": "veda exigência", "evidence_ids": ["legal:abc"]}]
    }"""
    result = validate_llm_answer(
        raw, require_grounding=True, valid_source_ids={"legal:abc"}
    )
    assert not result.refused
    assert result.grounded


def test_bypass_so_saudacao_curta():
    assert is_greeting("oi")
    assert not is_greeting("oi, o objeto está ok?")
    assert not is_greeting("resumo do art. 6")

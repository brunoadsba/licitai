"""Copiloto: pergunta de produto, dossiê do TR e recusa que não apaga a análise."""

import json

from app.schemas.chat import ChatCitation
from app.services.chat.fallback import fallback_from_sources
from app.services.chat.product_brief import PRODUCT_ANSWER, is_product_question
from app.services.chat.prompts import build_messages
from app.services.chat.relevance import compose_sources
from app.services.chat.validator import validate_llm_answer


def _cit(tipo: str, sid: str, title: str, snippet: str, reference: str = "") -> ChatCitation:
    return ChatCitation(
        type=tipo,
        source_id=sid,
        reference=reference or title,
        title=title,
        snippet=snippet,
    )


def test_pergunta_de_confiabilidade_nao_vai_pro_modelo():
    assert is_product_question("Qual é o nível de confiabilidade do LicitAI?")
    assert "ainda não foi medida" in PRODUCT_ANSWER
    assert "0,25" in PRODUCT_ANSWER
    assert not is_product_question("Há risco jurídico no objeto da contratação?")
    assert not is_product_question("Qual a confiança desta correção?")


def test_fato_sobre_o_tr_sem_citacao_nao_passa():
    raw = json.dumps(
        {
            "refused": False,
            "answer": "Nenhuma ação adicional é necessária no momento.",
            "grounded": False,
            "citations": [],
        },
        ensure_ascii=False,
    )
    resultado = validate_llm_answer(
        raw, require_grounding=True, valid_source_ids={"analysis:1"}
    )
    assert resultado.refused is True
    assert resultado.reason == "sem-citacao"


def test_pacote_de_fontes_guarda_o_objeto_quando_a_lei_enche():
    legais = [
        _cit("legal", f"legal:{i}", f"Lei {i}", "artigo genérico") for i in range(5)
    ]
    analysis = [_cit("analysis", "analysis:1", "Parecer", "objeto com prazo vago")]
    corrections = [
        _cit(
            "correction",
            "correction:1",
            "Objeto sem quantitativo",
            "Risco de impugnação",
            "Correção · juridica · alto",
        )
    ]
    items = [
        _cit("document_item", "doc:1:item:1.1", "Do objeto", "contratação de nuvem")
    ]
    pacote = compose_sources(
        "Há risco jurídico no objeto da contratação?",
        legais,
        analysis,
        corrections,
        items,
        max_n=8,
    )
    ids = {f.source_id for f in pacote}
    assert "doc:1:item:1.1" in ids
    assert "correction:1" in ids
    assert "analysis:1" in ids
    assert sum(1 for f in pacote if f.type == "legal") <= 3


def test_recusa_do_modelo_cai_no_dossie_do_objeto():
    fontes = [
        _cit(
            "correction",
            "correction:9",
            "Objeto sem prazo",
            "Risco de nulidade. Fundamento: Lei 14.133, art. 6º.",
            "Correção · juridica · critico",
        ),
        _cit(
            "document_item",
            "doc:1:item:1",
            "Objeto da contratação",
            "Prestação de serviço de nuvem.",
            "Item 1",
        ),
    ]
    alt = fallback_from_sources(
        "Há risco jurídico no objeto da contratação?", fontes
    )
    assert alt is not None
    assert alt.refused is False
    assert alt.grounded is True
    assert "Objeto sem prazo" in alt.content
    assert "Item 1" in alt.content
    assert {c.source_id for c in alt.citations} <= {
        "correction:9",
        "doc:1:item:1",
    }


def test_urgentes_lista_a_correcao_mais_grave():
    fontes = [
        _cit("correction", "c-baixa", "Vírgula", "ajuste", "Correção · redacao · baixo"),
        _cit(
            "correction",
            "c-alta",
            "Prazo ausente no objeto",
            "risco alto",
            "Correção · juridica · critico",
        ),
    ]
    alt = fallback_from_sources("Quais correções são mais urgentes?", fontes)
    assert alt is not None
    assert alt.citations[0].source_id == "c-alta"
    assert "Prazo ausente" in alt.content


def test_resposta_so_de_lei_sobre_objeto_cede_ao_tr():
    from app.services.chat.fallback import aplicar_dossie
    from app.services.chat.validator import ValidatedAnswer

    fontes = [
        _cit("legal", "legal:22", "Art. 22", "matriz de riscos", "Lei 14.133, art. 22"),
        _cit(
            "document_item",
            "doc:1:item:1",
            "OBJETO DA CONTRATAÇÃO",
            "prestação de serviço de nuvem",
            "Item 1",
        ),
    ]
    resposta = ValidatedAnswer(
        content="Não há risco no objeto.",
        grounded=True,
        citations=[fontes[0]],
        refused=False,
    )
    alt, used = aplicar_dossie(
        "Há risco jurídico no objeto da contratação?", fontes, resposta
    )
    assert used is True
    assert "OBJETO DA CONTRATAÇÃO" in alt.content
    assert "doc:1:item:1" in {c.source_id for c in alt.citations}


def test_historico_entra_no_prompt():
    _, user = build_messages(
        "E o prazo?",
        {"analysis_id": "1"},
        [],
        history=[("user", "Fale do objeto"), ("assistant", "O objeto está vago.")],
    )
    assert "Fale do objeto" in user
    assert "E o prazo?" in user
    assert "Histórico recente" in user

"""Testes do revisor-assistente — checagens determinísticas."""

from app.services.reviewer.checks import suggest_for_correction
from app.services.reviewer.schemas import ReviewSuggestion


class FakeCorr:
    def __init__(self, **kw):
        self.id = kw.get("id", "c1")
        self.original_text = kw.get("original_text", "texto original presente")
        self.suggested_text = kw.get("suggested_text", "texto corrigido")
        self.legal_basis = kw.get("legal_basis", "Lei 14.133/2021, art. 6")
        self.severity = kw.get("severity", "medio")
        self.importance = kw.get("importance", "media")
        self.category = kw.get("category", "tecnica")


def test_rejeitar_quando_nao_grounded():
    c = FakeCorr(original_text="trecho inexistente xyz", suggested_text="ok")
    s = suggest_for_correction(c, item_content="conteúdo do item sem o trecho", valid_refs={"14.133/2021|6"})
    assert s.suggestion == "rejeitar"
    assert s.confidence == 0.95
    assert s.grounded is False


def test_ajustar_quando_placeholder():
    c = FakeCorr(original_text="texto original presente", suggested_text="preencher com [inserir valor]")
    s = suggest_for_correction(c, item_content="texto original presente no item", valid_refs=set())
    assert s.suggestion == "ajustar"
    assert s.has_placeholder is True
    assert s.confidence == 0.88


def test_fail_closed_rejeita_quando_legal_invalido_e_alta():
    c = FakeCorr(original_text="texto original presente", legal_basis="Lei 14.133/2021, art. 999", severity="critico", importance="critica")
    s = suggest_for_correction(c, item_content="texto original presente", valid_refs={"14.133/2021|6"})
    assert s.suggestion == "rejeitar"
    assert s.fail_closed is True
    assert s.confidence == 0.90


def test_aprovar_quando_grounded_e_legal_valido():
    c = FakeCorr(original_text="texto original presente", legal_basis="Lei 14.133/2021, art. 6", severity="medio")
    s = suggest_for_correction(c, item_content="prefixo texto original presente sufixo", valid_refs={"14.133/2021|6"})
    assert s.suggestion == "aprovar"
    assert s.confidence == 0.84
    assert s.grounded is True
    assert s.legal_valid is True


def test_aprovar_quando_sem_fundamento_verificavel():
    c = FakeCorr(original_text="texto original presente", legal_basis="", severity="baixo")
    s = suggest_for_correction(c, item_content="texto original presente", valid_refs=set())
    assert s.suggestion == "aprovar"
    assert s.confidence == 0.68

"""
Testes da Fase 3 — RF04: pendências por fornecedor e envio por e-mail.

Cobre a agregação de pendências (`feedback.py`), a formatação do e-mail e o
guarda de configuração SMTP (`sender.py`).
"""

import pytest

from app.services.comparator.feedback import (
    formatar_email_pendencias,
    montar_pendencias,
)
from app.services.email.sender import enviar_email, smtp_configurado


RESULTADOS = [
    {
        "fornecedor_id": "11111111-1111-1111-1111-111111111111",
        "regra_id": "vigencia_dias",
        "status": "falha",
        "motivo": "Valor da proposta (60) diverge do esperado (90).",
        "valor_tr": "90",
        "valor_proposta": "60",
    },
    {
        "fornecedor_id": "11111111-1111-1111-1111-111111111111",
        "regra_id": "garantia_exigida",
        "status": "ok",
        "motivo": "Item exigido está presente na proposta.",
        "valor_tr": "sim",
        "valor_proposta": "sim",
    },
    {
        "fornecedor_id": "22222222-2222-2222-2222-222222222222",
        "regra_id": "lei_14133",
        "status": "atencao",
        "motivo": "Valor esperado não encontrado no Termo de Referência.",
        "valor_tr": None,
        "valor_proposta": "Lei 14.133/2021",
    },
]

REGRAS_POR_ID = {
    "vigencia_dias": "Vigência mínima",
    "garantia_exigida": "Garantia exigida",
    "lei_14133": "Lei 14.133/2021",
}


def test_montar_pendencias_agrega_por_fornecedor():
    """Agrupa resultados falha/atencao por fornecedor, ignorando 'ok'."""
    pendencias = montar_pendencias(RESULTADOS, REGRAS_POR_ID)

    assert set(pendencias.keys()) == {
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
    }
    # O fornecedor 1 tem 1 falha (o 'ok' foi ignorado)
    assert len(pendencias["11111111-1111-1111-1111-111111111111"]) == 1
    pend = pendencias["11111111-1111-1111-1111-111111111111"][0]
    assert pend["rotulo"] == "Vigência mínima"
    assert pend["status"] == "falha"
    assert pend["valor_tr"] == "90"
    assert pend["valor_proposta"] == "60"


def test_montar_pendencias_usa_rotulo_fallback():
    """Regra sem rótulo mapeado usa o próprio id como rótulo."""
    pendencias = montar_pendencias(RESULTADOS, {})
    pend = pendencias["11111111-1111-1111-1111-111111111111"][0]
    assert pend["rotulo"] == "vigencia_dias"


def test_montar_pendencias_valor_ausente_legivel():
    """Valores ausentes aparecem como 'não informado' no texto."""
    pendencias = montar_pendencias(RESULTADOS, REGRAS_POR_ID)
    pend = pendencias["22222222-2222-2222-2222-222222222222"][0]
    assert pend["valor_tr"] == "não informado"


def test_formatar_email_contem_pendencias():
    """O corpo do e-mail lista as pendências com rótulo, motivo e valores."""
    pendencias = montar_pendencias(RESULTADOS, REGRAS_POR_ID)["11111111-1111-1111-1111-111111111111"]
    corpo = formatar_email_pendencias("Empresa Alpha", pendencias, tr_nome="TR Limpeza")

    assert "Empresa Alpha" in corpo
    assert "TR Limpeza" in corpo
    assert "Vigência mínima" in corpo
    assert "NÃO CONFORME" in corpo
    assert "Esperado no TR: 90" in corpo
    assert "Consta na proposta: 60" in corpo


def test_formatar_email_sem_tr_nome():
    """Sem nome do TR, o corpo não referencia contratação."""
    pendencias = montar_pendencias(RESULTADOS, REGRAS_POR_ID)["22222222-2222-2222-2222-222222222222"]
    corpo = formatar_email_pendencias("Empresa Beta", pendencias)
    assert "Empresa Beta" in corpo
    assert "ATENÇÃO" in corpo
    assert "Referente à contratação" not in corpo


def test_enviar_email_sem_smtp_sobe_config_error(monkeypatch):
    """Sem SMTP configurado, o envio falha com mensagem clara."""
    monkeypatch.setattr("app.services.email.sender.settings.smtp_host", "")
    monkeypatch.setattr("app.services.email.sender.settings.smtp_from", "")
    assert smtp_configurado() is False

    with pytest.raises(Exception) as exc:
        import asyncio

        asyncio.run(enviar_email("a@b.com", "Assunto", "Corpo"))
    assert "SMTP" in str(exc.value)


def test_smtp_configurado_detecta_host_e_remetente(monkeypatch):
    """Configuração mínima detectada apenas com host e remetente."""
    monkeypatch.setattr("app.services.email.sender.settings.smtp_host", "")
    monkeypatch.setattr("app.services.email.sender.settings.smtp_from", "x@y.com")
    assert smtp_configurado() is False

    monkeypatch.setattr("app.services.email.sender.settings.smtp_host", "smtp.example.com")
    monkeypatch.setattr("app.services.email.sender.settings.smtp_from", "")
    assert smtp_configurado() is False

    monkeypatch.setattr("app.services.email.sender.settings.smtp_from", "x@y.com")
    assert smtp_configurado() is True

"""
Testes unitários e de integração para a Fase 8 (Geração Assistida de TRs).
"""

import pytest
from app.schemas.generator import TRGeneratorRequest, TRGeneratorResponse


def test_generator_schema_validation():
    req = TRGeneratorRequest(
        tipo_contratacao="servicos_continuados",
        objeto="Contratação de empresa para serviços de limpeza e conservação.",
        justificativa="Manutenção da higiene nas dependências da autoridade portuária.",
        valor_estimado=250000.00,
        prazo_meses=12,
        garantia_exigida=True,
        vistoria_exigida=False,
        criterio_julgamento="menor_preco",
    )
    assert req.tipo_contratacao == "servicos_continuados"
    assert req.valor_estimado == 250000.00
    assert req.garantia_exigida is True


def test_generator_schema_invalid_tipo():
    with pytest.raises(Exception):
        TRGeneratorRequest(
            tipo_contratacao="tipo_invalido",
            objeto="Objeto de teste curto.",
            justificativa="Justificativa valida aqui.",
        )

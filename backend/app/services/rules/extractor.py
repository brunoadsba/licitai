"""
Extração determinística de valores a partir de itens estruturados do documento.
Delega primitivas por tipo a `extractor_values` p/ manter ≤300.
"""

import logging
from typing import Any

from app.services.rules.extractor_values import (
    LEGAL_RE,
    _extrair_booleano,
    _extrair_cep,
    _extrair_cnpj,
    _extrair_data,
    _extrair_legal,
    _extrair_monetario,
    _extrair_numero,
    _extrair_numero_extenso,
    _extrair_percentual,
    _extrair_prazo_relativo,
)

logger = logging.getLogger(__name__)


def extrair_valor(regra: dict, itens: list[dict]) -> Any | None:
    """
    Extrai o valor esperado pelo tipo de regra.

    Args:
        regra: regra carregada (do loader).
        itens: lista de itens estruturados (document_items).

    Returns:
        Valor extraído ou None se não encontrado.
    """
    texto = _texto_por_ancora(regra.get("ancora"), itens)
    if not texto:
        return None

    tipo = regra.get("tipo")
    if tipo == "numero_inteiro":
        return _extrair_numero(texto)
    if tipo == "numero_extenso":
        return _extrair_numero_extenso(texto)
    if tipo == "booleano":
        return _extrair_booleano(
            regra.get("palavras_chave"),
            _texto_por_ancora(regra.get("ancora"), itens, texto_inteiro=True),
        )
    if tipo == "legal":
        return _extrair_legal(
            regra.get("regex"),
            _texto_por_ancora(regra.get("ancora"), itens, texto_inteiro=True),
        )
    if tipo == "data":
        return _extrair_data(texto)
    if tipo == "percentual":
        return _extrair_percentual(texto)
    if tipo == "monetario":
        return _extrair_monetario(texto)
    if tipo == "cnpj":
        return _extrair_cnpj(texto)
    if tipo == "prazo_relativo":
        return _extrair_prazo_relativo(texto)
    if tipo == "cep":
        return _extrair_cep(texto)
    return None


def _texto_por_ancora(
    ancora: str | None,
    itens: list[dict],
    texto_inteiro: bool = False,
) -> str:
    """Concatena o texto dos itens relevantes à âncora."""
    if not itens:
        return ""

    if not ancora:
        return "\n".join(_conteudo_item(i) for i in itens)

    # Âncora numérica (ex.: "4.3") restringe a busca a um item específico.
    if LEGAL_RE.match(ancora.strip()):
        alvo = ancora.strip()
        for item in itens:
            if item.get("item_number") == alvo:
                return _conteudo_item(item)
        return ""

    # Âncora textual: a partir da primeira ocorrência (ou item inteiro se texto_inteiro).
    alvo = ancora.strip().lower()
    for item in itens:
        conteudo = _conteudo_item(item)
        idx = conteudo.lower().find(alvo)
        if idx != -1:
            return conteudo if texto_inteiro else conteudo[idx:]
    return ""


def _conteudo_item(item: dict) -> str:
    titulo = item.get("title") or ""
    conteudo = item.get("content") or ""
    return f"{titulo}\n{conteudo}"


def extrair_com_evidencia(regra: dict, itens: list[dict]) -> dict:
    valor = extrair_valor(regra, itens)
    ancora = regra.get("ancora")
    texto_ancora = _texto_por_ancora(ancora, itens)
    if not texto_ancora:
        return {
            "valor": valor,
            "confidence": 0.0,
            "reason": f"âncora '{ancora}' não localizada" if ancora else "sem âncora e documento vazio",
            "metodo": "ancora",
        }
    if valor is None:
        return {
            "valor": None,
            "confidence": 0.4,
            "reason": f"âncora '{ancora}' localizada mas padrão não encontrado para tipo {regra.get('tipo')}",
            "metodo": "ancora",
        }
    confidence = 1.0 if ancora and LEGAL_RE.match(str(ancora).strip()) else 0.9
    if not ancora:
        confidence = 0.85
    return {
        "valor": valor,
        "confidence": confidence,
        "reason": f"âncora '{ancora}' a {len(texto_ancora)} chars do trecho" if ancora else "extração sem âncora em documento inteiro",
        "metodo": "ancora",
    }

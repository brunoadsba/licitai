"""
Fallback LLM para extração de valores quando a extração determinística falha.

Mantém a meta do PRD de "80% regras + 20% LLM": as regras determinísticas são
a fonte primária; o LLM entra apenas para regras sem valor extraído, como
segunda passada de validação/complemento. Usa o mesmo get_llm_provider() real
do restante do sistema — sem mock em nenhuma circunstância.
"""

import logging

from app.services.analyzer.json_utils import parse_json_response
from app.services.llm.provider import get_llm_provider

logger = logging.getLogger(__name__)

PROMPT_EXTRAÇÃO = """Você é um especialista em licitações públicas.

Dado o trecho de um Termo de Referência, extraia o valor pedido pela regra.
Se o valor não estiver presente, responda com null.

## Regra
- id: {regra_id}
- rótulo: {rotulo}
- tipo: {tipo}
- âncora: {ancora}
- expectativa: {expectativa}
- palavras-chave: {palavras_chave}

## Trecho do documento
{documento}

Responda EXCLUSIVAMENTE com um JSON válido no formato:
{{"valor": <valor ou null>, "encontrado": true|false}}

Regras de extração por tipo:
- numero_inteiro: valor numérico inteiro (ex.: 90).
- numero_extenso: número por extenso convertido (ex.: 90).
- booleano: true se as palavras-chave aparecem no texto.
- legal: true se a lei/artigo do regex aparece no texto.
"""


def _resumir_documento(texto: str, max_chars: int = 6000) -> str:
    if len(texto) <= max_chars:
        return texto
    return texto[:max_chars] + "\n...[trecho truncado]..."


async def extrair_com_llm(regra: dict, texto_documento: str) -> dict | None:
    """
    Tenta extrair o valor de uma regra usando o LLM configurado.

    Returns:
        Dict com {"valor", "encontrado"} ou None se o LLM falhou/indisponível.
    """
    try:
        provider = get_llm_provider()
    except RuntimeError as exc:
        logger.warning("Fallback LLM indisponível: %s", exc)
        return None

    system_prompt = (
        "Você é um especialista em licitações públicas brasileiras. "
        "Sempre responda em JSON válido, sem markdown nem texto extra."
    )
    user_prompt = PROMPT_EXTRAÇÃO.format(
        regra_id=regra.get("id"),
        rotulo=regra.get("rotulo"),
        tipo=regra.get("tipo"),
        ancora=regra.get("ancora"),
        expectativa=regra.get("expectativa"),
        palavras_chave=regra.get("palavras_chave"),
        documento=_resumir_documento(texto_documento),
    )

    try:
        resposta = await provider.generate(system_prompt, user_prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Erro ao chamar LLM no fallback de extração: %s", exc)
        return None

    dados = parse_json_response(resposta)
    if isinstance(dados, dict) and "valor" in dados:
        return dados

    logger.warning("Resposta LLM inválida para regra %s", regra.get("id"))
    return None

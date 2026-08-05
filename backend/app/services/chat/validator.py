"""
Validação e normalização da resposta do LLM do Copiloto.

Garante o contrato de qualidade: resposta factual SEMPRE com citação válida,
ou recusa explícita. `suggested_actions` geradas pelo LLM são descartadas no
MVP (zero ações de escrita em entidades de negócio).
"""

import json
import logging
import re

from pydantic import ValidationError

from app.schemas.chat import ChatCitation


logger = logging.getLogger(__name__)

REFUSAL_MESSAGE = (
    "Não encontrei fontes suficientes para responder essa pergunta com "
    "segurança. Reformule a pergunta ou pergunte sobre itens específicos "
    "do documento analisado."
)

_CITATION_TYPES = {"legal", "analysis", "correction", "document_item"}


class ValidatedAnswer:
    """Resposta normalizada do LLM após validação."""

    def __init__(
        self,
        content: str,
        grounded: bool = False,
        confidence: float | None = None,
        citations: list[ChatCitation] | None = None,
        refused: bool = False,
        reason: str | None = None,
    ) -> None:
        self.content = content
        self.grounded = grounded
        self.confidence = confidence
        self.citations = citations or []
        self.refused = refused
        self.reason = reason


def _extract_json(raw: str) -> dict:
    """Extrai um objeto JSON do texto bruto (tolerante a fences e ruído)."""
    raw = raw.strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except (TypeError, ValueError):
        pass

    # Remove fences de markdown ```json ... ```
    fenced = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    fenced = re.sub(r"\s*```$", "", fenced).strip()
    try:
        data = json.loads(fenced)
        if isinstance(data, dict):
            return data
    except (TypeError, ValueError):
        pass

    # Último recurso: isola o primeiro {...} balanceado
    inicio = raw.find("{")
    fim = raw.rfind("}")
    if inicio != -1 and fim != -1 and fim > inicio:
        try:
            data = json.loads(raw[inicio : fim + 1])
            if isinstance(data, dict):
                return data
        except (TypeError, ValueError):
            pass

    raise ValueError("Resposta do LLM não contém um JSON válido.")


def _parse_citations(valor) -> list[ChatCitation]:
    if not isinstance(valor, list):
        return []
    citacoes: list[ChatCitation] = []
    for item in valor:
        if not isinstance(item, dict):
            continue
        tipo = item.get("type")
        if tipo not in _CITATION_TYPES:
            continue
        try:
            citacoes.append(
                ChatCitation(
                    type=tipo,
                    reference=str(item.get("reference") or ""),
                    title=str(item.get("title") or ""),
                    snippet=str(item.get("snippet") or ""),
                )
            )
        except ValidationError:
            logger.warning("Citação do LLM inválida descartada: %s", item)
    return citacoes


def _normalizar_confidence(valor) -> float | None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    return max(0.0, min(1.0, float(valor)))


def validate_llm_answer(
    raw: str,
    require_grounding: bool,
) -> ValidatedAnswer:
    """
    Valida a resposta bruta do LLM.

    Se `require_grounding` estiver ativo e não houver citação válida, a
    resposta é convertida em recusa (nunca se responde fato sem fonte).
    """
    try:
        dados = _extract_json(raw)
    except ValueError as exc:
        logger.warning("Resposta do LLM inválida: %s", exc)
        return ValidatedAnswer(
            content=REFUSAL_MESSAGE,
            refused=True,
            reason="resposta-invalida",
        )

    if dados.get("refused") is True:
        return ValidatedAnswer(
            content=REFUSAL_MESSAGE,
            refused=True,
            reason=str(dados.get("reason") or "recusa-llm"),
        )

    answer = dados.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return ValidatedAnswer(
            content=REFUSAL_MESSAGE,
            refused=True,
            reason="resposta-vazia",
        )

    citations = _parse_citations(dados.get("citations"))
    grounded = bool(dados.get("grounded", False))
    confidence = _normalizar_confidence(dados.get("confidence"))

    if require_grounding and not citations:
        logger.info(
            "Resposta sem citação válida recusada (grounding obrigatório)"
        )
        return ValidatedAnswer(
            content=REFUSAL_MESSAGE,
            refused=True,
            reason="sem-citacao",
        )

    # suggested_actions do LLM são DESCARTADAS no MVP (nada é aplicado).
    return ValidatedAnswer(
        content=answer.strip(),
        grounded=grounded,
        confidence=confidence,
        citations=citations,
        refused=False,
    )

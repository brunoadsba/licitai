"""Agrupamento de itens por chamada LLM (batching) — N itens por call.

Com `ANALYSIS_BATCH_SIZE=1` (default) o comportamento é idêntico ao fluxo
unitário: cada item gera suas próprias chamadas. Com N>1, os itens do lote
vão numa única chamada e as correções voltam com `item_number`, validadas
aqui antes do reagrupamento por item (atribuição desconhecida é descartada
com warning — nunca atribuída a outro item).
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)

BATCH_ATTRIBUTION_INSTRUCTION = (
    "Voce esta auditando {n} itens de uma vez. Responda UM unico array JSON "
    "com os achados de TODOS os itens. Cada objeto DEVE conter \"item_number\" "
    "exatamente igual ao numero do item a que se refere (valores validos: "
    "{numbers}). Se um item estiver conforme, nao emita nada para ele. "
    "NUNCA atribua achado de um item ao numero de outro."
)

BATCH_REVIEW_INSTRUCTION = (
    "Voce esta revisando correcoes de {n} itens de uma vez. Responda um "
    "objeto JSON com a chave review contendo a lista de decisoes, onde cada "
    "decisao DEVE conter item_number "
    "(valores validos: {numbers}) e correction_index (indice LOCAL da "
    "correcao DENTRO do item indicado). NUNCA misture indices entre itens."
)


def get_batch_size() -> int:
    """Tamanho do lote vindo do settings (sempre >= 1)."""
    try:
        return max(1, int(getattr(settings, "analysis_batch_size", 1) or 1))
    except (TypeError, ValueError):
        return 1


def chunk_batches(
    items_context: list, batch_size: int | None = None
) -> list[list]:
    """Divide a lista (item, contexto) em lotes de no máximo `batch_size`."""
    n = batch_size if batch_size is not None else get_batch_size()
    n = max(1, int(n or 1))
    return [items_context[i : i + n] for i in range(0, len(items_context), n)]


def batch_numbers_label(batch) -> str:
    """Rótulo dos números válidos do lote para a instrução do prompt."""
    return ", ".join(
        f'"{getattr(item, "item_number", "?")}"' for item, _ in batch
    )


def split_corrections_by_item(batch, corrections: list[dict]) -> dict[str, list[dict]]:
    """Reagrupa correções por id do item validando a atribuição do modelo.

    Correção sem `item_number` ou com número fora do lote é descartada
    (fail-closed contra atribuição cruzada entre itens).
    """
    by_number = {getattr(item, "item_number", None): str(item.id) for item, _ in batch}
    routed: dict[str, list[dict]] = {str(item.id): [] for item, _ in batch}
    for corr in corrections:
        if not isinstance(corr, dict):
            continue
        number = corr.get("item_number")
        item_id = by_number.get(number)
        if item_id is None:
            logger.warning(
                "Correcao com item_number %r fora do lote (%s) — descartada",
                number,
                batch_numbers_label(batch),
            )
            continue
        routed[item_id].append(corr)
    return routed

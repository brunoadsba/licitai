"""Orçamento e custo estimado por operação (Fase 7)."""

from __future__ import annotations

from dataclasses import dataclass

from app.utils.metrics import metrics

USD_PER_1K_TOKENS = 0.0002
MAX_COST_USD_PER_OPERATION = 0.50


@dataclass
class CostRecord:
    operation: str
    tokens: int
    usd: float


def estimate_tokens(text: str | None) -> int:
    return max(1, len(text or "") // 4)


def record_operation_cost(operation: str, tokens: int) -> CostRecord:
    usd = (max(0, tokens) / 1000.0) * USD_PER_1K_TOKENS
    if usd > MAX_COST_USD_PER_OPERATION:
        usd = MAX_COST_USD_PER_OPERATION
        metrics.inc("cost_budget_capped")
    metrics.add_cost_usd(usd)
    metrics.inc(f"cost_tokens_{operation}", float(tokens))
    return CostRecord(operation=operation, tokens=tokens, usd=usd)

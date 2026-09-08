"""
Resultado tipado de um agente especializado.

Evita tratar exceção/lista vazia como “seguro” — o orquestrador só faz
early-exit quando a fase 1 concluiu com sucesso e zero achados.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentOutcome(str, Enum):
    OK_EMPTY = "ok_empty"
    FINDINGS = "findings"
    FAILED = "failed"
    PARSE_ERROR = "parse_error"
    SKIPPED = "skipped"


@dataclass(slots=True)
class AgentResult:
    agent_id: str
    outcome: AgentOutcome
    corrections: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.outcome in (AgentOutcome.OK_EMPTY, AgentOutcome.FINDINGS)

    @property
    def has_findings(self) -> bool:
        return self.outcome == AgentOutcome.FINDINGS and bool(self.corrections)

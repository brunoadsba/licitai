"""Regex e constantes do gate de evidências — extraído para caber o G4 canônico."""

from __future__ import annotations

import re

# Qualquer colchete é placeholder ([quantidade], [prazo], [inserir…]).
# Mantém X/Y/Z, {…}, "N meses", "a definir".
PLACEHOLDER_RE = re.compile(
    r"\b[XYZ]\b|\[[^\]]{1,80}\]|\___+"
    r"|\{[^}]+\}|a definir|a preencher|campo a preencher|N\s+meses|[XYZ]/[XYZ]",
    re.IGNORECASE,
)

NUMBER_RE = re.compile(r"\d+[.,]?\d*\s*%?")

OMISSION_RE = re.compile(
    r"n[aã]o\s+(especifica|define|prev[eê]|informa|detalha|apresenta|"
    r"menciona|traz|inclui|cont[eé]m|cita)"
    r"|ausente|omiss[oa]|falta|n[aã]o\s+consta|deixou\s+de"
    r"|sem\s+(prazo|defini|detalha)",
    re.IGNORECASE,
)

OPERATIONAL_RE = re.compile(
    r"reexecutar\s+a\s+an[aá]lise|reanalyze|falha\s+de\s+cobertura"
    r"|cobertura\s+incompleta|erro\s+de\s+processamento",
    re.IGNORECASE,
)

RILC_SIGNALS = re.compile(
    r"RILC|13\.303|estatal|CODEBA|companhia\s+de\s+docas", re.IGNORECASE
)
SIGNALS_14133 = re.compile(
    r"14\.133|preg[aã]o\s+eletr[oô]nico|entes\s+federativos", re.IGNORECASE
)

REGIME_ALLOWLIST: dict[str, set[str]] = {
    "13.303": {"13.303/2016", "13303/2016"},
    "14.133": {"14.133/2021", "14133/2021"},
}
TRANSVERSAL_RE = re.compile(
    r"TCU|AGU|CGU|RILC|s[úu]mula|ac[óo]rd[ãa]o", re.IGNORECASE
)

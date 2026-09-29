"""Resposta fixa sobre o próprio LicitAI.

Os números espelham `frontend/src/lib/confidence.ts` (medição de 28/09/2026).
Não passam pelo modelo: assim a frase não inventa precisão.
"""

from __future__ import annotations

import re

_CONFIABILIDADE_RE = re.compile(
    r"confiabilidade|n[ií]vel de confian[cç]a|qu[aã]o confi[aá]vel",
    re.IGNORECASE,
)
_PRODUTO_RE = re.compile(
    r"precis[aã]o|recall|como (voc[eê]|o licitai) funciona|"
    r"o que (voc[eê]|o licitai) (faz|pode)|limites do (sistema|licitai|copiloto)",
    re.IGNORECASE,
)

PRODUCT_ANSWER = (
    "**Resposta**\n"
    "A precisão do LicitAI ainda não foi medida no golden v2. "
    "O recall em termo de referência real também não está medido neste piloto: "
    "em 28/09/2026 o Postgres do piloto estava com zero análises. "
    "O harness antigo registrou recall 0,25 (3 de 12). "
    "Esse número não é a precisão atual. "
    "O resultado sintético 0,56 do Groq também não vale como precisão de hoje.\n\n"
    "**O que fazer agora**\n"
    "Trate cada correção como hipótese: confira o trecho no TR e o fundamento "
    "antes de aprovar. Os limites completos estão na página Como confiamos.\n\n"
    "**Limites**\n"
    "O recall não é garantido. A cota gratuita pode interromper uma análise "
    "no meio. Documento sigiloso exige modelo local. "
    "Eu não substituo um parecer jurídico."
)


def is_product_question(text: str | None) -> bool:
    """Pergunta sobre o LicitAI, não sobre o TR aberto."""
    if not text:
        return False
    bruto = text.strip()
    if _CONFIABILIDADE_RE.search(bruto):
        return True
    if "licitai" in bruto.lower() and _PRODUTO_RE.search(bruto):
        return True
    return False

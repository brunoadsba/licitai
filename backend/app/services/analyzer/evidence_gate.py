"""
Gate de evidências determinístico (Fase 1 — plano analise-confiavel-2026-09-16).

Supervisor sem LLM: propor × verificar × alinhar com código puro, custo zero,
100% reproduzível. Aplicado entre engine e persistência — achado reprovado é
descartado com motivo logado, nunca persiste como Correction.

Gates:
- G1 trecho existe? original_text com fuzzy-match >= 0.8 no item citado.
- G2 sugestão honesta? sem placeholders e sem números/percentuais ausentes.
- G3 lei do regime? legal_basis restrito à allowlist do regime detectado.
- G4 omissão real? "não especifica X" exige busca doc-wide por X antes.
- OPS falha operacional != achado (antecipação Fase 3): nunca vira Correction.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from app.services.analyzer.grounding import extract_law_and_articles, make_legal_ref

logger = logging.getLogger(__name__)

# Mesmo padrão do revisor-assistente + extensões da crítica afd39876
# (X/Y/Z isolados, "N meses", "a definir", "[...]").
_PLACEHOLDER_RE = re.compile(
    r"\b[XYZ]\b|\[inserir[^\]]*\]|\[preencher[^\]]*\]|\[…\]|\[\.\.\.\]|\___+"
    r"|\{[^}]+\}|a definir|a preencher|campo a preencher|N\s+meses|[XYZ]/[XYZ]",
    re.IGNORECASE,
)

_NUMBER_RE = re.compile(r"\d+[.,]?\d*\s*%?")

_OMISSION_RE = re.compile(
    r"n[aã]o\s+(especifica|define|prev[eê]|informa|detalha|apresenta)"
    r"|ausente|omiss[oa]|falta|n[aã]o\s+consta|sem\s+(prazo|defini|detalha)",
    re.IGNORECASE,
)

_OPERATIONAL_RE = re.compile(
    r"reexecutar\s+a\s+an[aá]lise|reanalyze|falha\s+de\s+cobertura"
    r"|cobertura\s+incompleta|erro\s+de\s+processamento",
    re.IGNORECASE,
)

_RILC_SIGNALS = re.compile(r"RILC|13\.303|estatal|CODEBA|companhia\s+de\s+docas", re.IGNORECASE)
_14133_SIGNALS = re.compile(r"14\.133|preg[aã]o\s+eletr[oô]nico|entes\s+federativos", re.IGNORECASE)

# Allowlist por regime: leis aceitas como fundamento principal.
_REGIME_ALLOWLIST: dict[str, set[str]] = {
    "13.303": {"13.303/2016", "13303/2016"},
    "14.133": {"14.133/2021", "14133/2021"},
}
# Leis transversais sempre aceitas (TCU, AGU, CGU, RILC interno).
_TRANSVERSAL_RE = re.compile(r"TCU|AGU|CGU|RILC|s[úu]mula|ac[óo]rd[ãa]o", re.IGNORECASE)


@dataclass
class GateResult:
    passed: bool
    gate: str  # G1, G2, G3, G4, OPS, OK
    reason: str
    confidence: float = 1.0


def _normalize(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def has_placeholder(text: str | None) -> bool:
    if not text:
        return False
    return bool(_PLACEHOLDER_RE.search(text))


def numbers_in(text: str | None) -> list[str]:
    if not text:
        return []
    return [m.group(0).strip() for m in _NUMBER_RE.finditer(text)]


def detect_regime(doc_text: str | None) -> str | None:
    """Detecta regime pelo documento inteiro. None = ambíguo."""
    if not doc_text:
        return None
    has_rilc = bool(_RILC_SIGNALS.search(doc_text))
    has_14133 = bool(_14133_SIGNALS.search(doc_text or ""))
    if has_rilc and not has_14133:
        return "13.303"
    if has_14133 and not has_rilc:
        return "14.133"
    if has_rilc and has_14133:
        return None  # ambíguo: allowlist união + aviso (ver plano §4)
    return None


def _g1_trecho_existe(original: str, item_content: str) -> GateResult | None:
    if not original or not original.strip():
        # Omissão pura (ex.: item não traz prazo) — G1 não se aplica, G4 decide.
        return None
    norm_orig = _normalize(original)
    norm_item = _normalize(item_content)
    if not norm_orig or not norm_item:
        return GateResult(False, "G1", "item ou trecho vazio após normalização", 0.95)
    if norm_orig in norm_item:
        return None  # passa
    ratio = SequenceMatcher(None, norm_orig, norm_item).ratio()
    # Também testa melhor janela: trecho pode ser subparte com ruído.
    # Se original é longo, compara contra janelas do item para evitar falso-negativo.
    if len(norm_orig) > 60 and len(norm_item) > len(norm_orig):
        best = ratio
        step = max(1, len(norm_orig) // 4)
        for i in range(0, len(norm_item) - len(norm_orig) + 1, step):
            window = norm_item[i : i + len(norm_orig)]
            r = SequenceMatcher(None, norm_orig, window).ratio()
            if r > best:
                best = r
        ratio = best
    if ratio < 0.8:
        return GateResult(
            False,
            "G1",
            f"original_text não encontrado no item (fuzzy {ratio:.2f} < 0.80, possível alucinação)",
            0.95,
        )
    return None


def _g2_sugestao_honesta(suggested: str, original: str, item_content: str, doc_text: str) -> GateResult | None:
    if not suggested or not suggested.strip():
        return GateResult(False, "G2", "suggested_text vazio: sem alteração textual", 0.90)
    if _normalize(suggested) == _normalize(original) and _normalize(suggested):
        return GateResult(False, "G2", "suggested_text idêntico ao original: sem alteração textual", 0.90)
    if has_placeholder(suggested):
        return GateResult(
            False, "G2", "suggested_text com placeholder (X/Y/Z, N meses, a definir)", 0.90
        )
    nums = numbers_in(suggested)
    if not nums:
        return None
    haystack = _normalize(f"{original} {item_content} {doc_text}")
    for n in nums:
        # Normaliza número: "30%" -> "30", "24 meses" -> "24"
        digits = re.sub(r"[^\d.,]", "", n).replace(",", ".")
        digits_norm = digits.strip(" .")
        if not digits_norm:
            continue
        # Busca com boundary para não casar "6" dentro de "67"
        if not re.search(rf"(?<!\d){re.escape(digits_norm)}(?!\d)", haystack):
            return GateResult(
                False,
                "G2",
                f"número '{n}' inventado: ausente no item e no documento",
                0.90,
            )
    return None


def _g3_lei_do_regime(legal_basis: str | None, regime: str | None) -> GateResult | None:
    if not legal_basis or not legal_basis.strip():
        return None  # sem fundamento: revisor decide, gate não barra
    if _TRANSVERSAL_RE.search(legal_basis):
        return None  # TCU/AGU/RILC valem em qualquer regime
    if regime is None:
        return None  # ambíguo: união + aviso, não barra
    law, arts = extract_law_and_articles(legal_basis)
    if not law:
        return None
    allowed = _REGIME_ALLOWLIST.get(regime, set())
    law_norm = law.strip()
    if law_norm in allowed:
        return None
    # Aceita par lei|art alternativo via make_legal_ref quando corpus usa outro formato
    for art in arts:
        if make_legal_ref(law, art) in {make_legal_ref(a, art) for a in allowed}:
            return None
    # Lei de outro regime como fundamento principal -> descarta
    other_regime = "14.133" if regime == "13.303" else "13.303"
    other_laws = _REGIME_ALLOWLIST.get(other_regime, set())
    if law_norm in other_laws:
        return GateResult(
            False,
            "G3",
            f"lei fora do regime ({law_norm} sob contexto {regime}/RILC)",
            0.90,
        )
    return None


def _g4_omissao_real(problem: str, suggested: str, item_content: str, doc_text: str) -> GateResult | None:
    if not _OMISSION_RE.search(problem or ""):
        return None
    # Entidades procuradas: números da sugestão + palavras-chave do problema
    # (prazo, prorrogação, ramais, vigência, garantia...).
    keywords = re.findall(r"[a-zA-Zçãõáéíóúâê]{4,}", _normalize(problem or ""))
    stop = {"para", "este", "esta", "item", "esta", "não", "nao", "que", "dos", "das", "com", "como"}
    keywords = [k for k in keywords if k not in stop][:8]
    norm_doc = _normalize(doc_text or "")
    norm_item = _normalize(item_content or "")
    nums = numbers_in(f"{problem} {suggested}")
    # 1. Número da sugestão existe em outro trecho? -> informação existe.
    for n in nums:
        digits = re.sub(r"[^\d.,]", "", n).replace(",", ".").strip(" .")
        if digits and re.search(rf"(?<!\d){re.escape(digits)}(?!\d)", norm_doc):
            if not re.search(rf"(?<!\d){re.escape(digits)}(?!\d)", norm_item):
                return GateResult(
                    False,
                    "G4",
                    f"omissão desmentida: '{n}' presente em outro trecho do documento",
                    0.85,
                )
    # 2. Palavras-chave da alegação aparecem no doc mas não no item?
    # Ex.: 1.1 "sem prazo" quando 1.4 tem "24 meses" e 11.5 "prorrogação".
    for kw in keywords:
        if kw in norm_doc and kw not in norm_item:
            # Exige ao menos 2 keywords externas para não barrar por coincidência
            others = [k for k in keywords if k in norm_doc and k not in norm_item]
            if len(others) >= 2:
                return GateResult(
                    False,
                    "G4",
                    f"omissão desmentida por busca doc-wide: {', '.join(others[:3])} presente em outro item",
                    0.80,
                )
                break
    return None


def _ops_ruido_operacional(problem: str, legal_basis: str | None, suggested: str) -> GateResult | None:
    if _OPERATIONAL_RE.search(problem or "") and not (legal_basis or "").strip():
        return GateResult(
            False,
            "OPS",
            "falha de cobertura não é achado: vai para banner operacional, nunca Correction",
            0.95,
        )
    return None


def claim_support_rate(
    correction: dict,
    item_content: str,
    doc_text: str = "",
    regime: str | None = None,
) -> dict:
    """Taxa de suporte por afirmação (R3): cada claim verificada isoladamente.

    Claims: trecho existe no item; cada número da sugestão existe no
    item/documento; fundamento não é de regime oposto. Retorna
    {"supported": s, "total": t} para persistir no evidence JSON.
    """
    original = correction.get("original_text", "") or ""
    suggested = correction.get("suggested_text", "") or ""
    legal_basis = correction.get("legal_basis")
    eff_regime = regime or detect_regime(f"{item_content} {doc_text}")
    claims: list[bool] = [
        _g1_trecho_existe(original, item_content or "") is None
        if (original or "").strip() else True,
        _g3_lei_do_regime(legal_basis, eff_regime) is None,
    ]
    haystack = _normalize(f"{original} {item_content} {doc_text}")
    for n in numbers_in(suggested):
        digits = re.sub(r"[^\d.,]", "", n).replace(",", ".").strip(" .")
        if not digits:
            continue
        claims.append(bool(re.search(rf"(?<!\d){re.escape(digits)}(?!\d)", haystack)))
    supported = sum(1 for c in claims if c)
    return {"supported": supported, "total": len(claims)}


def evaluate_finding(
    correction: dict,
    item_content: str,
    doc_text: str = "",
    regime: str | None = None,
    valid_refs: set[str] | None = None,  # reservado p/ G3-corpus (não barra aqui)
) -> GateResult:
    """
    Aplica OPS -> G1 -> G3 -> G2 -> G4 em ordem. Primeiro que reprovar vence.
    G3 antes de G2: número de artigo (ex. art. 6) é julgado como regime,
    não como número inventado.
    Achado reprovado deve ser descartado com motivo logado (auditoria).
    """
    _ = valid_refs  # G3-corpus já coberto por grounding fail-closed; regime é o foco aqui
    original = correction.get("original_text", "") or ""
    suggested = correction.get("suggested_text", "") or ""
    problem = correction.get("problem", "") or ""
    legal_basis = correction.get("legal_basis")

    eff_regime = regime or detect_regime(f"{item_content} {doc_text}")

    for check in (
        _ops_ruido_operacional(problem, legal_basis, suggested),
        _g1_trecho_existe(original, item_content or ""),
        _g3_lei_do_regime(legal_basis, eff_regime),
        _g2_sugestao_honesta(suggested, original, item_content or "", doc_text or ""),
        _g4_omissao_real(problem, suggested, item_content or "", doc_text or ""),
    ):
        if check is not None:
            logger.info("evidence_gate %s: %s", check.gate, check.reason)
            return check
    return GateResult(True, "OK", "evidências verificadas", 1.0)

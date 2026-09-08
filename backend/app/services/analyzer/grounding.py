"""
Validação de grounding anti-alucinação.

- `original_text` deve existir (normalizado) no conteúdo do item.
- `legal_basis` deve casar par (lei + artigo) no corpus, com matching por
  boundary de token (evita `Art. 6` ⊆ `Art. 67`).
- Severidade alta/crítica sem par válido → fail-closed.
"""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import selectinload

# Refs válidas: "lei_norm|artigo_num" (ex.: "14.133/2021|6")
LegalRefSet = set[str]

_HIGH_SEVERITIES = frozenset({"alto", "critico"})
_HIGH_IMPORTANCES = frozenset({"alta", "critica"})

_LAW_RE = re.compile(
    r"(?:lei(?:\s+n[ºo°.]*)?\s*)?(\d{1,2}\.?\d{3}/\d{2,4})",
    re.IGNORECASE,
)
# Captura número do artigo com boundary: não engole dígitos seguintes.
_ART_RE = re.compile(
    r"\bart\.?\s*(\d+)(?!\d)",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_law_number(law: str) -> str:
    """Normaliza número de lei para chave estável (ex.: 14.133/2021)."""
    norm = _normalize(law)
    norm = re.sub(r"^lei\s*(n[ºo°.]*)?\s*", "", norm).strip()
    m = re.search(r"(\d{1,2}\.?\d{3}/\d{2,4})", norm)
    if not m:
        return norm
    raw = m.group(1)
    # Padroniza 14133/2021 → 14.133/2021 quando possível
    digits_year = re.match(r"^(\d+)/(\d{2,4})$", raw.replace(".", ""))
    if digits_year and "." not in raw:
        num, year = digits_year.groups()
        if len(num) == 5:
            raw = f"{num[0:2]}.{num[2:]}/{year}"
        elif len(num) == 4:
            raw = f"{num[0:1]}.{num[1:]}/{year}"
    return raw


def _normalize_article_number(article: str | None) -> str | None:
    """Extrai o número canônico do artigo (`6`, `67`, `19`)."""
    if not article:
        return None
    norm = _normalize(article)
    m = _ART_RE.search(norm)
    if m:
        return m.group(1)
    m2 = re.search(r"(?<!\d)(\d+)(?!\d)", norm)
    return m2.group(1) if m2 else None


def make_legal_ref(law: str, article: str | int) -> str:
    """Monta chave imutável lei|artigo."""
    return f"{_normalize_law_number(law)}|{article}"


def extract_law_and_articles(legal_basis: str) -> tuple[str | None, list[str]]:
    """Extrai lei e lista de artigos citados em um fundamento."""
    if not legal_basis or not legal_basis.strip():
        return None, []
    law_m = _LAW_RE.search(legal_basis)
    law = _normalize_law_number(law_m.group(0)) if law_m else None
    arts = [m.group(1) for m in _ART_RE.finditer(legal_basis)]
    # Dedup preservando ordem
    seen: set[str] = set()
    unique_arts: list[str] = []
    for a in arts:
        if a not in seen:
            seen.add(a)
            unique_arts.append(a)
    return law, unique_arts


def article_token_matches(article_num: str, text: str) -> bool:
    """True se o número do artigo aparece com boundary (não como prefixo)."""
    if not article_num or not text:
        return False
    pattern = rf"(?<!\d)art\.?\s*{re.escape(str(article_num))}(?!\d)"
    return bool(re.search(pattern, _normalize(text), re.IGNORECASE))


def is_original_text_grounded(original_text: str, item_content: str) -> bool:
    if not original_text or not original_text.strip():
        return False
    if not item_content:
        return False
    norm_original = _normalize(original_text)
    norm_content = _normalize(item_content)
    if not norm_original:
        return False
    return norm_original in norm_content


async def get_valid_legal_refs(db) -> LegalRefSet:
    """
    Carrega pares (lei, artigo) existentes no corpus.

    Retorna conjunto de chaves `lei_norm|artigo_num`. Falhas de schema
    devolvem conjunto vazio (validação fica neutra via `None`).
    """
    try:
        from app.models.legal import LegalChunk, LegalDocument

        refs: LegalRefSet = set()
        result = await db.execute(
            select(LegalChunk)
            .options(selectinload(LegalChunk.legal_document))
            .join(LegalDocument)
        )
        chunks = result.scalars().all()
        for chunk in chunks:
            doc = chunk.legal_document
            if not doc or not doc.law_number:
                continue
            art_num = _normalize_article_number(chunk.article)
            if not art_num:
                continue
            refs.add(make_legal_ref(doc.law_number, art_num))
        return refs
    except OperationalError:
        return set()
    except Exception:
        return set()


def is_legal_basis_valid(
    legal_basis: str | None,
    valid_refs: LegalRefSet | set[str],
) -> bool | None:
    """
    Valida se o fundamento cita um par lei+artigo presente no corpus.

    Retornos:
    - `None`: sem fundamento ou corpus vazio (não dá para afirmar).
    - `True`: pelo menos um par (lei, artigo) bate com boundary.
    - `False`: fundamento presente mas sem par válido no corpus.

    Aceita refs no formato `lei|art` (preferido) ou legado flat
    (`lei 14.133/2021`, `art. 6`) — neste caso exige lei E artigo
    com matching por boundary no texto do fundamento.
    """
    if not legal_basis or not legal_basis.strip():
        return None
    if not valid_refs:
        return None

    law, arts = extract_law_and_articles(legal_basis)
    pair_refs = {r for r in valid_refs if isinstance(r, str) and "|" in r}
    flat_refs = {_normalize(r) for r in valid_refs if isinstance(r, str) and "|" not in r}

    if pair_refs:
        if not law or not arts:
            return False
        for art in arts:
            if make_legal_ref(law, art) in pair_refs:
                return True
        return False

    # Legado: refs flat — exige lei no conjunto E artigo com boundary.
    if not flat_refs:
        return False

    law_ok = False
    if law:
        law_norm = _normalize_law_number(law)
        for ref in flat_refs:
            ref_law = _normalize_law_number(ref)
            if ref_law == law_norm or law_norm in ref or ref in _normalize(legal_basis):
                # Evita aceitar só porque "14" aparece em outro lugar
                if re.search(rf"(?<!\d){re.escape(law_norm)}(?!\d)", _normalize(legal_basis)):
                    law_ok = True
                    break
                if ref_law == law_norm:
                    law_ok = True
                    break

    art_ok = False
    for art in arts:
        # Artigo no corpus flat: "art. 6" deve casar com boundary no fundamento
        for ref in flat_refs:
            ref_art = _normalize_article_number(ref)
            if ref_art and ref_art == art and article_token_matches(art, legal_basis):
                art_ok = True
                break
        if art_ok:
            break

    if law and arts:
        return bool(law_ok and art_ok)
    if law and not arts:
        # Só lei, sem artigo: não valida como fundamento completo
        return False
    return False


def is_high_severity_finding(
    severity: str | None = None,
    importance: str | None = None,
) -> bool:
    sev = (severity or "").lower()
    imp = (importance or "").lower()
    return sev in _HIGH_SEVERITIES or imp in _HIGH_IMPORTANCES


def should_fail_closed_legal(
    legal_valid: bool | None,
    *,
    severity: str | None = None,
    importance: str | None = None,
) -> bool:
    """True quando fundamento inválido em achado de severidade alta/crítica."""
    return legal_valid is False and is_high_severity_finding(severity, importance)

import re
import unicodedata
from sqlalchemy import select
from sqlalchemy.exc import OperationalError


def _normalize(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


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


async def get_valid_legal_refs(db) -> set[str]:
    try:
        from app.models.legal import LegalChunk, LegalDocument

        refs: set[str] = set()
        docs = (await db.execute(select(LegalDocument.law_number))).scalars().all()
        for law in docs:
            if law:
                refs.add(_normalize(law))
        chunks = (await db.execute(select(LegalChunk.article))).scalars().all()
        for art in chunks:
            if art:
                refs.add(_normalize(art))
                refs.add(_normalize(art.replace("Art.", "").replace("art.", "").strip()))
        return refs
    except OperationalError:
        return set()
    except Exception:
        return set()


def is_legal_basis_valid(legal_basis: str | None, valid_refs: set[str]) -> bool | None:
    if not legal_basis or not legal_basis.strip():
        return None
    if not valid_refs:
        return None
    norm_basis = _normalize(legal_basis)
    for ref in valid_refs:
        if ref and ref in norm_basis:
            return True
    law_pattern = re.search(r"\d+\.\d+/\d{4}", legal_basis)
    if law_pattern and _normalize(law_pattern.group(0)) in valid_refs:
        return True
    return False

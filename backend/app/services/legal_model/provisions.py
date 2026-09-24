"""Parser hierárquico: artigo → parágrafo → inciso → alínea → item."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.ingest.hashing import sha256_text
from app.services.parser.legal_marks import normalize_legal_text

_ARTICLE_RE = re.compile(r"^(?:Art\.|Artigo)\s*(\d+[º°\-A-Za-z]*)", re.IGNORECASE)
_PARA_RE = re.compile(
    r"^(?:§\s*(\d+[º°]?)|Parágrafo\s+único)\b",
    re.IGNORECASE,
)
_INCISO_RE = re.compile(r"^([IVXLCDM]+)\s*[-–—.)]")
_ALINEA_RE = re.compile(r"^([a-z])\)")
_ITEM_RE = re.compile(r"^(\d+)\s*[-–—.)]")


@dataclass
class ProvisionDraft:
    path: str
    parent_path: str | None
    article: str | None
    paragraph: str | None
    inciso: str | None
    alinea: str | None
    item: str | None
    canonical_text: str
    status: str
    provision_hash: str


def _norm_art(raw: str) -> str:
    cleaned = raw.replace("º", "").replace("°", "").rstrip(".")
    return cleaned.lower()


def _norm_para(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    return digits or raw.lower()


def _vetado_drafts(content: str) -> list[ProvisionDraft]:
    """Artigos só (VETADO) viram dispositivo histórico, não vigente."""
    from app.services.parser.legal_marks import normalize_legal_text as _norm

    drafts: list[ProvisionDraft] = []
    for mark in _norm(content).marks:
        if mark.kind != "vetado":
            continue
        match = _ARTICLE_RE.search(mark.text)
        if not match:
            continue
        art = match.group(1)
        path = f"art.{_norm_art(art)}"
        drafts.append(
            ProvisionDraft(
                path=path,
                parent_path=None,
                article=f"Art. {art}",
                paragraph=None,
                inciso=None,
                alinea=None,
                item=None,
                canonical_text=mark.text,
                status="vetado",
                provision_hash=sha256_text(mark.text),
            )
        )
    return drafts


def parse_provisions(content: str) -> list[ProvisionDraft]:
    """Extrai dispositivos do texto vigente, com caminho e ancestral."""
    vigente = normalize_legal_text(content).vigente
    drafts: list[ProvisionDraft] = []
    article = paragraph = inciso = alinea = item = None
    buffers: dict[str, list[str]] = {}

    def _path() -> str | None:
        if not article:
            return None
        parts = [f"art.{_norm_art(article)}"]
        if paragraph:
            parts.append(f"par.{_norm_para(paragraph)}")
        if inciso:
            parts.append(f"inc.{inciso}")
        if alinea:
            parts.append(f"ali.{alinea}")
        if item:
            parts.append(f"item.{item}")
        return "/".join(parts)

    def _parent(path: str) -> str | None:
        if "/" not in path:
            return None
        return path.rsplit("/", 1)[0]

    def _flush(path: str | None) -> None:
        if not path or path not in buffers:
            return
        text = "\n".join(buffers.pop(path)).strip()
        if not text:
            return
        for draft in drafts:
            if draft.path == path:
                merged = f"{draft.canonical_text}\n{text}".strip()
                draft.canonical_text = merged
                draft.provision_hash = sha256_text(merged)
                return
        drafts.append(
            ProvisionDraft(
                path=path,
                parent_path=_parent(path),
                article=f"Art. {article}" if article else None,
                paragraph=paragraph,
                inciso=inciso,
                alinea=alinea,
                item=item,
                canonical_text=text,
                status="vigente",
                provision_hash=sha256_text(text),
            )
        )

    current: str | None = None
    for raw in vigente.splitlines():
        line = raw.strip()
        if not line:
            continue
        art = _ARTICLE_RE.match(line)
        if art:
            _flush(current)
            article = art.group(1)
            paragraph = inciso = alinea = item = None
            current = _path()
            buffers[current] = [line]
            continue
        if not article:
            continue
        para = _PARA_RE.match(line)
        if para:
            _flush(current)
            inciso = alinea = item = None
            paragraph = "unico" if para.group(1) is None else para.group(1)
            current = _path()
            buffers[current] = [line]
            continue
        inc = _INCISO_RE.match(line)
        if inc and article:
            _flush(current)
            alinea = item = None
            inciso = inc.group(1)
            current = _path()
            buffers[current] = [line]
            continue
        ali = _ALINEA_RE.match(line)
        if ali and inciso:
            _flush(current)
            item = None
            alinea = ali.group(1)
            current = _path()
            buffers[current] = [line]
            continue
        itm = _ITEM_RE.match(line)
        if itm and alinea:
            _flush(current)
            item = itm.group(1)
            current = _path()
            buffers[current] = [line]
            continue
        if current:
            buffers.setdefault(current, []).append(line)

    _flush(current)
    seen = {d.path for d in drafts}
    for extra in _vetado_drafts(content):
        if extra.path not in seen:
            drafts.append(extra)
            seen.add(extra.path)
    return drafts

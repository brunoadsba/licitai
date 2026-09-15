"""
Parser de documentos ODT (OpenDocument Text).

Segurança:
- XML parsing com defusedxml (XXE / entity expansion mitigation)
- Limite de tamanho do content.xml descompactado
- Sem execução de macros
"""

import logging
import zipfile
from pathlib import Path

from defusedxml import ElementTree

logger = logging.getLogger(__name__)

TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"

# Limite de content.xml descompactado (zip bomb / DoS)
MAX_CONTENT_XML_BYTES = 50 * 1024 * 1024
MAX_ODT_ENTRIES = 5000
MAX_ODT_TOTAL_BYTES = 200 * 1024 * 1024


def _clean_ns(tag: str) -> str:
    return tag.split("}")[1] if "}" in tag else tag


def parse_odt(file_path: Path) -> tuple[str, list[dict]]:
    """
    Extrai texto de um ODT.

    O ODT é um ZIP contendo content.xml com o texto no formato ODF.

    Returns:
        Tuple (texto_completo, lista_de_páginas)
        ODT não tem conceito nativo de páginas, retorna página única.
    """
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            names = zf.namelist()
            if len(names) > MAX_ODT_ENTRIES:
                raise ValueError("Arquivo ODT com entries demais (possível zip bomb).")
            if any(n.startswith("/") or ".." in n for n in names):
                raise ValueError("Arquivo ODT com caminhos inválidos.")
            total = sum(zf.getinfo(n).file_size for n in names)
            if total > MAX_ODT_TOTAL_BYTES:
                raise ValueError("Arquivo ODT descompactado excede o limite total.")
            if "content.xml" not in names:
                raise ValueError("Arquivo ODT inválido: content.xml não encontrado.")
            info = zf.getinfo("content.xml")
            if info.file_size > MAX_CONTENT_XML_BYTES:
                raise ValueError(
                    f"content.xml descompactado excede o limite de "
                    f"{MAX_CONTENT_XML_BYTES // (1024 * 1024)} MB."
                )
            xml_content = zf.read("content.xml")
            if len(xml_content) > MAX_CONTENT_XML_BYTES:
                raise ValueError(
                    f"content.xml descompactado excede o limite de "
                    f"{MAX_CONTENT_XML_BYTES // (1024 * 1024)} MB."
                )
    except zipfile.BadZipFile as e:
        logger.exception("Erro ao abrir ODT: %s", file_path.name)
        raise ValueError("Não foi possível abrir o arquivo ODT. Verifique o formato.") from e

    root = ElementTree.fromstring(xml_content)

    text_parts = []

    for elem in root.iter():
        tag = _clean_ns(elem.tag)

        if tag == "p":
            text = "".join(elem.itertext()).strip()
            if text:
                text_parts.append(text)

        elif tag == "h":
            text = "".join(elem.itertext()).strip()
            if text:
                text_parts.append(f"[TÍTULO] {text}")

    # Tabelas
    for table in root.iter(f"{{{TABLE_NS}}}table"):
        rows = []
        for row in table.iter(f"{{{TABLE_NS}}}table-row"):
            cells = []
            for cell in row.iter(f"{{{TABLE_NS}}}table-cell"):
                cell_text = "".join(cell.itertext()).strip()
                cells.append(cell_text)
            if any(cells):
                rows.append(" | ".join(cells))
        if rows:
            text_parts.append("[TABELA]")
            text_parts.extend(rows)
            text_parts.append("[/TABELA]")

    full_text = "\n".join(text_parts)
    pages = [{"page": 1, "text": full_text}] if full_text.strip() else []

    if not full_text.strip():
        raise ValueError("Nenhum texto pôde ser extraído do ODT.")

    return full_text, pages

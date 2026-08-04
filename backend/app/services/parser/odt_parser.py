"""
Parser de documentos ODT (OpenDocument Text).

Segurança:
- XML parsing com entidades externas desabilitadas (XXE prevention)
- Sem execução de macros
"""

import logging
import zipfile
from pathlib import Path
from xml.etree import ElementTree

logger = logging.getLogger(__name__)

TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"

_clean_ns = lambda tag: tag.split("}")[1] if "}" in tag else tag


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
            if "content.xml" not in zf.namelist():
                raise ValueError("Arquivo ODT inválido: content.xml não encontrado.")
            xml_content = zf.read("content.xml")
    except zipfile.BadZipFile:
        logger.exception("Erro ao abrir ODT: %s", file_path.name)
        raise ValueError("Não foi possível abrir o arquivo ODT. Verifique o formato.")

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
        table_rows = []
        for row in table.iter(f"{{{TABLE_NS}}}table-row"):
            cells = []
            for cell in row.iter(f"{{{TABLE_NS}}}table-cell"):
                cell_text = "".join(cell.itertext()).strip()
                cells.append(cell_text)
            if any(c.strip() for c in cells):
                table_rows.append(" | ".join(cells))

        if table_rows:
            text_parts.append("[TABELA]")
            text_parts.extend(table_rows)
            text_parts.append("[/TABELA]")

    full_text = "\n".join(text_parts)

    if not full_text.strip():
        raise ValueError(
            "Nenhum texto pôde ser extraído do ODT. "
            "Verifique se o arquivo não está vazio ou corrompido."
        )

    pages = [{"page": 1, "text": full_text}]

    return full_text, pages

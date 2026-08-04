"""
Baixa e extrai o texto integral das leis do Planalto.

Gera arquivos .txt em backend/data/laws para serem ingeridos
pelo pipeline RAG. Usa apenas a stdlib (html.parser), sem
dependências externas.

Uso:
    python scripts/download_laws.py
"""

import html
import logging
import re
from html.parser import HTMLParser
from pathlib import Path

import urllib.request

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "backend" / "data" / "laws"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LAWS = [
    {
        "slug": "lei-14133-2021",
        "title": "Lei 14.133/2021",
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm",
    },
    {
        "slug": "lei-13303-2016",
        "title": "Lei 13.303/2016",
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2016/lei/l13303.htm",
    },
]


class TextExtractor(HTMLParser):
    """Extrai texto limpo de páginas HTML do Planalto."""

    def __init__(self):
        super().__init__()
        self._blocks: list[str] = []
        self._in_paragraph = False
        self._skip_depth = 0
        self._buffer: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in ("p", "div", "br", "h1", "h2", "h3", "h4"):
            self._flush()
        if tag in ("p", "h1", "h2", "h3", "h4"):
            self._in_paragraph = True

    def handle_endtag(self, tag):
        if tag in ("style", "script") and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in ("p", "h1", "h2", "h3", "h4"):
            self._flush()
            self._in_paragraph = False

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._in_paragraph or data.strip():
            self._buffer.append(data)

    def _flush(self):
        text = "".join(self._buffer)
        text = html.unescape(text)
        text = " ".join(text.split())
        if text:
            self._blocks.append(text)
        self._buffer = []

    def text(self) -> str:
        self._flush()
        return "\n".join(self._blocks)


def _detect_charset(raw_bytes: bytes, content_type: str) -> str:
    """Detecta o charset da resposta HTML (meta > header > latin-1)."""
    head = raw_bytes[:4096].decode("ascii", errors="ignore").lower()
    match = re.search(r'charset=["\']?([\w-]+)', head)
    if match:
        return match.group(1)

    for part in content_type.split(";")[1:]:
        if "charset" in part:
            return part.split("=")[1].strip().strip('"')

    return "latin-1"


def download(url: str) -> str:
    """Baixa a página HTML e extrai o texto limpo."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; LicitAI/1.0)"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        raw_bytes = response.read()

    # Detectar charset: meta tag no HTML > Content-Type > fallback latin-1
    charset = _detect_charset(raw_bytes, response.headers.get("Content-Type", ""))
    raw = raw_bytes.decode(charset, errors="replace")

    parser = TextExtractor()
    parser.feed(raw)
    return parser.text()


def main() -> None:
    for law in LAWS:
        out_path = DATA_DIR / f"{law['slug']}.txt"
        try:
            logger.info("Baixando %s ...", law["title"])
            text = download(law["url"])
            out_path.write_text(text, encoding="utf-8")
            logger.info(
                "Salvo %s (%d caracteres)", out_path.name, len(text)
            )
        except Exception:
            logger.exception("Falha ao baixar %s", law["title"])


if __name__ == "__main__":
    main()

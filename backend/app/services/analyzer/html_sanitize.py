"""Sanitiza HTML antes de ir ao editor do SEI.

Remove script, iframe, handlers e atributos. Mantém marcações de TR
(h1–h6, p, br, listas, tabelas, ênfase).
"""

from __future__ import annotations

from html.parser import HTMLParser

_ALLOWED = frozenset(
    {
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "br",
        "strong",
        "b",
        "em",
        "i",
        "u",
        "ul",
        "ol",
        "li",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "blockquote",
        "div",
        "span",
    }
)
_VOID = frozenset({"br"})


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._out: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _ALLOWED:
            return
        if tag in _VOID:
            self._out.append(f"<{tag}>")
            return
        self._out.append(f"<{tag}>")

    def handle_endtag(self, tag: str) -> None:
        if tag in _ALLOWED and tag not in _VOID:
            self._out.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self._out.append(
            data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

    def result(self) -> str:
        return "".join(self._out)


def sanitize_html(raw: str | None) -> str:
    """Devolve HTML sem script, eventos ou atributos."""
    if not raw:
        return ""
    parser = _Sanitizer()
    parser.feed(raw)
    parser.close()
    return parser.result()

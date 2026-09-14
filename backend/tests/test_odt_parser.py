"""Testes básicos do parser ODT (limite de tamanho / XML seguro)."""

import zipfile
from pathlib import Path

import pytest

from app.services.parser.odt_parser import MAX_CONTENT_XML_BYTES, parse_odt


def _write_minimal_odt(path: Path, xml: str) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("content.xml", xml)


def test_parse_odt_extrai_paragrafo(tmp_path: Path):
    xml = (
        '<?xml version="1.0"?>'
        '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
        "<office:body><office:text>"
        "<text:p>Objeto da contratação de serviços.</text:p>"
        "</office:text></office:body>"
        "</office:document-content>"
    )
    odt = tmp_path / "ok.odt"
    _write_minimal_odt(odt, xml)
    text, pages = parse_odt(odt)
    assert "Objeto da contratação" in text
    assert pages[0]["page"] == 1


def test_parse_odt_rejeita_content_xml_gigante(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.services.parser.odt_parser.MAX_CONTENT_XML_BYTES",
        64,
    )
    xml = "<?xml version='1.0'?><root>" + ("x" * 200) + "</root>"
    odt = tmp_path / "big.odt"
    _write_minimal_odt(odt, xml)
    with pytest.raises(ValueError, match="excede o limite"):
        parse_odt(odt)


def test_max_content_constant():
    assert MAX_CONTENT_XML_BYTES == 50 * 1024 * 1024

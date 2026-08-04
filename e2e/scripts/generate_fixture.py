from pathlib import Path
import zipfile


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "sample-tr.docx"

CONTENT = [
    ("1", "OBJETO", "O presente termo tem por objeto a contratação de serviços de limpeza predial."),
    (
        "2",
        "JUSTIFICATIVA",
        "A contratação é necessária para atender demanda institucional sem fundamentação legal adequada.",
    ),
    ("3", "PRAZO", "O prazo de execução será de 12 meses, contados da assinatura do contrato."),
]


def _xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _build_document_xml() -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
        "<w:body>",
    ]
    parts.append(
        "<w:p><w:pPr><w:pStyle w:val=\"Title\"/></w:pPr>"
        "<w:r><w:t>Termo de Referência — Teste E2E</w:t></w:r></w:p>"
    )
    for number, title, content in CONTENT:
        parts.append(
            f"<w:p><w:pPr><w:pStyle w:val=\"Heading2\"/></w:pPr>"
            f"<w:r><w:t>{_xml_escape(number)}. {_xml_escape(title)}</w:t></w:r></w:p>"
        )
        parts.append(
            f"<w:p><w:r><w:t>{_xml_escape(content)}</w:t></w:r></w:p>"
        )
    parts.append("</w:body></w:document>")
    return "\n".join(parts)


def generate() -> Path:
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)

    doc_xml = _build_document_xml()

    with zipfile.ZipFile(FIXTURE_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/word/document.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                "</Types>"
            ),
        )
        z.writestr(
            "_rels/.rels",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="word/document.xml"/>'
                "</Relationships>"
            ),
        )
        z.writestr("word/document.xml", doc_xml)
        z.writestr(
            "word/_rels/document.xml.rels",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
            ),
        )

    return FIXTURE_PATH


if __name__ == "__main__":
    path = generate()
    print(f"Fixture gerada: {path}")

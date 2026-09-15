"""Anonimização de e-mails nos TRs de Emergência (modo seguro por padrão).

Uso:
  python3 backend/scripts/anonymize_emergencia.py --dry-run   # só lista, não escreve nada
  ANONYMIZE_CONFIRM=1 python3 ... --apply                     # exige ok explícito + faz backup

Nunca envia nada para cloud; contagens passam pelo mascaramento (só números no log).
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import sys

EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE = re.compile(r"\(\d{2}\)\s?\d{4,5}[-\s]?\d{4}|\b\d{2}\s\d{4,5}[-\s]\d{4}\b")
TARGETS = sorted(
    glob.glob("fixtures/trs-codeba/objetos/06-base-emergencia-operacional/*.pdf")
    + (
        ["fixtures/trs-codeba/piloto-unico/06-base-emergencia-operacional.pdf"]
        if os.path.exists("fixtures/trs-codeba/piloto-unico/06-base-emergencia-operacional.pdf")
        else []
    )
)


def scan(pdf: str) -> tuple[int, int]:
    import fitz

    doc = fitz.open(pdf)
    ne = nt = 0
    for p in doc:
        t = p.get_text()
        ne += len(EMAIL.findall(t))
        nt += len(PHONE.findall(t))
    doc.close()
    return ne, nt


def redact_file(pdf: str) -> tuple[int, int]:
    """Substitui e-mails por [email] e telefones por [telefone]. Retorna (n_email, n_tel)."""
    import fitz

    doc = fitz.open(pdf)
    ne = nt = 0
    for page in doc:
        for w in page.get_text("words"):
            if "@" in w[4] and EMAIL.fullmatch(w[4]):
                page.add_redact_annot(fitz.Rect(w[:4]), text="[email]")
                ne += 1
        for m in PHONE.findall(page.get_text()):
            for r in page.search_for(m):
                page.add_redact_annot(r, text="[telefone]")
                nt += 1
                break
        page.apply_redactions(images=False, graphics=False)
    if ne or nt:
        tmp = pdf + ".redacted.tmp"
        doc.save(tmp, garbage=4, deflate=True)
        doc.close()
        os.replace(tmp, pdf)
    else:
        doc.close()
    return ne, nt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if args.apply:
        if os.getenv("ANONYMIZE_CONFIRM") != "1":
            print("recusado: exige ANONYMIZE_CONFIRM=1 (ok explícito do Bruno) + backup")
            return 2
        for pdf in TARGETS:
            ne, nt = redact_file(pdf)
            print(f"[apply] {pdf}: {ne} e-mail(s) + {nt} telefone(s) tarjado(s)")
        print("concluído; originais em backups/anonymize-emergencia-2026-09-15/")
        return 0

    te = tt = 0
    for pdf in TARGETS:
        ne, nt = scan(pdf)
        te += ne
        tt += nt
        print(f"[dry-run] {pdf}: trocaria {ne} e-mail(s) + {nt} telefone(s)")
    print(f"[dry-run] total: {te} e-mail(s) + {tt} telefone(s) em {len(TARGETS)} arquivos (nada foi alterado)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

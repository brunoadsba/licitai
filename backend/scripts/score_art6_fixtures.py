#!/usr/bin/env python3
"""Score Art. 6º (cobertura a–j) nos PDFs de fixtures/trs-codeba — sem LLM.

Uso:
  PYTHONPATH=backend python backend/scripts/score_art6_fixtures.py
  PYTHONPATH=backend python backend/scripts/score_art6_fixtures.py --dir fixtures/trs-codeba/piloto-unico
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.generator.validator import (  # noqa: E402
    ART6_COVERAGE_TARGET,
    art6_coverage_ratio,
    validate_tr_completeness,
)


def _extract_text(pdf: Path) -> str:
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("PyMuPDF (fitz) necessário") from exc
    doc = fitz.open(pdf)
    text = "\n".join(page.get_text() or "" for page in doc)
    doc.close()
    return text


def _secoes_from_text(text: str) -> list[dict]:
    """Heurística: títulos Art. 6 / numeração SEI → seções para o validador."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    art6_title = re.compile(
        r"(?i)\b("
        r"defini[cç][aã]o do objeto|do objeto|da fundamenta|"
        r"descri[cç][aã]o da solu[cç][aã]o|solu[cç][aã]o como um todo|"
        r"requisitos da contrata|"
        r"modelo de execu[cç][aã]o|modelo de gest[aã]o|"
        r"crit[eé]rios de medi[cç][aã]o|medi[cç][aã]o e.*?pagamento|"
        r"sele[cç][aã]o do fornecedor|crit[eé]rio de julgamento|"
        r"estimativas? do valor|estimativa de pre[cç]o|"
        r"adequa[cç][aã]o or[cç]ament"
        r")\b"
    )
    heading_re = re.compile(
        r"^(\d{1,2}(?:\.\d+)*\.?)\s+(.{8,160})$"
    )
    secoes: list[dict] = []
    current: dict | None = None

    def start(num: str, title: str) -> None:
        nonlocal current
        if current:
            secoes.append(current)
        current = {"item_number": num, "title": title, "content": ""}

    for ln in lines:
        if art6_title.search(ln) and len(ln) < 180:
            m = heading_re.match(ln)
            start(m.group(1) if m else str(len(secoes) + 1), ln)
            continue
        m = heading_re.match(ln)
        if m and not re.match(r"^\d{1,2}\.\d{2}\.\d{4}", ln):
            # só inicia seção numerada se parecer título (poucas palavras / MAIÚSCULAS)
            title = m.group(2)
            if title.isupper() or art6_title.search(title) or len(title.split()) <= 12:
                start(m.group(1), title)
                continue
        if current:
            current["content"] += ln + "\n"
    if current:
        secoes.append(current)

    if len(secoes) < 3:
        # último recurso: janelas por keyword no texto integral
        low = text.lower()
        for i, (key, needles) in enumerate(
            [
                ("objeto", ["do objeto", "definição do objeto", "1. do objeto"]),
                ("fundamentacao", ["fundamentação", "justificativa"]),
                ("descricao_solucao", ["solução como um todo", "ciclo de vida"]),
                ("requisitos", ["requisitos da contratação", "especificações"]),
                ("modelo_execucao", ["modelo de execução", "execução do objeto"]),
                ("modelo_gestao", ["modelo de gestão", "fiscalização"]),
                ("medicao", ["medição", "pagamento"]),
                ("selecao", ["seleção do fornecedor", "critério de julgamento"]),
                ("estimativa", ["estimativa", "valor da contratação"]),
                ("orcamentaria", ["adequação orçamentária", "dotação"]),
            ]
        ):
            for n in needles:
                idx = low.find(n)
                if idx >= 0:
                    snippet = text[max(0, idx - 40) : idx + 400]
                    secoes.append(
                        {
                            "item_number": f"{i + 1}.0",
                            "title": n.upper(),
                            "content": snippet,
                        }
                    )
                    break
    return secoes or [{"item_number": "1.0", "title": "DOCUMENTO", "content": text[:8000]}]


def main() -> int:
    parser = argparse.ArgumentParser(description="Score Art.6 coverage em PDFs locais")
    parser.add_argument(
        "--dir",
        type=Path,
        default=ROOT / "fixtures" / "trs-codeba" / "piloto-unico",
    )
    args = parser.parse_args()
    pdfs = sorted(args.dir.glob("*.pdf"))
    if not pdfs:
        print(f"Nenhum PDF em {args.dir}")
        return 1

    print(f"Alvo cobertura estrutural: ≥{ART6_COVERAGE_TARGET:.0%}")
    print(f"Fonte: {args.dir}\n")
    rows = []
    for pdf in pdfs:
        text = _extract_text(pdf)
        secoes = _secoes_from_text(text)
        cov = art6_coverage_ratio(secoes)
        miss = validate_tr_completeness(secoes)
        rows.append((pdf.name, cov, miss, len(secoes)))
        flag = "OK" if cov >= ART6_COVERAGE_TARGET else "GAP"
        print(f"[{flag}] {cov:.0%}  secoes={len(secoes):2d}  faltantes={miss or '-'}  {pdf.name}")

    mean = sum(r[1] for r in rows) / len(rows)
    ok_n = sum(1 for r in rows if r[1] >= ART6_COVERAGE_TARGET)
    print(f"\nMédia piloto: {mean:.0%} · ≥90%: {ok_n}/{len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
Geração de relatórios em Markdown.

Gera relatório formatado a partir dos dados de análise.
"""

import logging
from datetime import datetime

from app.schemas.analysis import ReportResponse


logger = logging.getLogger(__name__)

# Mapeamento de labels para português
CATEGORY_LABELS = {
    "juridica": "Jurídica",
    "tecnica": "Técnica",
    "redacao": "Redação",
    "estrutural": "Estrutural",
}

SEVERITY_LABELS = {
    "info": "ℹ️ Informativo",
    "baixo": "🟢 Baixo",
    "medio": "🟡 Médio",
    "alto": "🟠 Alto",
    "critico": "🔴 Crítico",
}

RISK_LABELS = {
    "baixo": "🟢 Baixo",
    "medio": "🟡 Médio",
    "alto": "🟠 Alto",
    "critico": "🔴 Crítico",
}


def generate_markdown_report(report: ReportResponse) -> str:
    """Gera relatório completo em Markdown."""
    lines = []

    # Cabeçalho
    lines.append("# Relatório de Análise — Termo de Referência")
    lines.append("")
    lines.append(f"**Documento:** {report.document_name}")
    lines.append(f"**Data da Análise:** {_format_date(report.analyzed_at)}")
    lines.append(f"**Status:** {report.status}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Pontuação
    lines.append("## 📊 Pontuação Geral")
    lines.append("")
    lines.append("| Dimensão | Nota |")
    lines.append("|----------|------|")
    for score in report.scores:
        nota = f"{score.score:.1f}/10" if score.score is not None else "N/A"
        lines.append(f"| {score.label} | {nota} |")
    lines.append("")

    # Risco
    if report.risk_level:
        risk_label = RISK_LABELS.get(report.risk_level, report.risk_level)
        lines.append(f"**Risco de Impugnação:** {risk_label}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Resumo de correções
    lines.append("## 📋 Resumo")
    lines.append("")
    lines.append(f"**Total de correções:** {report.total_corrections}")
    lines.append("")

    if report.corrections_by_category:
        lines.append("### Por Categoria")
        lines.append("")
        for cat, count in report.corrections_by_category.items():
            label = CATEGORY_LABELS.get(cat, cat)
            lines.append(f"- **{label}:** {count}")
        lines.append("")

    if report.corrections_by_severity:
        lines.append("### Por Severidade")
        lines.append("")
        for sev, count in report.corrections_by_severity.items():
            label = SEVERITY_LABELS.get(sev, sev)
            lines.append(f"- {label}: {count}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Correções detalhadas
    lines.append("## 🔍 Correções Detalhadas")
    lines.append("")

    if not report.corrections:
        lines.append("*Nenhuma correção identificada. O documento está adequado.*")
    else:
        for i, correction in enumerate(report.corrections, 1):
            cat_label = CATEGORY_LABELS.get(correction.category, correction.category)
            sev_label = SEVERITY_LABELS.get(correction.severity, correction.severity)

            lines.append(f"### Correção {i} — {cat_label} ({sev_label})")
            lines.append("")
            lines.append(f"**Situação:** {correction.situation}")
            lines.append("")
            lines.append(f"**Problema:** {correction.problem}")
            lines.append("")
            lines.append(f"**Risco:** {correction.risk}")
            lines.append("")

            lines.append("**DE (texto original):**")
            lines.append(f"> {correction.original_text}")
            lines.append("")

            lines.append("**PARA (texto sugerido):**")
            lines.append(f"> {correction.suggested_text}")
            lines.append("")

            lines.append(f"**Justificativa:** {correction.justification}")
            lines.append("")

            if correction.legal_basis:
                lines.append(f"**Fundamento Legal:** {correction.legal_basis}")
                lines.append("")

            lines.append("---")
            lines.append("")

    # Parecer final
    if report.final_opinion:
        lines.append("## 📝 Parecer Final")
        lines.append("")
        lines.append(report.final_opinion)
        lines.append("")

    # Rodapé
    lines.append("---")
    lines.append("")
    lines.append("*Relatório gerado automaticamente pelo Sistema de Análise de Termos de Referência.*")
    lines.append(f"*Gerado em: {_format_date(report.analyzed_at)}*")

    return "\n".join(lines)


def _format_date(dt: datetime | None) -> str:
    """Formata data para exibição."""
    if dt is None:
        return "N/A"
    return dt.strftime("%d/%m/%Y às %H:%M")

"""
Motor de análise de documentos.

Orquestra a análise item a item usando LLM:
1. Carrega documento e seus itens do banco
2. Para cada item, monta prompt e envia ao LLM
3. Parseia resposta estruturada (JSON)
4. Salva correções no banco
5. Gera pontuação consolidada via LLM
"""

import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentItem
from app.models.analysis import Analysis, Correction
from app.services.llm import get_llm_provider
from app.services.analyzer.prompts import (
    SYSTEM_PROMPT,
    ITEM_ANALYSIS_PROMPT,
    SCORING_PROMPT,
)


logger = logging.getLogger(__name__)


async def run_analysis(
    db: AsyncSession,
    analysis_id,
    document_id,
) -> None:
    """
    Executa análise completa de um documento.

    Esta função roda em background e atualiza o status no banco
    conforme progride.
    """
    # Carregar análise
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        logger.error("Análise %s não encontrada", analysis_id)
        return

    # Carregar documento com itens
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.items))
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        analysis.status = "error"
        analysis.error_message = "Documento não encontrado."
        await db.flush()
        return

    # Iniciar análise
    analysis.status = "running"
    analysis.started_at = datetime.now(timezone.utc)
    analysis.total_items = len(document.items)
    await db.flush()

    # Obter provedor LLM
    try:
        llm = get_llm_provider()
    except ValueError as e:
        analysis.status = "error"
        analysis.error_message = str(e)
        await db.flush()
        return

    all_corrections = []

    # Analisar cada item
    for idx, item in enumerate(document.items):
        try:
            corrections = await _analyze_item(llm, item)

            for correction_data in corrections:
                correction = Correction(
                    analysis_id=analysis.id,
                    document_item_id=item.id,
                    category=correction_data.get("category", "tecnica"),
                    severity=correction_data.get("severity", "medio"),
                    situation=correction_data.get("situation", ""),
                    problem=correction_data.get("problem", ""),
                    risk=correction_data.get("risk", ""),
                    original_text=correction_data.get("original_text", ""),
                    suggested_text=correction_data.get("suggested_text", ""),
                    justification=correction_data.get("justification", ""),
                    legal_basis=correction_data.get("legal_basis"),
                    importance=correction_data.get("importance", "media"),
                )
                db.add(correction)
                all_corrections.append(correction_data)

            analysis.analyzed_items = idx + 1
            await db.flush()

            logger.info(
                "Item %d/%d analisado: %s — %d correções",
                idx + 1,
                len(document.items),
                item.item_number,
                len(corrections),
            )

        except Exception:
            logger.exception(
                "Erro ao analisar item %s do documento %s",
                item.item_number,
                document_id,
            )
            # Continuar com os próximos itens

    # Gerar pontuação consolidada
    try:
        scores = await _generate_scores(llm, all_corrections, len(document.items))

        analysis.score_overall = scores.get("score_overall")
        analysis.score_juridical = scores.get("score_juridical")
        analysis.score_technical = scores.get("score_technical")
        analysis.score_writing = scores.get("score_writing")
        analysis.score_structural = scores.get("score_structural")
        analysis.risk_level = scores.get("risk_level", "medio")
        analysis.final_opinion = scores.get("final_opinion", "")

    except Exception:
        logger.exception("Erro ao gerar pontuação para análise %s", analysis_id)
        # Análise concluída mesmo sem pontuação
        analysis.final_opinion = (
            f"Análise concluída com {len(all_corrections)} correções identificadas. "
            "Pontuação automática não disponível."
        )

    # Finalizar
    analysis.status = "completed"
    analysis.completed_at = datetime.now(timezone.utc)

    # Atualizar status do documento
    document.status = "completed"

    await db.flush()

    logger.info(
        "Análise %s concluída: %d itens, %d correções, nota %.1f",
        analysis_id,
        len(document.items),
        len(all_corrections),
        float(analysis.score_overall) if analysis.score_overall else 0,
    )


async def _analyze_item(llm, item: DocumentItem) -> list[dict]:
    """Analisa um item individual usando o LLM."""
    user_prompt = ITEM_ANALYSIS_PROMPT.format(
        item_number=item.item_number,
        item_title=item.title or "(sem título)",
        page_number=item.page_number or "N/A",
        item_content=item.content[:8000],  # Limitar tamanho do conteúdo
    )

    response = await llm.generate(SYSTEM_PROMPT, user_prompt)

    # Parsear resposta JSON
    corrections = _parse_json_response(response)

    # Validar e limpar cada correção
    valid_corrections = []
    for c in corrections:
        if _validate_correction(c):
            valid_corrections.append(_sanitize_correction(c))

    return valid_corrections


async def _generate_scores(
    llm, corrections: list[dict], total_items: int
) -> dict:
    """Gera pontuação consolidada via LLM."""
    # Resumir correções para o prompt
    summary_parts = []
    for i, c in enumerate(corrections[:50], 1):  # Limitar a 50 correções
        summary_parts.append(
            f"{i}. [{c.get('category', '?')}] [{c.get('severity', '?')}] "
            f"{c.get('problem', 'N/A')[:100]}"
        )

    corrections_summary = "\n".join(summary_parts) if summary_parts else "Nenhuma correção identificada."

    user_prompt = SCORING_PROMPT.format(
        corrections_summary=corrections_summary,
        total_items=total_items,
        total_corrections=len(corrections),
    )

    response = await llm.generate(SYSTEM_PROMPT, user_prompt)
    scores = _parse_json_response(response)

    # Se retornou lista, pegar primeiro item
    if isinstance(scores, list) and scores:
        scores = scores[0]

    if not isinstance(scores, dict):
        raise ValueError("Resposta de pontuação não é um JSON válido.")

    return scores


def _parse_json_response(response: str) -> list[dict] | dict:
    """
    Extrai e parseia JSON da resposta do LLM.
    Lida com respostas que podem conter texto extra.
    """
    # Tentar parsear diretamente
    try:
        parsed = json.loads(response)
        return parsed
    except json.JSONDecodeError:
        pass

    # Tentar extrair JSON de blocos de código
    json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", response)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Tentar encontrar array ou object JSON no texto
    for pattern in [r"\[[\s\S]*\]", r"\{[\s\S]*\}"]:
        match = re.search(pattern, response)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue

    logger.warning("Não foi possível parsear JSON da resposta do LLM")
    return []


# Valores válidos para campos de correção
VALID_CATEGORIES = {"juridica", "tecnica", "redacao", "estrutural"}
VALID_SEVERITIES = {"info", "baixo", "medio", "alto", "critico"}
VALID_IMPORTANCES = {"baixa", "media", "alta", "critica"}


def _validate_correction(correction: dict) -> bool:
    """Valida se uma correção tem os campos obrigatórios."""
    required = ["category", "problem", "original_text", "suggested_text"]
    return all(correction.get(field) for field in required)


def _sanitize_correction(correction: dict) -> dict:
    """Limpa e normaliza valores de uma correção."""
    category = correction.get("category", "tecnica").lower()
    if category not in VALID_CATEGORIES:
        category = "tecnica"

    severity = correction.get("severity", "medio").lower()
    if severity not in VALID_SEVERITIES:
        severity = "medio"

    importance = correction.get("importance", "media").lower()
    if importance not in VALID_IMPORTANCES:
        importance = "media"

    return {
        "category": category,
        "severity": severity,
        "situation": str(correction.get("situation", ""))[:2000],
        "problem": str(correction.get("problem", ""))[:2000],
        "risk": str(correction.get("risk", ""))[:2000],
        "original_text": str(correction.get("original_text", ""))[:5000],
        "suggested_text": str(correction.get("suggested_text", ""))[:5000],
        "justification": str(correction.get("justification", ""))[:2000],
        "legal_basis": str(correction.get("legal_basis", ""))[:500] or None,
        "importance": importance,
    }

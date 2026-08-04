"""
Motor de análise de documentos.

Orquestra a análise item a item usando LLM:
1. Carrega documento e seus itens do banco
2. Para cada item, monta prompt e envia ao LLM
3. Parseia resposta estruturada (JSON)
4. Salva correções no banco
5. Gera pontuação consolidada via LLM
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentItem
from app.models.analysis import Analysis, Correction
from app.services.llm import get_llm_provider
from app.services.rag.retriever import retrieve
from app.services.analyzer.prompts import (
    SYSTEM_PROMPT,
    ITEM_ANALYSIS_PROMPT,
    SCORING_PROMPT,
)
from app.services.analyzer.json_utils import (
    parse_json_response,
    validate_correction,
    sanitize_correction,
)
from app.services.analyzer.review import (
    review_item_corrections,
    apply_review_decisions,
)
from app.services.agents.orchestrator import MultiAgentOrchestrator


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
    await db.commit()

    # Obter provedor LLM
    try:
        llm = get_llm_provider()
    except ValueError as e:
        analysis.status = "error"
        analysis.error_message = str(e)
        await db.flush()
        return

    all_corrections = []
    analyzed_count = 0
    pending_reviews = []
    orchestrator = MultiAgentOrchestrator() if getattr(analysis, "analysis_mode", "multi_agent") == "multi_agent" else None

    # Analisar cada item
    for idx, item in enumerate(document.items):
        try:
            legal_context = await _retrieve_legal_context(db, item)
            if orchestrator:
                corrections = await orchestrator.analyze_item_multi(llm, item, legal_context)
            else:
                corrections = await _analyze_item(db, llm, item, legal_context)

            correction_objs = []
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
                    agent_origin=correction_data.get("agent_origin"),
                )
                db.add(correction)
                correction_objs.append(correction)
                all_corrections.append(correction_data)

            pending_reviews.append((item, legal_context, correction_objs))

            analyzed_count += 1
            analysis.analyzed_items = analyzed_count
            await db.commit()

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

    # Se nenhum item foi analisado, os provedores LLM estão indisponíveis:
    # marcar como erro em vez de reportar sucesso falso.
    if analyzed_count == 0:
        analysis.status = "error"
        analysis.completed_at = datetime.now(timezone.utc)
        analysis.error_message = (
            "Nenhum item pôde ser analisado: todos os provedores LLM "
            "falharam (verifique quota/limites das chaves Gemini e Groq)."
        )
        await db.flush()
        logger.error(
            "Análise %s marcada como erro: nenhum item analisado "
            "(provedores LLM indisponíveis)",
            analysis_id,
        )
        return

    # Fase 2.2: revisão cruzada das correções (após análise completa)
    all_corrections = await _run_cross_review(db, llm, pending_reviews)

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

        if not analysis.score_overall:
            raise ValueError("Score zerado ou ausente")

    except Exception:
        logger.exception("Erro ao gerar pontuação via LLM para análise %s; aplicando cálculo determinístico de fallback", analysis_id)
        scores = _calculate_fallback_scores(all_corrections, len(document.items))
        analysis.score_overall = scores["score_overall"]
        analysis.score_juridical = scores["score_juridical"]
        analysis.score_technical = scores["score_technical"]
        analysis.score_writing = scores["score_writing"]
        analysis.score_structural = scores["score_structural"]
        analysis.risk_level = scores["risk_level"]
        analysis.final_opinion = scores["final_opinion"]

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


async def _analyze_item(
    db: AsyncSession, llm, item: DocumentItem, legal_context: str | None = None
) -> list[dict]:
    """Analisa um item individual usando o LLM, com contexto jurídico."""
    if legal_context is None:
        legal_context = await _retrieve_legal_context(db, item)
    return await analyze_item_llm(llm, item, legal_context)


async def analyze_item_llm(llm, item, legal_context: str) -> list[dict]:
    """Analisa um item via LLM usando contexto jurídico fornecido (sem DB).

    Usada pelo engine (com contexto do RAG) e pelo benchmark (com contexto fixo).
    """
    user_prompt = ITEM_ANALYSIS_PROMPT.format(
        item_number=item.item_number,
        item_title=item.title or "(sem título)",
        page_number=item.page_number or "N/A",
        item_content=item.content[:8000],  # Limitar tamanho do conteúdo
        legal_context=legal_context,
    )

    response = await llm.generate(SYSTEM_PROMPT, user_prompt)

    # Parsear resposta JSON
    corrections = parse_json_response(response)

    # Validar e limpar cada correção
    valid_corrections = []
    for c in corrections:
        if isinstance(c, dict) and validate_correction(c):
            valid_corrections.append(sanitize_correction(c))

    return valid_corrections


async def _run_cross_review(
    db: AsyncSession,
    llm,
    pending_reviews: list[tuple[DocumentItem, str, list[Correction]]],
) -> list[dict]:
    """Revisa as correções de cada item e devolve o conjunto final válido."""
    kept: list[dict] = []

    for item, legal_context, correction_objs in pending_reviews:
        if not correction_objs:
            continue

        try:
            corrections_dict = [
                _correction_to_dict(obj) for obj in correction_objs
            ]
            decisions = await review_item_corrections(
                llm, item, corrections_dict, legal_context
            )
            kept.extend(apply_review_decisions(correction_objs, decisions))
        except Exception:
            logger.exception(
                "Falha na revisão cruzada do item %s", item.item_number
            )
            # Sem revisão: mantém as correções como estão
            for obj in correction_objs:
                obj.review_status = "pendente"
            kept.extend(_correction_to_dict(obj) for obj in correction_objs)

    await db.flush()
    logger.info("Revisão cruzada concluída: %d correções válidas", len(kept))
    return kept


def _correction_to_dict(obj: Correction) -> dict:
    """Converte um objeto Correction em dict (para pontuação)."""
    return {
        "category": obj.category,
        "severity": obj.severity,
        "situation": obj.situation,
        "problem": obj.problem,
        "risk": obj.risk,
        "original_text": obj.original_text,
        "suggested_text": obj.suggested_text,
        "justification": obj.justification,
        "legal_basis": obj.legal_basis,
        "importance": obj.importance,
    }


async def _retrieve_legal_context(db: AsyncSession, item: DocumentItem) -> str:
    """Busca artigos relevantes no corpus jurídico e formata para o prompt."""
    try:
        chunks = await retrieve(
            db,
            query=f"{item.title or ''} {item.content}",
            top_k=4,
        )
    except Exception:
        logger.exception("Falha ao recuperar contexto jurídico")
        return ""

    if not chunks:
        return ""

    parts = []
    for c in chunks:
        parts.append(
            f"### {c.law_number} — {c.article}\n{c.text[:2500]}"
        )
    return "\n\n".join(parts)


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
    scores = parse_json_response(response)

    # Se retornou lista, pegar primeiro item
    if isinstance(scores, list) and scores:
        scores = scores[0]

    if not isinstance(scores, dict):
        raise ValueError("Resposta de pontuação não é um JSON válido.")

    return scores


def _calculate_fallback_scores(corrections: list[dict], total_items: int) -> dict:
    """Calcula pontuação e parecer de forma determinística caso a LLM falhe na sumarização final."""
    cat_penalties = {"juridica": 0.0, "tecnica": 0.0, "redacao": 0.0, "estrutural": 0.0}
    has_critical = False
    has_high = False

    sev_weights = {"critico": 2.5, "alto": 1.5, "medio": 0.7, "baixo": 0.2}

    for c in corrections:
        cat = c.get("category", "tecnica")
        sev = c.get("severity", "medio")
        weight = sev_weights.get(sev, 0.7)
        if cat in cat_penalties:
            cat_penalties[cat] += weight
        if sev == "critico":
            has_critical = True
        elif sev == "alto":
            has_high = True

    score_juridical = round(max(0.0, min(10.0, 10.0 - cat_penalties["juridica"])), 1)
    score_technical = round(max(0.0, min(10.0, 10.0 - cat_penalties["tecnica"])), 1)
    score_writing = round(max(0.0, min(10.0, 10.0 - cat_penalties["redacao"])), 1)
    score_structural = round(max(0.0, min(10.0, 10.0 - cat_penalties["estrutural"])), 1)

    score_overall = round(
        (score_juridical * 0.35 + score_technical * 0.30 + score_structural * 0.20 + score_writing * 0.15), 1
    )

    if has_critical or score_overall < 5.0:
        risk_level = "critico"
    elif has_high or score_overall < 7.0:
        risk_level = "alto"
    elif score_overall < 8.5:
        risk_level = "medio"
    else:
        risk_level = "baixo"

    final_opinion = (
        f"Análise concluída com {len(corrections)} apontamento(s) de atenção formulados pelos 4 agentes especialistas. "
        f"Pontuação consolidada do Termo de Referência: {score_overall}/10. Nível de Risco Global: {risk_level.upper()}."
    )

    return {
        "score_overall": score_overall,
        "score_juridical": score_juridical,
        "score_technical": score_technical,
        "score_writing": score_writing,
        "score_structural": score_structural,
        "risk_level": risk_level,
        "final_opinion": final_opinion,
    }

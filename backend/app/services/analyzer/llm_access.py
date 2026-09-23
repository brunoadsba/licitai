"""Aquisição do LLM da análise conforme a classificação do documento."""

from datetime import datetime, timezone

from app.services.agents.legal_agent import LegalAgent
from app.services.agents.orchestrator import MultiAgentOrchestrator
from app.services.agents.structural_agent import StructuralAgent
from app.services.llm.factory import get_llm_provider_for
from app.services.privacy import PrivacyPolicyError, resolve_policy


def build_orchestrator(mode: str) -> MultiAgentOrchestrator | None:
    if mode == "economic":
        return MultiAgentOrchestrator([LegalAgent(), StructuralAgent()])
    if mode == "multi_agent":
        return MultiAgentOrchestrator()
    return None


def calls_per_item(mode: str) -> int:
    if mode == "economic":
        return 2
    if mode == "single":
        return 1
    return 4


async def acquire_analysis_llm(db, analysis, document, document_id):
    """Devolve (llm, policy). None se o provedor não sobe.

    PrivacyPolicyError é gravada na análise e relançada (job sem retry).
    """
    policy = resolve_policy(getattr(document, "classification", None))
    try:
        llm = get_llm_provider_for(policy, document_id=str(document_id))
    except PrivacyPolicyError as exc:
        analysis.status = "error"
        analysis.error_message = str(exc)
        analysis.llm_provider = "blocked"
        analysis.completed_at = datetime.now(timezone.utc)
        await db.commit()
        raise
    except (ValueError, RuntimeError) as exc:
        analysis.status = "error"
        analysis.error_message = str(exc)
        await db.flush()
        return None, None

    provider_name = getattr(llm, "provider_name", None) or analysis.llm_provider
    analysis.llm_provider = str(provider_name)[:20]
    analysis.status = "running"
    analysis.started_at = datetime.now(timezone.utc)
    analysis.total_items = len(document.items)
    await db.commit()
    return llm, policy

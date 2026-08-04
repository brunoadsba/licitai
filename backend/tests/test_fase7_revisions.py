"""
Testes unitários e de integração para a Fase 7.

Testa o histórico e versionamento de edições de documentos (single-user)
e a presença do checklist estrito no Agente Estrutural.
"""

import pytest
from app.services.agents.structural_agent import StructuralAgent


def test_structural_agent_system_prompt_contains_strict_checklist():
    agent = StructuralAgent()
    prompt = agent.system_prompt
    assert "CHECKLIST ESTRITO DE COMPLETUDE" in prompt
    assert "Art. 6º, XXIII" in prompt
    assert "Sensibilidade a Omissões" in prompt


def test_structural_agent_build_user_prompt():
    class ItemMock:
        item_number = "2.1"
        title = "Do Objeto"
        page_number = 3
        content = "O objeto consiste em contratação de serviços."

    agent = StructuralAgent()
    user_prompt = agent.build_user_prompt(ItemMock(), legal_context="Lei 14.133/21")

    assert "2.1" in user_prompt
    assert "Do Objeto" in user_prompt
    assert "Lei 14.133/21" in user_prompt

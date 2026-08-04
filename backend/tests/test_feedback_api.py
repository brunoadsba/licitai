"""
Testes de integração do endpoint POST /comparison/{id}/feedback (RF04).

Cobre os guards (404/400), a montagem da resposta e a semântica de falha
parcial, usando banco SQLite em memória e `enviar_email` mockado (sem SMTP
real). Os UUIDs passam pelo fluxo real do banco (verifica a consistência da
conversão para string usada no agrupamento por fornecedor).
"""

import asyncio
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.comparison import (
    Comparacao,
    ComparacaoResultado,
    Fornecedor,
    Molde,
)
from app.models.document import Document


CONFIG_MOLDE = json.dumps({
    "versao": 1,
    "regras": [
        {"id": "r1", "rotulo": "Vigência mínima", "tipo": "numero_inteiro"},
        {"id": "r2", "rotulo": "Garantia", "tipo": "booleano"},
    ],
})


async def _montar_cenario(
    status: str = "completed",
) -> tuple[async_sessionmaker, dict]:
    """Cria banco em memória, popula e devolve sessionmaker + ids."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        molde = Molde(nome="Molde Teste", config_json=CONFIG_MOLDE)
        tr = Document(
            filename_original="TR Limpeza.pdf",
            filename_stored="tr-limpeza.pdf",
            file_type="pdf",
            file_size_bytes=1000,
            document_type="tr",
            status="completed",
        )
        session.add_all([molde, tr])
        await session.commit()
        await session.refresh(molde)
        await session.refresh(tr)

        fornecedores = {
            "com_email": Fornecedor(nome="Alpha", email="alpha@exemplo.com"),
            "com_email2": Fornecedor(nome="Beta", email="beta@exemplo.com"),
            "sem_email": Fornecedor(nome="Gama"),
            "sem_pendencia": Fornecedor(nome="Delta"),
        }
        session.add_all(fornecedores.values())
        await session.commit()
        for f in fornecedores.values():
            await session.refresh(f)

        comparacao = Comparacao(
            tr_document_id=tr.id,
            molde_id=molde.id,
            status=status,
        )
        session.add(comparacao)
        await session.commit()
        await session.refresh(comparacao)

        resultados = [
            # Alpha: 1 falha → deve receber e-mail
            ComparacaoResultado(
                comparacao_id=comparacao.id,
                fornecedor_id=fornecedores["com_email"].id,
                regra_id="r1",
                status="falha",
                motivo="Valor diverge.",
                valor_tr="90",
                valor_proposta="60",
            ),
            # Beta: 1 atencao → deve receber e-mail
            ComparacaoResultado(
                comparacao_id=comparacao.id,
                fornecedor_id=fornecedores["com_email2"].id,
                regra_id="r2",
                status="atencao",
                motivo="Item não confirmado.",
                valor_tr=None,
                valor_proposta=None,
            ),
            # Gama: sem e-mail, com pendência → entra em sem_email
            ComparacaoResultado(
                comparacao_id=comparacao.id,
                fornecedor_id=fornecedores["sem_email"].id,
                regra_id="r1",
                status="falha",
                motivo="Valor diverge.",
                valor_tr="90",
                valor_proposta="30",
            ),
            # Delta: sem pendência → entra em sem_pendencias
            ComparacaoResultado(
                comparacao_id=comparacao.id,
                fornecedor_id=fornecedores["sem_pendencia"].id,
                regra_id="r1",
                status="ok",
                motivo="Confere.",
                valor_tr="90",
                valor_proposta="90",
            ),
        ]
        session.add_all(resultados)
        await session.commit()

        ids = {
            "comparacao": comparacao.id,
            "fornecedores": {k: v.id for k, v in fornecedores.items()},
        }

    return Session, ids


def _run(coroutine):
    return asyncio.run(coroutine)


async def _post_feedback(Session, comparacao_id: uuid.UUID) -> dict:
    """Sobe a app com override de get_db e dispara o endpoint."""
    async def override_get_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                f"/api/v1/comparison/{comparacao_id}/feedback"
            )
            return {
                "status": response.status_code,
                "body": response.json() if response.content else {},
            }
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_feedback_404_comparacao_inexistente():
    async def _cenario():
        Session, _ids = await _montar_cenario()
        return await _post_feedback(Session, uuid.uuid4())

    resultado = _run(_cenario())
    assert resultado["status"] == 404


def test_feedback_400_comparacao_nao_concluida():
    async def _cenario():
        Session, ids = await _montar_cenario(status="pending")
        return await _post_feedback(Session, ids["comparacao"])

    resultado = _run(_cenario())
    assert resultado["status"] == 400
    assert "não concluída" in resultado["body"]["detail"]


def test_feedback_400_smtp_ausente(monkeypatch):
    monkeypatch.setattr("app.api.comparison.smtp_configurado", lambda: False)

    async def _cenario():
        Session, ids = await _montar_cenario()
        return await _post_feedback(Session, ids["comparacao"])

    resultado = _run(_cenario())
    assert resultado["status"] == 400
    assert "SMTP" in resultado["body"]["detail"]


def test_feedback_envia_apenas_com_email_e_pendencia(monkeypatch):
    chamadas = []

    async def fake_enviar_email(to: str, subject: str, body: str):
        chamadas.append({"to": to, "subject": subject, "body": body})

    monkeypatch.setattr("app.api.comparison.smtp_configurado", lambda: True)
    monkeypatch.setattr("app.api.comparison.enviar_email", fake_enviar_email)

    async def _cenario():
        Session, ids = await _montar_cenario()
        return await _post_feedback(Session, ids["comparacao"])

    resultado = _run(_cenario())

    assert resultado["status"] == 200
    body = resultado["body"]
    assert body["enviados"] == 2
    assert body["falhas"] == []
    assert sorted(body["fornecedores_sem_pendencias"]) == ["Delta"]
    assert sorted(body["fornecedores_sem_email"]) == ["Gama"]

    destinatarios = {c["to"] for c in chamadas}
    assert destinatarios == {"alpha@exemplo.com", "beta@exemplo.com"}
    for c in chamadas:
        assert "TR Limpeza" in c["subject"]
        assert "Vigência mínima" in c["body"] or "Garantia" in c["body"]


def test_feedback_falha_parcial_nao_quebra_lote(monkeypatch):
    async def fake_enviar_email(to: str, subject: str, body: str):
        raise ConnectionError("Servidor SMTP recusou conexão")

    monkeypatch.setattr("app.api.comparison.smtp_configurado", lambda: True)
    monkeypatch.setattr("app.api.comparison.enviar_email", fake_enviar_email)

    async def _cenario():
        Session, ids = await _montar_cenario()
        return await _post_feedback(Session, ids["comparacao"])

    resultado = _run(_cenario())

    assert resultado["status"] == 200
    body = resultado["body"]
    assert body["enviados"] == 0
    assert len(body["falhas"]) == 2
    nomes = {f["nome"] for f in body["falhas"]}
    assert nomes == {"Alpha", "Beta"}
    for f in body["falhas"]:
        assert "SMTP" in f["motivo"] or "recusou" in f["motivo"]

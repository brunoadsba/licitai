"""
Regressão de integridade referencial e concorrência:

- C3: PRAGMA foreign_keys=ON → delete de documento cascata em comparações/resultados
- C2: restore_revision restaura fielmente o snapshot (add/update/remove) com backup pré-restauro
- I2: unique (document_id, versao) em document_revisions
- I4: índice parcial único impede duas análises ativas por documento
"""

import asyncio
import uuid

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.analysis import Analysis
from app.models.comparison import Comparacao, ComparacaoResultado, Fornecedor, Molde
from app.models.document import Document, DocumentItem
from app.schemas.document import DocumentRevisionCreate


def _make_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _fk_on(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


async def _criar_doc_com_itens(session, itens):
    doc = Document(
        filename_original="TR.pdf",
        filename_stored=f"{uuid.uuid4()}.pdf",
        file_type="pdf",
        file_size_bytes=100,
        document_type="tr",
        status="parsed",
        total_items=len(itens),
    )
    session.add(doc)
    await session.flush()
    for order, (numero, titulo, conteudo) in enumerate(itens):
        session.add(DocumentItem(
            document_id=doc.id,
            item_number=numero,
            title=titulo,
            content=conteudo,
            page_number=1,
            item_order=order,
            item_type="item",
        ))
    await session.flush()
    return doc


def test_delete_documento_cascateia_comparacoes_e_resultados():
    async def scenario():
        engine = _make_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            fornecedor = Fornecedor(nome="Fornecedor X")
            molde = Molde(nome="Molde", config_json='{"versao": 1, "regras": []}')
            doc = Document(
                filename_original="tr.pdf",
                filename_stored=f"{uuid.uuid4()}.pdf",
                file_type="pdf",
                file_size_bytes=10,
                document_type="tr",
                status="parsed",
            )
            session.add_all([fornecedor, molde, doc])
            await session.flush()

            comparacao = Comparacao(
                tr_document_id=doc.id, molde_id=molde.id, status="completed"
            )
            session.add(comparacao)
            await session.flush()
            session.add(ComparacaoResultado(
                comparacao_id=comparacao.id,
                fornecedor_id=fornecedor.id,
                regra_id="regra_1",
                status="ok",
            ))
            await session.commit()

            await session.delete(doc)
            await session.commit()

            n_cmp = (
                await session.execute(select(func.count()).select_from(Comparacao))
            ).scalar_one()
            n_res = (
                await session.execute(
                    select(func.count()).select_from(ComparacaoResultado)
                )
            ).scalar_one()
            return n_cmp, n_res

    n_cmp, n_res = asyncio.run(scenario())
    assert n_cmp == 0
    assert n_res == 0


def test_restore_revision_restaura_fielmente_snapshot():
    async def scenario():
        from app.api.revisions import create_revision, restore_revision

        engine = _make_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            doc = await _criar_doc_com_itens(session, [
                ("1", "Objeto", "Conteúdo original do objeto."),
                ("2", "Prazo", "Prazo original de 12 meses."),
            ])
            doc_id = doc.id

            await create_revision(
                doc_id, DocumentRevisionCreate(rotulo="v1"), session
            )

            items = {i.item_number: i for i in (await session.execute(
                select(DocumentItem).where(DocumentItem.document_id == doc_id)
            )).scalars()}
            items["1"].content = "Conteúdo EDITADO."
            await session.delete(items["2"])
            session.add(DocumentItem(
                document_id=doc_id,
                item_number="3",
                title="Novo",
                content="Item adicionado após o snapshot.",
                page_number=9,
                item_order=99,
                item_type="item",
            ))
            await session.commit()

            # expire_all simula novo request: sem isso doc.items ficaria obsoleto
            # no identity map da sessão compartilhada (expire_on_commit=False).
            session.expire_all()

            resposta = await restore_revision(doc_id, 1, session)

            finais = (await session.execute(
                select(DocumentItem)
                .where(DocumentItem.document_id == doc_id)
                .order_by(DocumentItem.item_order)
            )).scalars().all()
            return resposta, finais

    resposta, finais = asyncio.run(scenario())

    numeros = [i.item_number for i in finais]
    assert numeros == ["1", "2"]
    por_numero = {i.item_number: i for i in finais}
    assert por_numero["1"].content == "Conteúdo original do objeto."
    assert por_numero["2"].content == "Prazo original de 12 meses."
    assert resposta["versao_backup"] == 2
    assert "restaurado" in resposta["message"].lower()


def test_restore_revision_404_para_versao_inexistente():
    from fastapi import HTTPException

    async def scenario():
        from app.api.revisions import restore_revision

        engine = _make_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            doc = await _criar_doc_com_itens(session, [("1", "T", "C")])
            with pytest.raises(HTTPException) as exc_info:
                await restore_revision(doc.id, 42, session)
            return exc_info

    exc_info = asyncio.run(scenario())
    assert exc_info.value.status_code == 404


def test_revisoes_duplicadas_mesma_versao_sao_rejeitadas():
    async def scenario():
        engine = _make_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            doc = await _criar_doc_com_itens(session, [("1", "T", "C")])
            from app.models.document_revision import DocumentRevision

            session.add(DocumentRevision(
                document_id=doc.id, versao=1, rotulo="primeira",
                items_snapshot=[],
            ))
            await session.commit()

            session.add(DocumentRevision(
                document_id=doc.id, versao=1, rotulo="duplicada",
                items_snapshot=[],
            ))
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return "rejeitada"
            return "aceita"

    assert asyncio.run(scenario()) == "rejeitada"


def test_analises_ativas_duplicadas_sao_rejeitadas_e_liberadas_apos_conclusao():
    async def scenario():
        engine = _make_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            doc = await _criar_doc_com_itens(session, [])
            analise_a = Analysis(
                document_id=doc.id, status="pending",
                llm_provider="fake", llm_model="fake",
            )
            session.add(analise_a)
            await session.commit()

            duplicada = Analysis(
                document_id=doc.id, status="pending",
                llm_provider="fake", llm_model="fake",
            )
            session.add(duplicada)
            try:
                await session.flush()
                await session.commit()
                segunda = "aceita"
            except IntegrityError:
                await session.rollback()
                segunda = "rejeitada"

            if segunda == "rejeitada":
                analise_a.status = "completed"
                await session.commit()

                session.add(duplicada)
                try:
                    await session.flush()
                    await session.commit()
                    terceira = "aceita"
                except IntegrityError:
                    await session.rollback()
                    terceira = "rejeitada"
                return segunda, terceira
            return segunda, None

    segunda, terceira = asyncio.run(scenario())
    assert segunda == "rejeitada"
    assert terceira == "aceita"

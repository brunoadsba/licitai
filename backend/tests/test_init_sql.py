"""
Validação do db/init.sql (D1/D4).

Usa o pglast (parser oficial do PostgreSQL — libpg_query) para garantir que o
script de inicialização seja sintaticamente válido em Postgres, e verifica o
contrato de schema: tipos, colunas novas, constraints e ausência de índices
sobre embedding (embedding é TEXT, não vector).

Isso substitui a necessidade de subir um container Postgres para validar a
sintaxe; execução real em banco continua possível via docker compose.
"""

from pathlib import Path

import pytest

pglast = pytest.importorskip("pglast")

INIT_SQL_PATH = Path(__file__).resolve().parents[2] / "db" / "init.sql"


def _statements():
    return pglast.parse_sql(INIT_SQL_PATH.read_text(encoding="utf-8"))


def _create_table_statements():
    tables = {}
    for node in _statements():
        if type(node.stmt).__name__ != "CreateStmt":
            continue
        tables[node.stmt.relation.relname] = node.stmt
    return tables


def _column_types(create_stmt) -> dict[str, str]:
    types = {}
    for elt in create_stmt.tableElts:
        if type(elt).__name__ != "ColumnDef":
            continue
        types[elt.colname] = elt.typeName.names[-1].sval
    return types


def _has_check_constraint(create_stmt, text: str) -> bool:
    for elt in create_stmt.tableElts:
        if type(elt).__name__ != "ColumnDef":
            continue
        for constraint in getattr(elt, "constraints", ()) or ():
            if type(constraint).__name__ != "Constraint":
                continue
            if constraint.contype != pglast.enums.ConstrType.CONSTR_CHECK:
                continue
            if constraint.raw_expr is not None and text in str(constraint.raw_expr):
                return True
    return False


class TestInitSqlSyntax:
    def test_arquivo_existe(self):
        assert INIT_SQL_PATH.exists()

    def test_parse_sintaticamente_valido(self):
        stmts = _statements()
        assert len(stmts) >= 30

    def test_extensao_vector_declarada(self):
        raw = INIT_SQL_PATH.read_text(encoding="utf-8")
        assert "CREATE EXTENSION IF NOT EXISTS vector;" in raw

    def test_sem_indice_ivfflat_sobre_embedding(self):
        raw = INIT_SQL_PATH.read_text(encoding="utf-8")
        assert "ivfflat" not in raw.lower()


class TestInitSqlContract:
    def test_document_items_fechamento_sintatico(self):
        raw = INIT_SQL_PATH.read_text(encoding="utf-8")
        start = raw.index("CREATE TABLE IF NOT EXISTS document_items")
        end = raw.index("CREATE TABLE IF NOT EXISTS document_revisions")
        block = raw[start:end]
        assert ");" in block

    def test_document_revisions_items_snapshot_json(self):
        tables = _create_table_statements()
        assert "document_revisions" in tables
        types = _column_types(tables["document_revisions"])
        assert types["items_snapshot"] == "json"

    def test_analyses_analysis_mode(self):
        tables = _create_table_statements()
        assert "analyses" in tables
        types = _column_types(tables["analyses"])
        assert types.get("analysis_mode") == "varchar"
        raw = INIT_SQL_PATH.read_text(encoding="utf-8")
        assert "analysis_mode VARCHAR(20) NOT NULL DEFAULT 'multi_agent'" in raw

    def test_corrections_agent_origin(self):
        tables = _create_table_statements()
        assert "corrections" in tables
        types = _column_types(tables["corrections"])
        assert types.get("agent_origin") == "varchar"

    def test_legal_chunks_embedding_text(self):
        tables = _create_table_statements()
        assert "legal_chunks" in tables
        types = _column_types(tables["legal_chunks"])
        assert types["embedding"] == "text"

    def test_comparacao_resultados_unico_fornecedor_regra(self):
        raw = INIT_SQL_PATH.read_text(encoding="utf-8")
        assert "uq_comparacao_fornecedor_regra" in raw
        assert "UNIQUE (comparacao_id, fornecedor_id, regra_id)" in raw

    def test_corrections_importance_check(self):
        tables = _create_table_statements()
        assert _has_check_constraint(
            tables["corrections"],
            "baixa",
        )

    def test_analyses_status_check(self):
        tables = _create_table_statements()
        assert _has_check_constraint(
            tables["analyses"],
            "completed",
        )


class TestInitSqlChatContract:
    def test_chat_conversations_context_json(self):
        tables = _create_table_statements()
        assert "chat_conversations" in tables
        types = _column_types(tables["chat_conversations"])
        assert types["context_json"] == "json"

    def test_chat_messages_role_check(self):
        tables = _create_table_statements()
        assert "chat_messages" in tables
        assert _has_check_constraint(
            tables["chat_messages"],
            "assistant",
        )

    def test_chat_messages_sources_json(self):
        tables = _create_table_statements()
        types = _column_types(tables["chat_messages"])
        assert types["sources"] == "json"

    def test_chat_messages_unico_conversacao_role(self):
        raw = INIT_SQL_PATH.read_text(encoding="utf-8")
        assert "uq_chat_messages_conversation_role" in raw

    def test_chat_messages_retrieval_run_id(self):
        tables = _create_table_statements()
        types = _column_types(tables["chat_messages"])
        assert types.get("retrieval_run_id") == "varchar"

    def test_retrieval_runs_existe(self):
        tables = _create_table_statements()
        assert "retrieval_runs" in tables
        types = _column_types(tables["retrieval_runs"])
        assert types["query_hash"] == "varchar"
        assert types["corpus_version"] == "varchar"
        assert types["retrieved_ids"] == "jsonb"

    def test_legal_documents_ingest_fase3(self):
        tables = _create_table_statements()
        types = _column_types(tables["legal_documents"])
        assert types["content_hash"] == "varchar"
        assert types["origin"] == "varchar"
        assert types["ingest_status"] == "varchar"
        assert types["ingest_manifest"] == "jsonb"
        raw = INIT_SQL_PATH.read_text(encoding="utf-8")
        assert "schema_version', '20260924_004'" in raw
        assert "search_tsv" in raw
        assert "ix_legal_chunks_search_tsv" in raw

    def test_legal_chunks_fase5_fts(self):
        tables = _create_table_statements()
        types = _column_types(tables["legal_chunks"])
        assert types["search_tsv"] == "tsvector"

    def test_legal_works_fase4(self):
        tables = _create_table_statements()
        assert "legal_works" in tables
        assert "legal_versions" in tables
        assert "legal_provisions" in tables
        assert "legal_id_map" in tables
        types = _column_types(tables["legal_provisions"])
        assert types["path"] == "varchar"
        assert types["canonical_text"] == "text"
        assert types["provision_hash"] == "varchar"

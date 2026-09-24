-- Migração manual de confiabilidade (equivalente Alembic 20260908_001 + _002)
-- Aplicar: docker exec -i sei-db psql -U sei_user -d sei_analise < scripts/apply_reliability_schema.sql

ALTER TABLE documents ADD COLUMN IF NOT EXISTS generation_manifest JSONB;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS classification VARCHAR(50);

ALTER TABLE document_items ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE document_items ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;

ALTER TABLE corrections ADD COLUMN IF NOT EXISTS evidence JSONB;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'legal_chunks' AND column_name = 'metadata'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'legal_chunks' AND column_name = 'doc_metadata'
  ) THEN
    ALTER TABLE legal_chunks RENAME COLUMN metadata TO doc_metadata;
  ELSIF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'legal_chunks' AND column_name = 'doc_metadata'
  ) THEN
    ALTER TABLE legal_chunks ADD COLUMN doc_metadata JSONB;
  END IF;
END $$;

ALTER TABLE legal_chunks ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100);
ALTER TABLE legal_chunks ADD COLUMN IF NOT EXISTS embedding_dim INTEGER;

CREATE UNIQUE INDEX IF NOT EXISTS uq_analyses_active_per_document
  ON analyses (document_id) WHERE status IN ('pending', 'running');
CREATE UNIQUE INDEX IF NOT EXISTS uq_revision_doc_versao
  ON document_revisions (document_id, versao);

ALTER TABLE analyses ADD COLUMN IF NOT EXISTS run_snapshot JSONB;
ALTER TABLE comparacoes ADD COLUMN IF NOT EXISTS run_snapshot JSONB;
ALTER TABLE comparacoes ADD COLUMN IF NOT EXISTS propostas_ids JSONB;

CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    payload JSON NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    lease_until TIMESTAMPTZ,
    error TEXT,
    result JSON,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_type_status ON jobs (type, status);

CREATE TABLE IF NOT EXISTS schema_meta (
    key VARCHAR(64) PRIMARY KEY,
    value VARCHAR(255) NOT NULL
);
ALTER TABLE legal_documents ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);
ALTER TABLE legal_documents ADD COLUMN IF NOT EXISTS origin VARCHAR(200);
ALTER TABLE legal_documents ADD COLUMN IF NOT EXISTS collected_at TIMESTAMPTZ;
ALTER TABLE legal_documents ADD COLUMN IF NOT EXISTS ingest_status VARCHAR(20) NOT NULL DEFAULT 'published';
ALTER TABLE legal_documents ADD COLUMN IF NOT EXISTS last_error TEXT;
ALTER TABLE legal_documents ADD COLUMN IF NOT EXISTS ingest_manifest JSONB;

CREATE TABLE IF NOT EXISTS legal_works (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    law_number VARCHAR(80) NOT NULL UNIQUE,
    title VARCHAR(500) NOT NULL,
    kind VARCHAR(40) NOT NULL DEFAULT 'lei',
    issuing_body VARCHAR(200),
    sphere VARCHAR(40),
    jurisdiction VARCHAR(80),
    subject_area VARCHAR(80),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS legal_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_id UUID NOT NULL REFERENCES legal_works(id) ON DELETE CASCADE,
    source_url VARCHAR(500),
    collected_at TIMESTAMPTZ,
    content_hash VARCHAR(64) NOT NULL,
    wording VARCHAR(40) DEFAULT 'consolidada',
    status VARCHAR(20) NOT NULL DEFAULT 'unpublished',
    validity_start DATE,
    validity_end DATE,
    amending_norm VARCHAR(200),
    validation_source VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS legal_provisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID NOT NULL REFERENCES legal_versions(id) ON DELETE CASCADE,
    work_id UUID NOT NULL REFERENCES legal_works(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES legal_provisions(id) ON DELETE SET NULL,
    path VARCHAR(200) NOT NULL,
    article VARCHAR(40),
    paragraph VARCHAR(40),
    inciso VARCHAR(20),
    alinea VARCHAR(10),
    item VARCHAR(20),
    canonical_text TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'vigente',
    provision_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (version_id, path)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_provision_vigente_path
    ON legal_provisions (work_id, path)
    WHERE status = 'vigente';
CREATE TABLE IF NOT EXISTS legal_id_map (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    old_chunk_id UUID NOT NULL UNIQUE REFERENCES legal_chunks(id) ON DELETE CASCADE,
    provision_id UUID NOT NULL REFERENCES legal_provisions(id) ON DELETE CASCADE,
    legal_document_id UUID NOT NULL REFERENCES legal_documents(id) ON DELETE CASCADE
);

INSERT INTO schema_meta (key, value) VALUES ('schema_version', '20260924_003')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

CREATE TABLE IF NOT EXISTS retrieval_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id VARCHAR(64),
    operation_type VARCHAR(20) NOT NULL,
    query_hash VARCHAR(64) NOT NULL,
    corpus_version VARCHAR(64) NOT NULL,
    embedding_model VARCHAR(100),
    rerank_model VARCHAR(100),
    params JSONB,
    retrieved_ids JSONB NOT NULL DEFAULT '[]',
    scores JSONB NOT NULL DEFAULT '[]',
    filters JSONB,
    classification VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_retrieval_runs_created_at ON retrieval_runs (created_at);
CREATE INDEX IF NOT EXISTS ix_retrieval_runs_operation_type ON retrieval_runs (operation_type);

ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS retrieval_run_id VARCHAR(36);

-- Alembic version tracking (se a tabela existir após alembic stamp)
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL
);
DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('20260924_003');

-- CHECKs alinhados ao ORM (idempotente em Postgres legado)
DO $$
BEGIN
  ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_status_check;
  ALTER TABLE analyses ADD CONSTRAINT analyses_status_check
    CHECK (status IN ('pending', 'running', 'completed', 'completed_with_errors', 'error'));
  ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_file_type_check;
  ALTER TABLE documents ADD CONSTRAINT documents_file_type_check
    CHECK (file_type IN ('pdf', 'docx', 'odt', 'html'));
EXCEPTION WHEN undefined_table THEN
  NULL;
END $$;
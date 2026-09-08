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
INSERT INTO schema_meta (key, value) VALUES ('schema_version', '20260908_002')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Alembic version tracking (se a tabela existir após alembic stamp)
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL
);
DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('20260908_002');

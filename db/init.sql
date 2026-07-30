-- ============================================================
-- Sistema de Análise de Termos de Referência
-- Script de inicialização do banco de dados
-- ============================================================

-- Habilitar extensão para vetores (preparação para RAG v1.0)
CREATE EXTENSION IF NOT EXISTS vector;

-- Habilitar extensão para UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------
-- Tabela: documents
-- Armazena os documentos enviados pelo usuário
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename_original VARCHAR(500) NOT NULL,
    filename_stored VARCHAR(255) NOT NULL UNIQUE,
    file_type VARCHAR(10) NOT NULL CHECK (file_type IN ('pdf', 'docx', 'odt')),
    file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes > 0),
    total_items INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'uploaded'
        CHECK (status IN ('uploaded', 'parsing', 'parsed', 'analyzing', 'completed', 'error')),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------
-- Tabela: document_items
-- Itens estruturados extraídos de cada documento
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    item_number VARCHAR(50) NOT NULL,
    title VARCHAR(500),
    content TEXT NOT NULL,
    page_number INTEGER,
    parent_item_id UUID REFERENCES document_items(id) ON DELETE SET NULL,
    item_order INTEGER NOT NULL DEFAULT 0,
    item_type VARCHAR(20) NOT NULL DEFAULT 'item'
        CHECK (item_type IN ('section', 'item', 'subitem', 'table', 'annex')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------
-- Tabela: analyses
-- Registro de cada análise executada
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'error')),
    llm_provider VARCHAR(20) NOT NULL,
    llm_model VARCHAR(100) NOT NULL,
    total_items INTEGER DEFAULT 0,
    analyzed_items INTEGER DEFAULT 0,
    score_overall NUMERIC(4,2) CHECK (score_overall >= 0 AND score_overall <= 10),
    score_juridical NUMERIC(4,2) CHECK (score_juridical >= 0 AND score_juridical <= 10),
    score_technical NUMERIC(4,2) CHECK (score_technical >= 0 AND score_technical <= 10),
    score_writing NUMERIC(4,2) CHECK (score_writing >= 0 AND score_writing <= 10),
    score_structural NUMERIC(4,2) CHECK (score_structural >= 0 AND score_structural <= 10),
    risk_level VARCHAR(10) CHECK (risk_level IN ('baixo', 'medio', 'alto', 'critico')),
    final_opinion TEXT,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------
-- Tabela: corrections
-- Correções sugeridas pela IA para cada item
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS corrections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    document_item_id UUID NOT NULL REFERENCES document_items(id) ON DELETE CASCADE,
    category VARCHAR(20) NOT NULL
        CHECK (category IN ('juridica', 'tecnica', 'redacao', 'estrutural')),
    severity VARCHAR(10) NOT NULL
        CHECK (severity IN ('info', 'baixo', 'medio', 'alto', 'critico')),
    situation TEXT NOT NULL,
    problem TEXT NOT NULL,
    risk TEXT NOT NULL,
    original_text TEXT NOT NULL,
    suggested_text TEXT NOT NULL,
    justification TEXT NOT NULL,
    legal_basis TEXT,
    importance VARCHAR(10) NOT NULL
        CHECK (importance IN ('baixa', 'media', 'alta', 'critica')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------
-- Índices
-- -----------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_document_items_document_id ON document_items(document_id);
CREATE INDEX IF NOT EXISTS idx_document_items_order ON document_items(document_id, item_order);
CREATE INDEX IF NOT EXISTS idx_analyses_document_id ON analyses(document_id);
CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses(status);
CREATE INDEX IF NOT EXISTS idx_corrections_analysis_id ON corrections(analysis_id);
CREATE INDEX IF NOT EXISTS idx_corrections_item_id ON corrections(document_item_id);
CREATE INDEX IF NOT EXISTS idx_corrections_category ON corrections(category);
CREATE INDEX IF NOT EXISTS idx_corrections_severity ON corrections(severity);

-- -----------------------------------------------------------
-- Trigger: atualizar updated_at automaticamente
-- -----------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

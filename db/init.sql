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
    document_type VARCHAR(10) NOT NULL DEFAULT 'tr'
        CHECK (document_type IN ('tr', 'proposta')),
    fornecedor_id UUID REFERENCES fornecedores(id) ON DELETE SET NULL,
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
        CHECK (item_type IN ('section', 'item', 'subitem', 'table', 'annex'))
);

-- -----------------------------------------------------------
-- Tabela: document_revisions
-- Histórico e versionamento de edições do documento (Single-User)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_revisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    versao INTEGER NOT NULL,
    rotulo VARCHAR(150) NOT NULL,
    descricao VARCHAR(500),
    items_snapshot JSON NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_revisions_doc_id ON document_revisions(document_id);

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
    analysis_mode VARCHAR(20) NOT NULL DEFAULT 'multi_agent',
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
    agent_origin VARCHAR(20),
    review_status VARCHAR(20) NOT NULL DEFAULT 'pendente'
        CHECK (review_status IN ('pendente', 'aprovada', 'rejeitada', 'ajustada')),
    review_note TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------
-- Tabela: legal_documents
-- Corpus jurídico (leis, decretos) para o RAG
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS legal_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    law_number VARCHAR(50) NOT NULL UNIQUE,
    law_title VARCHAR(500) NOT NULL,
    source_url VARCHAR(500),
    version VARCHAR(50),
    total_chunks INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------
-- Tabela: legal_chunks
-- Trechos (artigos) das leis com embedding para busca semântica
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS legal_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    legal_document_id UUID NOT NULL REFERENCES legal_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    article VARCHAR(100),
    section VARCHAR(200),
    chunk_text TEXT NOT NULL,
    embedding TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------
-- Tabela: fornecedores
-- Fornecedores que participam da licitação (módulo de auditoria)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS fornecedores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(500) NOT NULL,
    cnpj VARCHAR(18),
    email VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------
-- Tabela: moldes
-- Moldes de regras de conformidade (config_json validado)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS moldes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(200) NOT NULL,
    descricao TEXT,
    config_json TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------
-- Tabela: comparacoes
-- Execução de uma comparação TR × propostas
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS comparacoes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tr_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    molde_id UUID NOT NULL REFERENCES moldes(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'error')),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- -----------------------------------------------------------
-- Tabela: comparacao_resultados
-- Resultado de uma regra para um fornecedor (matriz de conformidade)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS comparacao_resultados (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    comparacao_id UUID NOT NULL REFERENCES comparacoes(id) ON DELETE CASCADE,
    fornecedor_id UUID NOT NULL REFERENCES fornecedores(id) ON DELETE CASCADE,
    regra_id VARCHAR(100) NOT NULL,
    status VARCHAR(10) NOT NULL
        CHECK (status IN ('ok', 'falha', 'atencao')),
    motivo TEXT,
    valor_tr VARCHAR(255),
    valor_proposta VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_comparacao_fornecedor_regra
        UNIQUE (comparacao_id, fornecedor_id, regra_id)
);

-- -----------------------------------------------------------
-- Tabela: chat_conversations
-- Conversas consultivas do Copiloto (chat v1.1)
-- Referenciam documents/analyses apenas como contexto (somente leitura)
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_conversations (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(36),
    analysis_id VARCHAR(36),
    context_json JSON NOT NULL DEFAULT '{}',
    title VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------
-- Tabela: chat_messages
-- Mensagens (user/assistant) de uma conversa do Copiloto
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL
        REFERENCES chat_conversations(id) ON DELETE CASCADE,
    role VARCHAR(10) NOT NULL DEFAULT 'user'
        CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources JSON NOT NULL DEFAULT '[]',
    grounded BOOLEAN NOT NULL DEFAULT FALSE,
    confidence DOUBLE PRECISION,
    provider VARCHAR(50),
    model VARCHAR(100),
    latency_ms BIGINT,
    warning TEXT,
    feedback_rating VARCHAR(10),
    feedback_comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_chat_messages_conversation_role
        UNIQUE (conversation_id, role, id)
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
CREATE INDEX IF NOT EXISTS idx_legal_chunks_document_id ON legal_chunks(legal_document_id);
CREATE INDEX IF NOT EXISTS idx_legal_chunks_article ON legal_chunks(article);
CREATE INDEX IF NOT EXISTS idx_documents_fornecedor_id ON documents(fornecedor_id);
CREATE INDEX IF NOT EXISTS idx_documents_document_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_comparacoes_tr_document_id ON comparacoes(tr_document_id);
CREATE INDEX IF NOT EXISTS idx_comparacoes_status ON comparacoes(status);
CREATE INDEX IF NOT EXISTS idx_comparacao_resultados_comparacao_id ON comparacao_resultados(comparacao_id);
CREATE INDEX IF NOT EXISTS idx_comparacao_resultados_fornecedor_id ON comparacao_resultados(fornecedor_id);
CREATE INDEX IF NOT EXISTS ix_chat_conversations_updated_at ON chat_conversations(updated_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id ON chat_messages(conversation_id);

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

-- ============================================================
-- Migração: Copiloto (chat consultivo) — chat v1.1
-- Adiciona as tabelas chat_conversations e chat_messages.
-- Idempotente (CREATE IF NOT EXISTS).
-- ============================================================

CREATE TABLE IF NOT EXISTS chat_conversations (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(36),
    analysis_id VARCHAR(36),
    context_json JSON NOT NULL DEFAULT '{}',
    title VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

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

CREATE INDEX IF NOT EXISTS ix_chat_conversations_updated_at ON chat_conversations(updated_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id ON chat_messages(conversation_id);

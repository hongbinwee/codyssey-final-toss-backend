-- Additive BGE-M3 comparison storage. Existing 384-d MiniLM vectors stay intact.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rag.index_run_embedding_profiles (
    run_id UUID NOT NULL REFERENCES rag.index_runs(run_id) ON DELETE CASCADE,
    embedding_model TEXT NOT NULL,
    model_revision TEXT NOT NULL,
    dimension INTEGER NOT NULL CHECK (dimension = 1024),
    max_input_tokens INTEGER NOT NULL CHECK (max_input_tokens > 0),
    category_scope TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('building', 'ready', 'failed')),
    chunk_count BIGINT NOT NULL CHECK (chunk_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, embedding_model)
);

CREATE TABLE IF NOT EXISTS rag.evidence_chunk_embeddings (
    run_id UUID NOT NULL,
    chunk_id TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding vector(1024) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, chunk_id, embedding_model),
    FOREIGN KEY (run_id, embedding_model)
        REFERENCES rag.index_run_embedding_profiles(run_id, embedding_model) ON DELETE CASCADE,
    FOREIGN KEY (run_id, chunk_id)
        REFERENCES rag.evidence_chunks(run_id, chunk_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS evidence_chunk_embeddings_cosine_idx
    ON rag.evidence_chunk_embeddings USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS evidence_chunk_embeddings_model_run_idx
    ON rag.evidence_chunk_embeddings (run_id, embedding_model);

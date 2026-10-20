-- Run on the existing toss_rag database as its administrator.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_search CASCADE;

CREATE SCHEMA IF NOT EXISTS rag;

CREATE TABLE IF NOT EXISTS rag.index_runs (
    run_id UUID PRIMARY KEY,
    profile_name TEXT NOT NULL DEFAULT 'all_products',
    dataset_version TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    chunker_version TEXT NOT NULL,
    category_policy_version TEXT NOT NULL DEFAULT 'legacy',
    status TEXT NOT NULL CHECK (status IN ('building', 'active', 'superseded', 'failed')),
    counts JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_code TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    UNIQUE (run_id, dataset_version)
);

ALTER TABLE rag.index_runs
    ADD COLUMN IF NOT EXISTS category_policy_version TEXT NOT NULL DEFAULT 'legacy';
ALTER TABLE rag.index_runs
    ADD COLUMN IF NOT EXISTS profile_name TEXT NOT NULL DEFAULT 'all_products';

-- Replace the legacy global active-run constraint with one per profile.
DROP INDEX IF EXISTS rag.index_runs_one_active_idx;
CREATE UNIQUE INDEX IF NOT EXISTS index_runs_one_active_per_profile_idx
    ON rag.index_runs (profile_name) WHERE status = 'active';
CREATE UNIQUE INDEX IF NOT EXISTS index_runs_profile_run_idx
    ON rag.index_runs (profile_name, run_id);
CREATE INDEX IF NOT EXISTS index_runs_dataset_status_idx
    ON rag.index_runs (dataset_version, status);

CREATE TABLE IF NOT EXISTS rag.index_profiles (
    profile_name TEXT PRIMARY KEY,
    active_run_id UUID NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (profile_name, active_run_id)
        REFERENCES rag.index_runs(profile_name, run_id)
);

-- Backfill legacy installations without changing an existing profile pointer.
INSERT INTO rag.index_profiles (profile_name, active_run_id)
SELECT profile_name, run_id FROM rag.index_runs WHERE status = 'active'
ON CONFLICT (profile_name) DO NOTHING;

CREATE TABLE IF NOT EXISTS rag.quarantined_products (
    run_id UUID NOT NULL REFERENCES rag.index_runs(run_id) ON DELETE CASCADE,
    dataset_version TEXT NOT NULL,
    category TEXT NOT NULL,
    product_id TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    product_title TEXT,
    main_category TEXT,
    categories JSONB NOT NULL DEFAULT '[]'::jsonb,
    type_signals JSONB NOT NULL DEFAULT '[]'::jsonb,
    review_status TEXT NOT NULL DEFAULT 'pending_review'
        CHECK (review_status IN ('pending_review', 'confirmed', 'rejected')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, category, product_id),
    FOREIGN KEY (run_id, dataset_version)
        REFERENCES rag.index_runs(run_id, dataset_version) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS quarantined_products_review_idx
    ON rag.quarantined_products (review_status, category, product_id);

CREATE TABLE IF NOT EXISTS rag.indexed_products (
    run_id UUID NOT NULL REFERENCES rag.index_runs(run_id) ON DELETE CASCADE,
    dataset_version TEXT NOT NULL,
    category TEXT NOT NULL,
    product_id TEXT NOT NULL,
    product_payload JSONB NOT NULL,
    price_amount NUMERIC,
    price_currency TEXT,
    PRIMARY KEY (run_id, category, product_id),
    UNIQUE (run_id, dataset_version, category, product_id),
    FOREIGN KEY (run_id, dataset_version)
        REFERENCES rag.index_runs(run_id, dataset_version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rag.evidence_chunks (
    run_id UUID NOT NULL REFERENCES rag.index_runs(run_id) ON DELETE CASCADE,
    chunk_key TEXT NOT NULL UNIQUE,
    chunk_id TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    category TEXT NOT NULL,
    product_id TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('product', 'review')),
    source_id TEXT NOT NULL,
    source_field TEXT NOT NULL CHECK (source_field LIKE '/%'),
    start_offset INTEGER NOT NULL CHECK (start_offset >= 0),
    end_offset INTEGER NOT NULL CHECK (end_offset > start_offset),
    evidence_text TEXT NOT NULL,
    embedding_text TEXT NOT NULL,
    source_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(384) NOT NULL,
    embedding_model TEXT NOT NULL,
    chunker_version TEXT NOT NULL,
    PRIMARY KEY (run_id, chunk_id),
    FOREIGN KEY (run_id, dataset_version, category, product_id)
        REFERENCES rag.indexed_products(run_id, dataset_version, category, product_id)
        ON DELETE CASCADE,
    CHECK (char_length(evidence_text) = end_offset - start_offset),
    CHECK (source_type <> 'product' OR source_id = product_id)
);

CREATE INDEX IF NOT EXISTS evidence_chunks_run_source_idx
    ON rag.evidence_chunks (run_id, category, product_id, source_type);
CREATE INDEX IF NOT EXISTS indexed_products_run_category_idx
    ON rag.indexed_products (run_id, category, product_id);

-- pg_search 0.26.0 provides the ParadeDB index access method. Keep run_id in
-- the index because serving queries filter each channel to the active run.
CREATE INDEX IF NOT EXISTS evidence_chunks_search_idx
    ON rag.evidence_chunks USING paradedb (chunk_key, run_id, embedding_text);

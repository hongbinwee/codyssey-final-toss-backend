-- Apply to toss_rag as an administrator before enabling the aspect aggregate API.
CREATE SCHEMA IF NOT EXISTS rag;

CREATE TABLE IF NOT EXISTS rag.review_aspect_annotation_batches (
    batch_id UUID PRIMARY KEY,
    profile_name TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    category TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL,
    classifier_version TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('building', 'active', 'superseded', 'failed')),
    expected_review_count BIGINT NOT NULL CHECK (expected_review_count >= 0),
    labeled_review_count BIGINT NOT NULL DEFAULT 0 CHECK (labeled_review_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    activated_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS review_aspect_one_active_batch_idx
    ON rag.review_aspect_annotation_batches (profile_name, dataset_version, category, taxonomy_version)
    WHERE status = 'active';
CREATE INDEX IF NOT EXISTS review_aspect_batch_lookup_idx
    ON rag.review_aspect_annotation_batches (profile_name, dataset_version, category, taxonomy_version, status);

CREATE TABLE IF NOT EXISTS rag.review_aspect_labels (
    batch_id UUID NOT NULL REFERENCES rag.review_aspect_annotation_batches(batch_id) ON DELETE CASCADE,
    product_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    aspect TEXT NOT NULL,
    polarity TEXT NOT NULL CHECK (polarity IN (
        'positive', 'negative', 'mixed', 'neutral', 'not_mentioned', 'unclassified'
    )),
    confidence NUMERIC(6, 5) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    PRIMARY KEY (batch_id, product_id, source_id, aspect)
);

CREATE INDEX IF NOT EXISTS review_aspect_labels_lookup_idx
    ON rag.review_aspect_labels (batch_id, aspect, product_id, source_id);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rag_runtime') THEN
        EXECUTE 'GRANT USAGE ON SCHEMA rag TO rag_runtime';
        EXECUTE 'GRANT SELECT ON rag.review_aspect_annotation_batches, rag.review_aspect_labels TO rag_runtime';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rag_annotation_loader') THEN
        EXECUTE 'GRANT USAGE ON SCHEMA rag TO rag_annotation_loader';
        EXECUTE 'GRANT SELECT ON rag.index_profiles, rag.index_runs TO rag_annotation_loader';
        EXECUTE 'GRANT SELECT (run_id, category) ON rag.indexed_products TO rag_annotation_loader';
        EXECUTE 'GRANT SELECT (run_id, dataset_version, category, source_type, product_id, source_id, source_field, start_offset, end_offset, evidence_text) ON rag.evidence_chunks TO rag_annotation_loader';
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON rag.review_aspect_annotation_batches, rag.review_aspect_labels TO rag_annotation_loader';
    END IF;
END
$$;

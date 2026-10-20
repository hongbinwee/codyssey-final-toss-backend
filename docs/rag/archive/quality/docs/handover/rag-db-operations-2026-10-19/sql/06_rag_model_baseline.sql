-- Connect to database toss_rag. Read only. Current active-run baseline, not a new-run publish operation.
BEGIN READ ONLY;
SELECT embedding_model,chunker_version,vector_dims(embedding) AS dimensions,count(*) AS chunks FROM rag.evidence_chunks WHERE run_id=(SELECT active_run_id FROM rag.index_profiles WHERE profile_name='test_items2') GROUP BY embedding_model,chunker_version,vector_dims(embedding);
SELECT count(DISTINCT product_id) AS products,count(DISTINCT source_id) FILTER (WHERE source_type='review') AS review_sources FROM rag.evidence_chunks WHERE run_id=(SELECT active_run_id FROM rag.index_profiles WHERE profile_name='test_items2');
SELECT extname,extversion FROM pg_extension WHERE extname IN ('vector','pg_search');
ROLLBACK;

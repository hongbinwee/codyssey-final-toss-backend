-- Connect to database toss_rag. Read only.
BEGIN READ ONLY;
SELECT p.profile_name,r.run_id,r.dataset_version,r.embedding_model,r.chunker_version,r.status,r.counts FROM rag.index_profiles p JOIN rag.index_runs r ON r.profile_name=p.profile_name AND r.run_id=p.active_run_id ORDER BY p.profile_name;
SELECT source_type,count(*) AS chunks,count(embedding) AS embedded FROM rag.evidence_chunks WHERE run_id=(SELECT active_run_id FROM rag.index_profiles WHERE profile_name='test_items2') GROUP BY source_type ORDER BY source_type;
ROLLBACK;

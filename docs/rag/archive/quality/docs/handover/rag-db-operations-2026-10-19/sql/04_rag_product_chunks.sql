-- Connect to database toss_rag. Read only. Change product ID when needed.
BEGIN READ ONLY;
SELECT product_id,source_type,source_id,source_field,start_offset,end_offset,evidence_text,source_metadata,embedding_model,chunker_version,vector_dims(embedding) AS dimensions FROM rag.evidence_chunks WHERE run_id=(SELECT active_run_id FROM rag.index_profiles WHERE profile_name='test_items2') AND product_id='p-v4-o-0286' ORDER BY source_type,source_id,start_offset;
ROLLBACK;

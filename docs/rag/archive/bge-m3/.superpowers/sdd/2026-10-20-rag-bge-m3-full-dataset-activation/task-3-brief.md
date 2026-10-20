### Task 3: Route BGE queries through hybrid search and readiness

**Files:**
- Modify: `src/toss_ads/rag/embeddings.py`
- Modify: `src/toss_ads/rag/bge_m3.py`
- Modify: `src/toss_ads/rag/config.py`
- Modify: `src/toss_ads/rag/retriever.py`
- Modify: `src/toss_ads/rag/api.py`
- Modify: `deploy/product-rag-runtime.env.example`
- Test: `tests/test_rag_retriever.py`
- Test: `tests/test_rag_api.py`

**Interfaces:**
- Consumes: Task 1 wildcard profile queries and the existing `BgeM3Embedder` dense adapter.
- Produces: `create_embedder(settings)` returns the BGE adapter for `BAAI/bge-m3` at the pinned revision and persistent cache path, and FastEmbed for the existing MiniLM model; `hybrid_search` dispatches by configured vector dimension/model and keeps BM25 + product RRF unchanged.

- [ ] **Step 1: Write failing tests**
  - Add `test_bge_model_factory_returns_pinned_1024_dimension_embedder` asserting BGE model name, revision, 1,024 dimension, and 128-token maximum.
  - Add `test_bge_model_uses_configured_persistent_cache_path` asserting model snapshot downloads use the configured cache directory.
  - Add `test_bge_hybrid_search_uses_bm25_and_embedding_vector_channels` asserting BM25 and `search_embedding_vector` receive the same requested category and the configured model; include review-only channels for review queries.
  - Add `test_minilm_hybrid_search_keeps_384_dimension_vector_path` asserting the existing MiniLM vector search continues to work when the active run records MiniLM.
  - Add API tests that BGE health is `not_ready` for missing, building, failed, wrong-scope, or incomplete profiles and becomes `ok` only for a complete ready wildcard profile; assert BGE does not require changing `index_runs.embedding_model`.
  - Add `test_bge_search_returns_index_not_ready_without_embedding_partial_profile` asserting a missing or building full profile returns `index_not_ready` before query embedding or retrieval.
- [ ] **Step 2: Run focused tests and confirm the new assertions fail**
  - Run each focused suite: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_retriever.py'`; `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_api.py'`.
  - Expected: existing MiniLM behavior passes; BGE factory, routing, and profile readiness cases fail before implementation.
- [ ] **Step 3: Implement model-aware embedder, retrieval, and readiness**
  - Add `BGE_M3_CACHE_PATH` to `Settings`, defaulted beneath `FASTEMBED_CACHE_PATH` so the existing mounted cache volume persists BGE weights.
  - Pass `cache_dir` through `BgeM3Embedder` to `snapshot_download`; instantiate it with revision `5617a9f61b028005a4858fdac845db406aefb181` and 128-token maximum. Keep MiniLM as the default and rollback path.
  - For BGE, use `search_embedding_vector(run_id, embedding_model, vector, limit, category, source_type)`; for MiniLM, retain `search_vector` and its 384D check.
  - Always run the existing BM25 channel and preserve product-level RRF with `k=60`; use BGE dense vectors for both general and review-only dense channels.
  - Make `/healthz` verify BGE profile info, scope, status, expected count, and actual stored count against all active-run chunks; make search return `index_not_ready` before embedding unless the BGE profile info is ready at scope `*`. Keep MiniLM readiness tied to its existing active-run model.
- [ ] **Step 4: Run focused tests and verify they pass**
  - Run each focused suite: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_retriever.py'`; `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_api.py'`.
  - Expected: all BGE and MiniLM retrieval/readiness cases pass, with no BGE sparse or ColBERT calls.
- [ ] **Step 5: Review the diff and commit only Task 3 files**
  - Confirm repository root and remote; stage only the five source files, runtime example, and two listed test files.


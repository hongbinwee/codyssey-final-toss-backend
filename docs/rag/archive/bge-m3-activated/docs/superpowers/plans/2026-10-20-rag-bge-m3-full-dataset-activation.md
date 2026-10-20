# test_items2 Full-Dataset BGE-M3 Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate BM25 + BGE-M3 dense hybrid search for all 1,500 products and 114,106 chunks in the active `test_items2` run.

**Architecture:** Keep the active run, chunks, BM25 index, and MiniLM vectors. Widen the existing BGE profile from `beauty` to `*`, fill only missing vectors, and make model-aware retrieval/readiness select BGE only when the full profile is ready. Build and switch the local API container after database readiness, keeping the previous MiniLM container available for rollback.

**Tech Stack:** Python 3.12, FastAPI, FlagEmbedding BGE-M3 dense encoder, PostgreSQL 5432 database `toss_rag`, pgvector, ParadeDB BM25, Docker.

**Spec:** [2026-10-20-rag-bge-m3-full-dataset-activation-design.md](../specs/2026-10-20-rag-bge-m3-full-dataset-activation-design.md)

**Operations:** [BGE-M3 full-dataset runtime and rollback runbook](../../rag-bge-m3-test-items2-full-operations.md)

## Global Constraints

- Target only active run `e925490f-4f34-4c03-9248-eb9ebdfcde48` and dataset version `test_items2:v6.1-review-refined:sha256=94681a28271ca9b1:products=1500:reviews=46100`.
- Use only PostgreSQL port `5432`, database `toss_rag`; do not connect to or query port `15436`.
- Full scope is the literal `category_scope='*'`, expected to cover 1,500 products and 114,106 chunks across `beauty`, `fashion`, `food`, and `living`.
- Use model `BAAI/bge-m3`, revision `5617a9f61b028005a4858fdac845db406aefb181`, dense dimension 1,024, and maximum input length 128 tokens.
- Keep BM25 and product-level RRF `k=60`; do not enable BGE sparse or ColBERT outputs.
- Preserve all existing chunks, BM25 rows, MiniLM vectors, BGE beauty vectors, and the active run's `index_runs.embedding_model` value.
- Do not stage or overwrite user-owned worktree changes. Work in the `codyssey-final-toss-backend` repository on `feature/rag-bge-m3`; do not push, open a PR, or merge without a separate user instruction.
- Do not describe the beauty-only labels as a full-dataset accuracy result; no labeled evaluation set exists for fashion, food, or living.

## Review Focus

- Full scope `*` must include all categories while a requested category still filters dense results to that category — pin in Task 1 store tests.
- Promoting an existing beauty profile must preserve its 78,595 vectors and make it unavailable to BGE queries while `building` — pin in Task 1 profile transition tests.
- A wrong run, dataset version, or category set must fail before model loading or profile mutation — pin in Task 2 indexing tests.
- BGE query vectors must be 1,024-dimensional and use the BGE vector table; MiniLM must retain its 384-dimensional path and remain a valid rollback — pin in Task 3 retrieval and factory tests.
- BGE readiness must require a full ready profile with 114,106 stored vectors even though `index_runs.embedding_model` still names MiniLM — pin in Task 3 API readiness tests.

---

### Task 1: Add safe whole-run BGE profile scope

**Files:**
- Modify: `src/toss_ads/rag/store.py`
- Test: `tests/test_rag_embedding_store.py`

**Interfaces:**
- Consumes: Existing `RagStore` profile and vector methods.
- Produces: `prepare_full_embedding_profile(*, run_id: str, embedding_model: str, model_revision: str, expected_chunk_count: int) -> None`, `embedding_target_category_counts(run_id: str, dataset_version: str) -> dict[str, int]`, and `embedding_profile_info(run_id: str, embedding_model: str) -> dict[str, Any] | None`; allow `"*"` as the full-run scope for count, missing-row, readiness, and vector search operations.

- [ ] **Step 1: Write failing tests**
  - Add `test_prepare_full_profile_promotes_complete_beauty_profile_to_building` asserting the existing profile's beauty vector count is checked and its scope/count/status become `*`/`114106`/`building` without deleting vectors.
  - Add `test_prepare_full_profile_rejects_incomplete_beauty_vectors` asserting no scope promotion occurs if the existing vector count differs from its beauty chunk count.
  - Add `test_full_scope_counts_and_missing_texts_cover_all_categories` asserting the `*` scope selects all four categories while category-filtered dense search still selects only the requested category, and profile info reports its scope/status/dimension/count.
  - Add `test_target_category_counts_validate_dataset_version` asserting the target run resolves to `beauty=78595`, `fashion=11566`, `food=13409`, and `living=10536`, and a version mismatch is rejected.
  - Add `test_full_profile_cannot_search_while_building_or_with_wrong_category_scope` asserting partial or non-ready profiles and category filters outside the profile scope are rejected.
- [ ] **Step 2: Run the focused tests and confirm the new assertions fail**
  - Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_embedding_store.py'`
  - Expected: the new full-scope behavior is absent; existing beauty-scope tests continue to pass.
- [ ] **Step 3: Implement atomic scope promotion and wildcard scope queries**
  - In `RagStore`, validate the active run's total chunk count and existing profile metadata before changing scope.
  - In one transaction, lock the profile row with `FOR UPDATE`, validate the existing complete `beauty` profile or matching full profile, then set the scope/count/status to `*`/expected/`building` and preserve its rows.
  - Make `embedding_target_category_counts`, `embedding_target_chunk_count`, `missing_embedding_texts`, `embedding_profile_counts`, `mark_embedding_profile_ready`, and `search_embedding_vector` interpret `*` as every category; retain exact-category behavior for existing beauty comparisons.
  - Make dense search require a `ready` 1,024D profile and `category_scope='*'` or an exact category match.
- [ ] **Step 4: Run focused tests and verify they pass**
  - Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_embedding_store.py'`
  - Expected: all store tests pass, including the new promotion, preservation, wildcard count, category filter, and not-ready cases.
- [ ] **Step 5: Review the diff and commit only Task 1 files**
  - Before commit, confirm Git root and remote match the Backend repository; stage only `src/toss_ads/rag/store.py` and `tests/test_rag_embedding_store.py`.

### Task 2: Index every missing BGE vector with resume support

**Files:**
- Modify: `src/toss_ads/rag/embedding_indexer.py`
- Modify: `src/toss_ads/rag/__main__.py`
- Test: `tests/test_rag_embedding_indexer.py`

**Interfaces:**
- Consumes: Task 1 `prepare_full_embedding_profile` and wildcard store methods.
- Produces: `index_existing_chunks(..., category="*", ...)` handles all categories and retains the existing summary field with `category="*"`; CLI supports an explicit `--all-categories` option mutually exclusive with `--category` and checks the approved run, dataset version, and category counts before model loading.

- [ ] **Step 1: Write failing tests**
  - Add `test_all_category_indexing_reuses_existing_vectors_and_embeds_only_missing` asserting preexisting beauty vectors are reused and missing fashion, food, and living chunks are processed in batches no larger than 16.
  - Add `test_full_profile_is_ready_only_at_expected_total_count` asserting ready status is set only when the stored count is 114,106.
  - Add `test_full_indexing_resumes_after_embedding_failure_without_deleting_vectors` asserting saved vectors remain and a retry processes only missing chunks.
  - Add `test_all_category_cli_scope_is_explicit_and_mutually_exclusive` asserting `--all-categories` selects `*` and cannot be combined with `--category`.
  - Add `test_full_indexing_rejects_wrong_run_version_or_category_counts_before_profile_write` asserting the exact approved run, dataset version, and four category counts are required before model loading or profile mutation.
  - Keep existing category-specific comparison calls backward compatible.
- [ ] **Step 2: Run the focused tests and confirm the new assertions fail**
  - Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_embedding_indexer.py'`
  - Expected: all existing beauty indexing tests pass; the new all-category assertions fail before implementation.
- [ ] **Step 3: Implement whole-run indexing and CLI scope selection**
  - Preflight the exact run ID `e925490f-4f34-4c03-9248-eb9ebdfcde48`, dataset version from the spec, and category counts `beauty=78595`, `fashion=11566`, `food=13409`, `living=10536` before loading BGE-M3 or mutating its profile.
  - Promote the profile to `*`, reuse all saved vectors, embed missing `embedding_text` values in batches of at most 16, and mark ready only after expected and stored counts match.
  - On an interrupted run, mark the incomplete profile failed without deleting vectors; a retry returns it to `building` and resumes from missing rows.
  - Write a machine-readable indexing summary with the run, dataset, scope, model revision, total/preexisting/new vector counts, elapsed time, throughput, and final status.
- [ ] **Step 4: Run focused tests and verify they pass**
  - Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_embedding_indexer.py'`
  - Expected: beauty comparison compatibility and all full-run/resume assertions pass.
- [ ] **Step 5: Review the diff and commit only Task 2 files**
  - Confirm repository root and remote; stage only `src/toss_ads/rag/embedding_indexer.py`, `src/toss_ads/rag/__main__.py`, and `tests/test_rag_embedding_indexer.py`.

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

### Task 4: Document and safely switch the local API runtime

**Files:**
- Modify: `docs/product-rag-service.md`
- Create: `reports/rag-bge-m3-test-items2-full-2026-10-20-index.json`

**Interfaces:**
- Consumes: Task 3 BGE-aware runtime configuration and Task 2 full-index summary.
- Produces: documented BGE activation/rollback procedure and a full-index report that records only operational metadata and counts, not credentials or source text.

- [ ] **Step 1: Update runtime and operations documentation**
  - Keep the runtime example's default MiniLM setting for other installations and add `BGE_M3_CACHE_PATH=.cache/fastembed/huggingface`; document the explicit local `RAG_EMBEDDING_MODEL=BAAI/bge-m3` switch only after full profile readiness.
  - Replace the outdated `test_items/beauty` runtime description with the active `test_items2` full-corpus state and list all four categories.
  - Document the container replacement sequence: preserve the existing MiniLM container/config for rollback, build the new image, launch/health-check the BGE container on a temporary port, then switch the service to port 8002 only after it is healthy.
  - Read the existing container's configuration into process memory to clone its environment, host networking, and cache bind mount; override only the BGE model and temporary/final port. Never print or persist runtime secrets.
  - Document that this is an operational smoke check, not an accuracy result; beauty has 10 positive and 2 OOD queries and the other categories have no approved labels.
- [ ] **Step 2: Run documentation and diff checks**
  - Run: `git diff --check` and validate all relative Markdown links in the touched documentation.
  - Expected: no whitespace errors, broken local targets, credentials, or claims of full-dataset accuracy.
- [ ] **Step 3: Commit only Task 4 files**
  - Confirm repository root and remote; stage only `docs/product-rag-service.md` and the generated full-index report.

### Task 5: Populate the full profile and activate BGE-M3

**Files:**
- Runtime data: `rag.index_run_embedding_profiles` and missing rows in `rag.evidence_chunk_embeddings` for the approved run only.
- Runtime container: `product-rag-api` and its BGE replacement.

**Interfaces:**
- Consumes: Tasks 1–4 code, operations, and index summary format.
- Produces: ready BGE profile at `*` with 114,106 vectors and a healthy local BM25 + BGE-M3 runtime on port 8002.

- [ ] **Step 1: Recheck the database target and exact run before writes**
  - Verify only `5432/toss_rag`, run ID `e925490f-4f34-4c03-9248-eb9ebdfcde48`, dataset version from the spec, 1,500 products, 114,106 chunks, category counts `beauty=78595`, `fashion=11566`, `food=13409`, `living=10536`, and 78,595 existing beauty BGE vectors.
  - Expected: every value matches the approved target; stop before writes if any value changed.
- [ ] **Step 2: Run resumable all-category BGE indexing**
  - Run `python -m toss_ads.rag embed-model --run-id e925490f-4f34-4c03-9248-eb9ebdfcde48 --dataset-version test_items2:v6.1-review-refined:sha256=94681a28271ca9b1:products=1500:reviews=46100 --all-categories --batch-size 16 --summary-output reports/rag-bge-m3-test-items2-full-2026-10-20-index.json` using the authorized local DB writer configuration; keep credentials out of command output and the report.
  - Expected: scope `*`, total 114,106, preexisting 78,595, new vectors 35,511, stored 114,106, profile `ready`.
- [ ] **Step 3: Verify database profile and vector counts**
  - Query only `5432/toss_rag`; confirm all four categories contribute the expected chunk counts, profile revision/dimension/scope/status match the spec, total BGE vectors equal 114,106, and MiniLM vectors remain present.
  - Expected: all counts match before changing the service runtime.
- [ ] **Step 4: Build and switch the local API container**
  - Build the image from `deploy/product-rag.Dockerfile`; create a BGE validation container on port 8003 from the preserved runtime config and cache mount, keeping secrets in process memory and out of output. After health and category-filtered/unfiltered search smoke checks pass, stop and rename the old container for rollback, then create the final BGE container on port 8002. If final startup or readiness fails, stop it and restart the saved MiniLM container.
  - Expected: `/healthz` reports `ok`; the container config uses `BAAI/bge-m3`; category-filtered requests work for beauty, fashion, food, and living, and an unfiltered request searches all four categories with BM25 + BGE dense retrieval.
- [ ] **Step 5: Verify rollback and report state**
  - Confirm the saved MiniLM container can be restarted with the existing 384D vectors if BGE activation fails; do not delete BGE rows during rollback.
  - Record the final profile and runtime state in the index report; state clearly that full-dataset retrieval accuracy remains unmeasured outside beauty.
- [ ] **Step 6: Review Git state and commit only owned files**
  - Confirm Git root, remote, and branch; inspect the staged file list to ensure unrelated user changes are excluded. Do not push, open a PR, or merge.

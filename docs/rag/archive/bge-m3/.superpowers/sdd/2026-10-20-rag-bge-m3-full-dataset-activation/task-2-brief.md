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


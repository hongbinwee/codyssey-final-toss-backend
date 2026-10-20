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


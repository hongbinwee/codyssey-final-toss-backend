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

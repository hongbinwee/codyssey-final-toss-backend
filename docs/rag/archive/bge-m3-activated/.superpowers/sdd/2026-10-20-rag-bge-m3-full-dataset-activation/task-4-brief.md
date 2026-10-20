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


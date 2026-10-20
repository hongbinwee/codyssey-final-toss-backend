# BGE API Compatibility Recovery Plan

> **For agentic workers:** Execute inline with superpowers:executing-plans. Preserve BGE embeddings and the pre-switch API contract; review the complete change before deployment.

**Goal:** Restore pre-BGE API 0.3 requests, response metadata, catalog routes and Commerce validation while continuing to search the existing 1,024-dimensional BGE index on 5432/toss_rag.

**Evidence:** Running image rag-bge-m3-full-test-items2-252bc90 serves API 0.2.0, rejects profile/product_type/filters.in_stock with 422, omits catalog routes, and lacks the 0.3 Commerce/relevance pipeline. Port 8002 and health remain reachable. The same extended request was reproduced as 422/invalid_request before editing.

**Workspace:** feature/rag-bge-api-compat, based on the prior 0.3 implementation 24a1051. Other worktrees, main, original records, active run and all vectors are preserved.

## Task 1 — Restore the serving interface with BGE

- [x] Add regression cases for BGE readiness, extended 0.3 request acceptance, response metadata, category/stock/budget eligibility and the legacy catalog routes.
- [x] Observe BGE tests fail on the unmodified 0.3 base (which only supports 384-dimensional serving).
- [x] Reuse the existing BGE adapter and read-only profile/vector lookup methods; keep the 0.3 profile selection, request validation, relevance and Commerce logic.
- [x] Filter BGE candidates by the same eligible product IDs used in BM25; do not retrieve ineligible prices then pretend they were verified.
- [x] Reject incomplete/wrong-revision BGE profiles before encoding. Preserve MiniLM configuration support.
- [x] Run the focused and complete worktree test suite. Expected: extended requests execute BGE without configuration/dimension errors, no ineligible candidate can bypass filters, and no source/index DB writes.

## Task 2 — Validate and restore the running API

- [x] Build a derived image using the current BGE runtime dependencies/cache.
- [x] Copy runtime credentials only in memory; restore Commerce settings from the saved pre-switch runtime. Use 5432/toss_rag and 5432/toss only.
- [x] Validate a temporary service on 8003: health/model/profile, the formerly rejected request, legacy catalog paths, category search and budget/stock semantics.
- [x] Preserve the old BGE container for rollback, then replace product-rag-api on the existing 8002 port.
- [x] Recheck local/domain health, the same request and catalog paths. Roll back the container if readiness fails.
- [x] Record actual checks and limitations; update the BGE documentation's API/feature status. Do not claim browser E2E for an unavailable client.

## Review focus

No model downgrade; no silent ignore of stock/product_type/profile; same-variant price/stock; BGE SQL product-ID constraints; no vector/index mutation; no credentials in files/output; explicit profile selection; readiness count/revision enforcement; existing routes and response shape; safe rollback.

## Constraints

No main commits/push/merge. No new data import or re-embedding. No speculative frontend changes: the local storefront is not currently listening; its old strict schema is a separate client revision and must not be assumed to be the external caller.

# SDD ledger — plan: docs/superpowers/plans/2026-10-15-rag-service-integration.md

BASE: `bb02734263f4954834265f27378a407d90ac1c48` (`codex/rag-contracts-validation`; clean before plan creation).

## Pre-flight

- Task 1 ↔ Task 2: contract paths consume chunker source paths. Ruling: canonical response/evidence paths are RFC 6901 JSON Pointers emitted by the chunker; update examples/checker, and keep legacy bracket path handling only as a migration aid if fixtures need it.
- Task 2 ↔ Task 4: source client and chunker outputs feed indexer. Ruling: stream category-wide pages and join review parent keys against the products for that category; reject missing or mismatched products.
- Task 3 ↔ Task 5: store search result fields feed RRF and response schema. Ruling: channel ranks are chunk ranks; product RRF uses each product’s best chunk rank in each channel, and returned evidence carries the product’s RRF rank.
- Task 4 ↔ Task 5: active dataset version gates search. Ruling: index runs are isolated by run_id; switch one active run in a transaction only after source counts and version are confirmed.
- Kaon ZIP ↔ production architecture: local rank-bm25 JSON snapshots conflict with the approved PostgreSQL pg_search + pgvector design. Ruling: preserve Kaon source-validation/retry lessons and treat its rank-bm25 scores as an offline comparison baseline, not the serving index.
- Test constraint: no test files or test commands are included in this execution because the user requested integration, not testing/verification.

## Progress

- Task 1: complete — JSON Pointer is now the canonical `source_field`; the contract checker keeps bracket notation only as a migration aid. The service resolver also emits canonical JSON for numeric/boolean `details` leaves.
- Task 2: complete — bounded source pagination/retries, recursive `user_id` removal, version/count/linkage checks, and tokenizer-aware source chunking are in `src/toss_ads/rag/`.
- Task 3: complete as code — versioned PostgreSQL schema, restricted bootstrap role, BM25 index, vector storage/search, and atomic active-run switching are documented and implemented. DB extensions were not installed and no database connection was made.
- Task 4: complete as code — the CLI builds an isolated complete run and activates it only after source version/count checks. Full indexing was not run.
- Task 5: complete as code — hybrid BM25/vector retrieval, product-level RRF, the LangChain adapter, and FastAPI request/response boundary are implemented. No live search request was run.
- Task 6: complete — setup/runbook and the three-input integration decisions, including owner follow-ups, are documented.

## Final static review

- Python source compiled with `compileall`; JSON contract/evaluation files parsed successfully; `git diff --check` passed.
- No tests were added or run. No extension bootstrap, source full-index, live API request, or relevance evaluation was run.
- Numeric and boolean `details` values are represented with canonical JSON evidence, matching the existing Agent contract.

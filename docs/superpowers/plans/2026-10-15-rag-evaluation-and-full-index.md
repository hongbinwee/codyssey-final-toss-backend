# RAG Evaluation and Full Index Plan

> **For agentic workers:** Implement inline in the current Backend feature branch. Preserve all existing local changes and use TDD for code changes.

**Goal:** Reconcile the RAG-017 evaluation label with the category quarantine policy, independently recheck tuning/holdout labels, and index the user-selected Appliances category through a dedicated RAG staging database.

**Architecture:** Read the source snapshot only through the existing Amazon Reviews API. Index only the selected Appliances category (10,000 products and 65,618 reviews) into a new local staging PostgreSQL container with its own volume. Keep out-of-scope book products as policy-exclusion checks and separate them from relevance metrics.

**Tech Stack:** Python, FastAPI, HTTPX, Psycopg 3, FastEmbed, LangChain Core, PostgreSQL 18-compatible extension image, pgvector 0.8.7, ParadeDB pg_search 0.26.0.

**Spec:** `../specs/2026-10-15-rag-category-quarantine-design.md`; evaluation contract `../../../evals/amazon_reviews_rag_cases.json`.

## Global Constraints

- Never modify the source database; the index target must be a distinct database instance and volume.
- Read the source via the versioned, paginated API and require the full snapshot version/counts to stay stable for the whole run; index only Appliances for this run.
- Quarantine `1942191537` and linked reviews; do not increase evidence limits to return this out-of-scope book.
- Keep the source-grounded labels for all 20 questions, but score only Appliances search cases: 4 tuning and 4 holdout. Report other categories outside this index scope.
- Keep all label statuses pending team approval; independent source verification is not team approval.
- Do not set `RAG_MIN_RRF_SCORE` without team-approved positive and negative judgments.
- Do not store credentials, raw private user fields, or full source records in committed artifacts.

## Review Focus

- A policy-excluded product appears in active product or evidence search results.
- Tuning and holdout metrics accidentally count policy-only cases as relevance hits.
- An index run activates after a source version/count mismatch or partial failure.
- A review is attached to a product in another category or has a broken source identifier.
- A staging command accidentally targets the source database or exposes a credential.

## Rulings

- RAG-017 and RAG-018 target `1942191537`, which the category policy identifies as a Books product mislabeled under Clothing. Keep it out of retrieval and score those cases as policy-exclusion checks, not relevant-answer cases. Risk if wrong: valid book search behavior is no longer measured by these cases; the team's category policy must confirm this classification.
- The configured remote RAG endpoint is not reachable from this workspace. Use a separate localhost staging container with an independent volume for the requested indexing/evaluation; do not use the live source Postgres container. Risk if wrong: local staging results do not certify the team's eventual hosted RAG instance.
- No team reviewer is available through this task. Perform source-grounded independent review and leave team relevance approval pending. Risk if wrong: labels or thresholds remain unapproved for production decisions.

## Tasks

### Task 1: Separate policy exclusions from relevance scoring

**Files:** `scripts/rag_contracts.py`, `evals/amazon_reviews_rag_cases.json`, `tests/test_rag_contracts_evaluation.py`.

- [x] Add a failing test that a `policy_exclusion` case passes only if its excluded category/product is absent from response items and all returned evidence remains source-valid.
- [x] Add a failing test that policy-only cases do not inflate product/source-hit metrics for relevance cases.
- [x] Add a failing test that returning an excluded product makes the policy check fail.
- [x] Implement separate `policy_exclusion` accounting without weakening the existing response contract checks.
- [x] Mark RAG-017 and RAG-018 as policy exclusions while retaining their source-grounded labels for audit.
- [x] Run the targeted tests and the complete Backend test suite (27/27 passed).

### Task 2: Recheck source labels and freeze the evaluation manifest

**Files:** `reports/rag-contracts/label-review-2026-10-15.json`, `reports/rag-contracts/evaluation-manifest-2026-10-15.json`.

- [x] Revalidate all 20 case sources against the live read-only API and record the actual source version.
- [x] Record tuning 10 relevance + 2 policy checks and holdout 8 source labels; team approval remains pending.
- [x] Freeze the dataset version, chunker/token limit, embedding model, channel depth, RRF k, top_k, per-product evidence cap, and unset relevance threshold for provisional evaluation.

### Task 3: Provision a separate local RAG staging database

**Files:** no tracked credentials or source database changes; use a private temporary environment file and dedicated Docker volume.

- [x] Start an extension-enabled PostgreSQL container bound to localhost on a free port, with its own volume and `toss_rag` database.
- [x] Bootstrap the `rag` schema and restricted runtime role.
- [x] Verify server identity, extension versions, schema, and target before any indexing write.

### Task 4: Index the selected Appliances source scope

**Files:** `reports/rag-contracts/full-index-2026-10-15.json`.

- [x] Apply the user-approved privacy handling before writing full source rows: recursively remove explicit identity fields; same-length mask emails and SSN-format values, and phone values only when a strong contact label directly precedes them.
- [x] Resume the sanitized run with the explicit `Appliances` category scope.
- [x] Verify 10,000 source products and 65,618 source reviews for Appliances; record 10,000 products, 65,618 reviews, 287,105 evidence chunks, 0 orphans, and 0 quarantined rows. The run is active after successful indexing; failure injection was not performed.
- [x] Verify out-of-scope categories are absent from the active index through the explicit Appliances-only filter. This run has no separate quarantine-table rows because non-Appliances records were excluded before indexing; no claim of a quarantine-table write is made.

### Task 5: Run tuning, policy, and holdout evaluations

**Files:** `reports/rag-contracts/search-tuning-appliances-final-2026-10-15.json`, `reports/rag-contracts/search-holdout-appliances-final-2026-10-15.json`, `reports/rag-contracts/evaluation-manifest-2026-10-15.json`, `docs/rag-progress-2026-10-15.md`, `docs/rag-progress-share-2026-10-15.md`.

- [x] Run the 4 Appliances tuning questions; report the other 8 original tuning cases as outside this index scope (including 2 policy checks).
- [x] Run the 4 Appliances holdout questions after fixing the category-scoped manifest; report the other 4 as outside scope and keep thresholds unset. Results remain provisional because team labels are pending and an API ranking-contract adjustment followed an earlier exploratory holdout run.
- [x] Record actual API/index/search execution separately from source-only and unit-test checks.
- [x] Update progress documentation with verified outcomes, remaining team approvals, and environment scope.

## Final execution record — 2026-10-15

- Task 4 complete for the user-selected scope: Appliances only, 10,000 products and 65,618 reviews; 196,882 product chunks and 90,223 review chunks (287,105 total). The source snapshot remained stable, no other category was indexed, source DB writes were zero, and no orphan or quarantined rows were present. Since the run is category-scoped, out-of-scope records are absent by the category filter; there are no explicit quarantine rows in this run.
- User-approved privacy sanitizer was applied before writes. Post-index scan of 10,000 product payloads and 287,105 evidence/source metadata rows found zero remaining matches under that sanitizer.
- Task 5 complete as an execution task: 4 tuning + 4 holdout questions searched. Aggregate: products 7/8, exact expected source 4/8, cases passing 4/8, invalid evidence 0, 9 HTTP attempts with one successful retry after `database_failed`. The retry's PostgreSQL error was recorded as `InternalError_`, SQLSTATE `XX000`; root cause is unknown.
- All 8 in-scope Appliance labels are verified against the live source, but semantic/team approval remains pending. Holdout independence is provisional; no relevance threshold is set.
- Final run reports: `reports/rag-contracts/full-index-2026-10-15.json`, `reports/rag-contracts/search-tuning-appliances-final-2026-10-15.json`, `reports/rag-contracts/search-holdout-appliances-final-2026-10-15.json`.
- Latest complete Backend test suite before documentation-only updates: 38/38 passed.

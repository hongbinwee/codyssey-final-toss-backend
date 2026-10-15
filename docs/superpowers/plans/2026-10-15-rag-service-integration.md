# Amazon Reviews RAG Service Integration Plan

> **For agentic workers:** Implement this plan task by task in the current Backend feature branch. Keep the existing contract and evaluation artifacts reviewable throughout.

**Goal:** Combine the current chunking pilot, Kaon’s BM25 prototype findings, and the Agent contract/evaluation proposal into a runnable PostgreSQL hybrid RAG service in the Backend repository.

**Architecture:** Read the existing Amazon Reviews API without changing it, create source-grounded chunks, embed them with LangChain FastEmbed, and store versioned products/chunks in a dedicated PostgreSQL `rag` schema. Run ParadeDB BM25 and pgvector cosine retrieval independently, fuse product ranks with RRF, and expose the existing Agent request/response contract through FastAPI.

**Tech Stack:** Python, FastAPI, HTTPX, Psycopg 3, PostgreSQL 18.6, pgvector 0.8.7, ParadeDB pg_search 0.26.0, FastEmbed, LangChain Core and Community, JSON Schema 2020-12.

**Spec:** `../docs/superpowers/specs/2026-10-14-amazon-reviews-rag-design.md`; existing Agent proposal: `contracts/amazon-reviews-rag/v0.1/`.

## Global Constraints

- Preserve the existing Amazon Reviews API and read all source data through its paginated HTTP endpoints.
- Keep the BM25 + FastEmbed + LangChain / RRF architecture and the existing candidate defaults (20 per channel, RRF k=60, top_k 1–20, up to 3 evidence chunks per product).
- Keep `parent_asin`, `category`, `review_key`, `dataset_version`, source field, exact source offsets, and original evidence text linked end to end.
- Remove `user_id` recursively; never infer source currency or filter products by an unverified currency.
- Activate only complete index runs; failures preserve the prior active run.
- Do not generate answers, rewrite or translate queries, or add reranking in this integration.
- Keep the Agent request/response schemas and evaluation set marked as proposals pending DB and Agent owner review.

## Review Focus

- A source version change or partial source failure must not activate an incomplete run.
- A review with a missing or mismatched product must fail indexing rather than attach evidence to another product.
- A chunk must fit within the embedding model input budget and preserve exact source offsets.
- A request with punctuation or query-language operators must not become SQL text or expose database details.
- A missing price currency or uncalibrated relevance threshold must not be represented as verified.

## Integration Rulings

- Use the current chunker’s RFC 6901 JSON Pointer as the canonical `source_field`; update Agent examples and the checker. This differs from the earlier bracket-path examples, so keep it listed for Agent owner review.
- Keep Kaon’s `rank-bm25` JSON snapshot as a prototype/comparison artifact. PostgreSQL pg_search is the production BM25 engine under the already approved architecture; retain the prototype’s bounded retry and source validation lessons in the API client.
- Use the source API’s category-wide review pagination, then link reviews by `(category, parent_asin)`. This avoids issuing one request per product.
- The selected FastEmbed model has a 128-token input window. Split at no more than 96 tokenizer-counted tokens to leave room for title/field context; character counts alone are not sufficient.
- Do not set an uncalibrated low-relevance threshold. Make it optional and return `low_relevance` only when an explicitly configured threshold rejects all candidates.

## Plan Tasks

### Task 1: Canonicalize source paths and contract mapping

**Files:** `scripts/rag_contracts.py`, `contracts/amazon-reviews-rag/v0.1/README.md`, examples and evaluation fixtures.

- Make JSON Pointer the serialized response format and resolve object/list paths safely without evaluating expressions.
- Migrate existing bracket-path example values to JSON Pointer while preserving the existing request/response field names and status meanings.
- Map prototype `insufficient_evidence` to Agent `low_relevance` only through the configured relevance threshold.

### Task 2: Source client, types, and tokenizer-aware chunking

**Files:** `src/toss_ads/rag/{__init__,types,config,source,chunker}.py`, `requirements-rag-service.txt`.

- Port the current parent-repository evidence chunker and type contract into Backend.
- Add bounded HTTP retries, response-size limits, pagination/version checks, duplicate detection, and recursive `user_id` removal.
- Read every category’s products and reviews using the source API pagination contract.
- Split source strings with FastEmbed tokenizer counts; keep evidence offsets on original Unicode strings.

### Task 3: Isolated PostgreSQL schema and store

**Files:** `src/toss_ads/rag/store.py`, `src/toss_ads/rag/bootstrap.py`, `deploy/amazon-reviews-rag.sql`, `deploy/amazon-reviews-rag.env.example`.

- Create `rag.index_runs`, `rag.indexed_products`, and `rag.evidence_chunks` with run-scoped primary keys, provenance, JSONB metadata, and `vector(384)`.
- Add the version/product/source B-tree indexes, pg_search index, and exact pgvector cosine query path.
- Enforce one active run and switch the active run atomically after full verification.
- Keep the runtime role scoped to `rag`; bootstrap credentials are separate from `RAG_DATABASE_URL`.

### Task 4: Complete versioned ingestion command

**Files:** `src/toss_ads/rag/embeddings.py`, `src/toss_ads/rag/indexer.py`, `src/toss_ads/rag/__main__.py`.

- Embed and upsert bounded batches, preserving product/review linkage and deterministic chunk IDs.
- Verify source version and expected API counts before activation; persist safe failure codes and leave the prior active run untouched.
- Keep raw prices as provided and `price_currency` null unless the source explicitly supplies a currency.

### Task 5: Hybrid retrieval, LangChain adapter, and Agent API

**Files:** `src/toss_ads/rag/retriever.py`, `src/toss_ads/rag/api.py`, `src/toss_ads/rag/schemas.py`.

- Retrieve up to 20 chunk candidates from each channel, rank products by their best channel ranks, and fuse with RRF k=60.
- Return at most `top_k` distinct products and 3 non-duplicate evidence chunks per product.
- Implement LangChain `Document` output and a `BaseRetriever` adapter without storing prompts or evidence text in logs.
- Return `ok`, `no_results`, `low_relevance`, or safe `error` codes in the existing response shape.
- Do not apply unsupported price/feature preferences as hard filters; report them under `unverified_conditions`.

### Task 6: Runbook and integration review record

**Files:** `README.md`, `docs/amazon-reviews-rag-contracts.md`, `docs/common-work-rules.md`, `docs/rag-progress-2026-10-15.md`, `docs/rag-integration-decisions.md`.

- Document setup, schema bootstrap, full index, API launch, request example, model cache, and current limitations.
- Record the contributions and boundaries of the three artifacts and the DB/Agent decisions still needing owner review.
- Keep the retrieval threshold explicitly uncalibrated until tuning and holdout judgments are approved.

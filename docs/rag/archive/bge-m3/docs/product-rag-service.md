# Product RAG Service

The service exposes source-grounded hybrid search over the active product/review index.

## Runtime

- Search API: `http://127.0.0.1:8002`
- `GET /healthz`: active index and supported categories
- `POST /v1/rag/search`: hybrid product and evidence retrieval
- Active dataset: `test_items`, category `beauty`
- Database: PostgreSQL `toss_rag`, schema `rag`

The query is embedded in memory for vector retrieval. BM25 and vector search read the already-indexed chunks. The request embedding is not stored as a separate record.

## Indexing

Indexing reads the configured product source API, splits product and review text into bounded evidence chunks, embeds those chunks, and stores their provenance and vectors in PostgreSQL. The active search API reads the completed index.

Runtime configuration is documented in [the environment example](../deploy/product-rag-runtime.env.example). Database bootstrap configuration is in [the bootstrap example](../deploy/product-rag-bootstrap.env.example).

## Quality status

The current beauty index passed exact stored-title smoke queries. Natural-language intent queries showed lower top-1 precision in an exploratory eight-query review. Labels were derived from product-title keywords and have not been approved by human reviewers, so the results are not a formal accuracy score. See the [current review](../../docs/rag-search-quality-test-items-beauty-2026-10-17.md).

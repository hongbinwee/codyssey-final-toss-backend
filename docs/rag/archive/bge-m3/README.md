# Product RAG Backend

Backend implementation for the Toss Ads project. The RAG service indexes product and review records, stores source-grounded chunks and embeddings in PostgreSQL, and serves hybrid BM25/vector search.

## Current search data

- Dataset: `test_items`
- Category: `beauty`
- API: `http://127.0.0.1:8002`
- Search quality notes: [current `test_items/beauty` review](../docs/rag-search-quality-test-items-beauty-2026-10-17.md)

## Main components

- `src/toss_ads/rag/source.py`: bounded source API client
- `src/toss_ads/rag/indexer.py`: source snapshot indexing and activation
- `src/toss_ads/rag/chunker.py`: token-bounded evidence chunks with offsets
- `src/toss_ads/rag/retriever.py`: BM25 and vector retrieval with rank fusion
- `src/toss_ads/rag/api.py`: search and health endpoints
- `deploy/product-rag.sql`: PostgreSQL schema
- `deploy/product-rag-runtime.env.example`: serving and source configuration
- `deploy/product-rag-bootstrap.env.example`: database bootstrap configuration

The historic evaluation cases and their reports were removed when the project moved to `test_items/beauty`. Current search measurements are exploratory and do not have a human-approved gold set yet.

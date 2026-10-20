# Product RAG Service

The service exposes source-grounded hybrid search over the active product/review index.

- Search endpoint: `POST /v1/rag/search`
- Health endpoint: `GET /healthz`
- Database schema: `rag`
- Indexer sources: pinned Commerce fixtures, read-only Commerce database, or a configured product source API

Product and review records are joined by `product_id`. The index stores product/review text, evidence offsets, source metadata, and document embeddings. A query embedding is calculated in memory and is not stored as a separate row.

Runtime settings are in [the environment example](../deploy/product-rag-runtime.env.example). Bootstrap settings are in [the bootstrap example](../deploy/product-rag-bootstrap.env.example).

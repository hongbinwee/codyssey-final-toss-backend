# Product RAG Backend

Backend implementation for product and review search in the Toss Ads project. The active RAG profile is `all_products`, backed by the `test_items` snapshot and the `beauty` category.

The service stores source-grounded evidence chunks and document embeddings in PostgreSQL, then serves hybrid BM25/vector retrieval. The live query embedding is computed in memory and is not stored as a separate record.

See [Product RAG service](docs/product-rag-service.md), [RAG catalog profiles](docs/superpowers/specs/2026-10-17-rag-catalog-profiles-design.md), and the `rag-performance-evaluation-2026-10-17` reports for current exploratory quality notes.

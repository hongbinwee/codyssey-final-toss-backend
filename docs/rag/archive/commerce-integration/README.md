# Product RAG Integration

RAG backend for product and review search in the Toss Ads project.

The current integration supports the Commerce demo from pinned fixtures or a read-only Commerce database. Both sources use the shared product/review indexing pipeline, which stores token-bounded evidence chunks and vectors in PostgreSQL and serves hybrid BM25/vector retrieval.

See [Commerce RAG demo operations](docs/commerce-rag-demo.md) and [current RAG direction](docs/rag-overall-direction.md).

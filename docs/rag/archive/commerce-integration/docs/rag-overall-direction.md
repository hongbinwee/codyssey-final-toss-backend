# RAG Search Direction

The RAG API returns product candidates and source evidence. It does not make the final recommendation or policy decision.

## Indexing

The indexer reads a configured product source, validates product/review links by `product_id`, creates bounded evidence chunks, and stores text, provenance, and embeddings in PostgreSQL. It activates a new dataset only after indexing finishes successfully.

Supported source adapters in this worktree are the pinned Commerce fixtures and a read-only Commerce database. The source API adapter is generic and is only used when a product source API URL is configured.

## Search

1. Embed the query in memory.
2. Retrieve candidate chunks with BM25 and vector similarity.
3. Combine product ranks with Reciprocal Rank Fusion.
4. Return product candidates with excerpts and source pointers.

Search ranking scores are not calibrated probabilities. Quality reporting requires human-approved relevance labels and a separate holdout set.

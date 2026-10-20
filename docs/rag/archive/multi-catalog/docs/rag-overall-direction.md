# RAG Search Direction

The active profile is `all_products`, with the current `test_items` snapshot in the `beauty` category. The API returns product candidates and source evidence. Final recommendations and policy decisions belong to a separate layer.

The indexer reads a configured product source, joins reviews by `product_id`, creates bounded evidence chunks, and stores text, provenance, and vectors in PostgreSQL. Search combines BM25 and vector candidates with Reciprocal Rank Fusion.

Ranking scores are not calibrated probabilities. The current exploratory measurements are in the 2026-10-17 performance reports; their keyword-derived labels are not a human-approved gold set.

# BGE-M3 Full-Dataset Operations

Updated: 2026-10-20

## Active configuration

- Dataset: `test_items2`, 1,500 products and 46,100 reviews.
- Active run: `e925490f-4f34-4c03-9248-eb9ebdfcde48`.
- Dataset version: `test_items2:v6.1-review-refined:sha256=94681a28271ca9b1:products=1500:reviews=46100`.
- Categories: `beauty`, `fashion`, `food`, and `living`.
- BGE profile: `BAAI/bge-m3`, revision `5617a9f61b028005a4858fdac845db406aefb181`, 1,024 dimensions, 128-token input limit, scope `*`, 114,106 vectors.
- Search: BM25 plus BGE-M3 dense retrieval, combined with product-level RRF (`k=60`). BGE sparse and ColBERT channels are off.
- MiniLM's 114,106 vectors remain stored for rollback.
- Database operations are restricted to `127.0.0.1:5432/toss_rag`.

## Runtime checks

The local API listens at `http://127.0.0.1:8002`.

- Health: `GET /healthz` should report `ok` and the active dataset version.
- Search: `POST /v1/rag/search` supports category filters for the four categories and an unfiltered request across all categories.
- The activation record lists the checks performed and the expected per-category vector counts: [full-dataset index report](../reports/rag-bge-m3-test-items2-full-2026-10-20-index.json).

These requests confirm the service responds and the profile is ready. They do not measure search accuracy. Beauty has 10 positive and 2 out-of-distribution fixture queries whose labels have not been human-reviewed; fashion, food, and living have no approved labels.

## Roll back to MiniLM

The stopped container `product-rag-api-minilm-rollback-20261020` preserves the prior MiniLM runtime. To restore it locally:

1. Stop the active `product-rag-api` container.
2. Start `product-rag-api-minilm-rollback-20261020`.
3. Check `http://127.0.0.1:8002/healthz` and run a beauty search.

This switches the service runtime only. Keep the BGE profile and vector rows in the database so BGE can be restored without re-embedding.

# Product RAG Service

The service exposes source-grounded hybrid search over the active product/review index.

## Runtime

- Search API: `http://127.0.0.1:8002`
- `GET /healthz`: active index and supported categories
- `POST /v1/rag/search`: hybrid product and evidence retrieval
- Dataset target: `test_items2`, all 1,500 products and 46,100 reviews
- Categories: `beauty`, `fashion`, `food`, and `living`
- Target run: `e925490f-4f34-4c03-9248-eb9ebdfcde48`
- Target dataset version: `test_items2:v6.1-review-refined:sha256=94681a28271ca9b1:products=1500:reviews=46100`
- Target chunk count: 114,106
- Database: PostgreSQL `toss_rag`, schema `rag`

The target search combines the existing BM25 channel with BGE-M3 dense vectors and product-level reciprocal rank fusion (`k=60`). The active run keeps its MiniLM vectors for rollback; BGE-M3 vectors live in the separate `rag.evidence_chunk_embeddings` table. BGE-M3 uses the pinned revision `5617a9f61b028005a4858fdac845db406aefb181`, 1,024 dimensions, and a 128-token input limit. Sparse and ColBERT outputs are disabled.

The query embedding stays in memory for vector retrieval and is not stored. The BGE-M3 cache is persistent at `BGE_M3_CACHE_PATH`, defaulting beneath `FASTEMBED_CACHE_PATH`.

## Indexing

Indexing reads the configured product source API, splits product and review text into bounded evidence chunks, embeds those chunks, and stores their provenance and vectors in PostgreSQL. The active search API reads the completed index.

Runtime configuration is documented in [the environment example](../deploy/product-rag-runtime.env.example). Database bootstrap configuration is in [the bootstrap example](../deploy/product-rag-bootstrap.env.example).

The environment example keeps MiniLM as its default. Set `RAG_EMBEDDING_MODEL=BAAI/bge-m3` for the local service only after the full `*` profile reports `ready` with all 114,106 vectors. A partial profile must leave the service on MiniLM.

## Local activation and rollback

1. Recheck the active run, dataset version, four category chunk counts, and BGE profile counts in `5432/toss_rag`. Keep the existing MiniLM container and its configuration available.
2. Read the existing container configuration into process memory. Reuse its environment, host networking, and cache bind mount; do not print or save secret values. Build the image from `deploy/product-rag.Dockerfile`.
3. Start a temporary BGE-M3 validation container on host port `8003`. Copy the existing environment and cache mount, overriding only `RAG_EMBEDDING_MODEL=BAAI/bge-m3` and the serve port. Keep the copied database credential in memory.
4. Check `/healthz`, then run category-filtered searches for each of the four categories and one unfiltered search. Switch only when health is `ok` and all checks return successfully.
5. Preserve the MiniLM container under a rollback name, then start the BGE-M3 service on port `8002` with the same runtime configuration.
6. For rollback, stop the BGE-M3 container and restart the saved MiniLM container with its original configuration. Keep all BGE vectors in the database.

This sequence is an operational smoke check. It does not establish search accuracy.

## Quality status

The existing beauty comparison has 10 positive queries and 2 out-of-distribution queries. Fashion, food, and living have no approved evaluation labels. Operational smoke checks across all four categories do not measure retrieval accuracy. See the [beauty-only comparison](./rag-bge-m3-test-items2-beauty-2026-10-20.md).

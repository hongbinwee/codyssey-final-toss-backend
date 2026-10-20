# Product RAG Service

The service exposes source-grounded hybrid search over the active product/review index.

- Search endpoint: `POST /v1/rag/search`
- Health endpoint: `GET /healthz`
- Active profile: `all_products`
- Current category: `beauty`
- Database schema: `rag`

Product and review records are connected by `product_id`. Indexed chunks retain their source fields, offsets, and product IDs. Query vectors are calculated in memory and are not stored separately.

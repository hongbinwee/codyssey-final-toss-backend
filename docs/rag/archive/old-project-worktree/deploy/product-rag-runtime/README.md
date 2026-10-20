# LangChain HTTP retrieval

The search endpoint uses this path:

```text
POST /v1/rag/search
  -> HybridRagRetriever.search(RagSearchRequest)
  -> request-scoped BaseRetriever.invoke(query, config)
  -> _get_relevant_documents()
  -> hybrid_search()
```

`search()` preserves the complete HTTP result, including request ID, category,
requested result count, dataset version, evidence, unverified conditions and
error status. Each call creates its own request scope; the shared store and
embedder do not hold request-specific state. The standard `invoke()` interface
returns LangChain Documents and raises SearchError on retrieval errors. An
empty search and low relevance retain their distinct HTTP statuses.

RunnableConfig callbacks can be passed to `search()` for LangChain tracing.
The `toss_ads.rag.retriever` logger records start/result events with request IDs,
without query text or database credentials.

The deployed test_items dataset, beauty category restrictions, simulated prices
and retrieval/ranking policy are preserved. This wiring does not add mandatory
spec filtering or improve relevance scores by itself.

Run the complete runtime regression suite without database or model access:

```sh
docker run --rm --network none \
  --mount type=bind,source="$PWD",target=/workspace,readonly \
  --env PYTHONPATH=/workspace/src --entrypoint python \
  toss-ads-product-rag-service:2026-10-17-compat \
  -m unittest discover -s /workspace/tests -v
```

Build using the current deployed image tag as the dependency base:

```sh
docker build -f Dockerfile.runtime \
  --build-arg RAG_BASE_IMAGE="$(docker inspect --format '{{.Config.Image}}' product-rag-api)" \
  -t toss-ads-product-rag-service:2026-10-18-langchain-http .
```

Deployment must retain the existing container environment and its connection
to PostgreSQL on port 5432, database toss_rag. Preview a replacement on a
separate API port and compare responses before switching the existing 8002
service. Keep the stopped previous container until the replacement is healthy.

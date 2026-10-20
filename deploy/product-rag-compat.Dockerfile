# Reuse the already installed/pinned BGE runtime dependencies and model cache.
ARG RAG_BASE_IMAGE=toss-ads-product-rag-service:rag-bge-m3-full-test-items2-252bc90
FROM ${RAG_BASE_IMAGE}
COPY src/toss_ads/rag /app/src/toss_ads/rag

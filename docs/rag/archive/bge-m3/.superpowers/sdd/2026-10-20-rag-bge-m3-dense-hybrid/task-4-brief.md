### Task 4: BM25·dense·hybrid 비교 검색

**Files:**
- Create: `src/toss_ads/rag/comparison.py`
- Test: `tests/test_rag_comparison.py`

**Interfaces:**
- `search_products(store, embedder, *, run_id: str, query: str, mode: Literal["bm25", "hybrid", "dense"], category: str, channel_depth: int = 20, rrf_k: int = 60) -> list[dict[str, Any]]`를 제공한다.
- BM25는 `search_bm25`, dense는 BGE query embedding과 `search_embedding_vector`, hybrid는 두 채널의 top 20을 받아 상품별 첫 chunk 순위를 각각 사용한 RRF로 정렬한다.
- 이 모듈은 오프라인 비교용이다. 기존 `hybrid_search()`와 API 기본 설정은 바꾸지 않는다.

- [ ] **Step 1: 실패하는 검색 모드 테스트 작성** — BM25 mode가 임베더를 호출하지 않는지, dense mode가 BM25를 호출하지 않는지, hybrid mode가 둘 다 호출하고 `k=60` 상품 단위 RRF를 적용하는지 테스트한다. 동일 상품의 다중 chunk는 한 번만 순위에 반영한다.
- [ ] **Step 2: 테스트가 실패하는지 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_comparison.py'`

  Expected: 비교 검색 함수가 없어 실패한다.

- [ ] **Step 3: 모드별 검색과 상품 deduplication 구현** — 각 채널은 최대 20개 chunk를 가져오고, 제품 순위는 해당 채널 내 첫 chunk 순위로 계산한다. hybrid는 두 채널 순위를 `1 / (60 + rank)`로 합산하고 동점은 category와 product ID로 결정한다.
- [ ] **Step 4: 검색 모드 테스트 통과 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_comparison.py'`

  Expected: BM25 미호출·dense 미호출·RRF·중복 제거 테스트 PASS.

- [ ] **Step 5: 커밋** — 이 task의 두 파일만 스테이징한다.

  Commit: `feat: compare BM25 and BGE-M3 retrieval modes`


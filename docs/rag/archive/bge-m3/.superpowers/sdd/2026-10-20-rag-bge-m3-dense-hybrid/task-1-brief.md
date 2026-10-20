### Task 1: BGE-M3 dense 임베딩 어댑터

**Files:**
- Create: `src/toss_ads/rag/bge_m3.py`
- Modify: `requirements-rag-service.txt`
- Modify: `deploy/product-rag.Dockerfile`
- Test: `tests/test_rag_bge_m3_embeddings.py`

**Interfaces:**
- Produces `BgeM3Embedder(model_name: str = "BAAI/bge-m3", max_length: int = 128, batch_size: int = 16, *, model: Any | None = None, model_revision: str | None = None)`. The last two keyword arguments inject a fake model and revision in unit tests.
- `BgeM3Embedder.embed_documents(texts: Sequence[str]) -> list[list[float]]`, `embed_query(text: str) -> list[float]`, `dimension: int = 1024`, `model_revision: str`를 제공한다. `model_revision`은 실제 로드한 Hugging Face snapshot commit이다.
- 기존 `create_embedder()`와 FastEmbed 설정은 수정하지 않는다. 테스트는 생성자에 fake `BGEM3FlagModel`을 주입한다.

- [ ] **Step 1: 실패하는 어댑터 테스트 작성** — `test_embed_documents_returns_dense_vectors_in_input_order`, `test_embed_query_uses_dense_output_only`, `test_rejects_wrong_dimension`, `test_empty_document_list_does_not_call_model`을 추가한다. sparse/ColBERT 반환값이 있어도 `dense_vecs`만 반환하고, 문서 입력 순서가 유지되며, 길이가 1,024가 아니면 `ValueError("embedding_dimension_mismatch")`가 나는지 고정한다.
- [ ] **Step 2: 테스트가 실패하는지 확인**

  Run: `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_rag_bge_m3_embeddings.py'`

  Expected: 새 어댑터가 없어 실패한다.

- [ ] **Step 3: `BgeM3Embedder` 구현** — `FlagEmbedding.BGEM3FlagModel`을 CPU 모드로 초기화하고 `encode(..., max_length=128, return_dense=True, return_sparse=False, return_colbert_vecs=False)["dense_vecs"]`만 사용한다. 빈 문서 목록은 빈 결과를 반환하고, 모델 로드·인코딩 예외를 숨기지 않는다.
- [ ] **Step 4: CPU 실행 의존성과 컨테이너 설정 추가** — `requirements-rag-service.txt`에 FlagEmbedding 의존성을 추가하고, Docker 이미지가 CPU 추론에 필요한 패키지를 설치하도록 한다. 기존 FastEmbed 의존성은 유지한다.
- [ ] **Step 5: 어댑터 테스트 통과 확인**

  Run: `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_rag_bge_m3_embeddings.py'`

  Expected: 4개 테스트 PASS.

- [ ] **Step 6: 커밋** — `tests/test_rag_bge_m3_embeddings.py`, `src/toss_ads/rag/bge_m3.py`, `requirements-rag-service.txt`, `deploy/product-rag.Dockerfile`만 스테이징한다.

  Commit: `feat: add BGE-M3 dense embedding adapter`


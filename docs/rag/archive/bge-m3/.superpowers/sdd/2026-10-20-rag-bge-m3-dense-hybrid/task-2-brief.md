### Task 2: 추가 임베딩 프로필·벡터 저장소

**Files:**
- Create: `deploy/product-rag-bge-m3-embeddings.sql`
- Modify: `src/toss_ads/rag/store.py`
- Test: `tests/test_rag_embedding_store.py`

**Interfaces:**
- SQL은 `rag.index_run_embedding_profiles`와 `rag.evidence_chunk_embeddings`를 생성한다. 프로필 키는 `(run_id, embedding_model)`이며 `model_revision`, `dimension`, `max_input_tokens`, `category_scope`, `status`, `chunk_count`를 기록한다. 이번 프로필 범위는 `beauty`다.
- `RagStore.register_embedding_profile(*, run_id: str, embedding_model: str, model_revision: str, dimension: int, max_input_tokens: int, category_scope: str, expected_chunk_count: int) -> None`을 추가한다. 기존 프로필과 revision·dimension·scope가 다르면 덮어쓰지 않고 실패한다.
- `RagStore.missing_embedding_texts(run_id: str, embedding_model: str, category: str, limit: int) -> tuple[tuple[str, str], ...]`는 `(chunk_id, embedding_text)`를 반환한다. `upsert_embedding_vectors(run_id: str, embedding_model: str, rows: Sequence[tuple[str, Sequence[float]]]) -> None`은 벡터를 저장한다.
- `RagStore.embedding_profile_counts(run_id: str, embedding_model: str, category: str) -> tuple[int, int]`은 `(expected_chunk_count, stored_vector_count)`를 반환한다. `mark_embedding_profile_ready(run_id: str, embedding_model: str, category: str) -> None`은 두 수가 일치할 때만 성공한다.
- `RagStore.mark_embedding_profile_failed(run_id: str, embedding_model: str) -> None`은 중단된 프로필을 `failed`로 표시하고 저장된 벡터를 유지해 Task 3에서 재개할 수 있게 한다.
- `RagStore.search_embedding_vector(run_id: str, embedding_model: str, vector: Sequence[float], limit: int, category: str | None = None, source_type: str | None = None) -> list[dict[str, Any]]`는 해당 모델 프로필의 `ready` 벡터만 검색한다.

- [ ] **Step 1: 실패하는 store 경계 테스트 작성** — 차원 1,023/1,025 벡터 거부, 같은 `(run_id, chunk_id, embedding_model)` upsert 중복 방지, run·model·category 범위 제한, 프로필의 총 청크 수와 저장 벡터 수 확인, 실패 상태에서도 저장 벡터가 유지되는지 테스트한다. DB 호출은 fake connection으로 검증한다.
- [ ] **Step 2: 테스트가 실패하는지 확인**

  Run: `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_rag_embedding_store.py'`

  Expected: 새 store 메서드가 없어 실패한다.

- [ ] **Step 3: additive DDL 작성** — 프로필은 `rag.index_runs(run_id)`를 참조하고 `dimension=1024`, `status IN ('building', 'ready', 'failed')`를 제한한다. 벡터 행은 프로필과 `rag.evidence_chunks(run_id, chunk_id)`를 외래 키로 참조하고, 키는 `(run_id, chunk_id, embedding_model)`, 열 타입은 `vector(1024)`로 둔다. 모든 생성 구문은 재실행 가능한 `IF NOT EXISTS`로 쓴다.
- [ ] **Step 4: 프로필 등록·누락 청크 조회·벡터 upsert·완료 수 확인 구현** — 각 배치에서 `embedding_text`와 `chunk_id`만 읽고, 입력 차원과 카테고리 범위를 쓰기 전에 검증한다. 프로필은 대상 청크 전부가 저장됐을 때만 `ready`로 바꾼다.
- [ ] **Step 5: 별도 임베딩 테이블 dense 검색 구현** — run/model/category/source_type을 모두 SQL 필터로 적용하고 cosine 거리 오름차순으로 결과를 반환한다. 벡터가 1,024차원이 아니면 SQL 실행 전에 거부한다.
- [ ] **Step 6: store 테스트 통과 확인**

  Run: `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_rag_embedding_store.py'`

  Expected: 저장·재조회·범위·차원 테스트 PASS.

- [ ] **Step 7: 커밋** — 이 task의 세 파일만 스테이징한다.

  Commit: `feat: store model-specific RAG embeddings`


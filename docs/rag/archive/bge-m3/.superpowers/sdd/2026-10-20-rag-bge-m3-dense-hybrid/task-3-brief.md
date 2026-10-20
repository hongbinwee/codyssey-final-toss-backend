### Task 3: 기존 beauty 청크 재임베딩 CLI

**Files:**
- Create: `src/toss_ads/rag/embedding_indexer.py`
- Modify: `src/toss_ads/rag/__main__.py`
- Test: `tests/test_rag_embedding_indexer.py`

**Interfaces:**
- `index_existing_chunks(store, embedder, *, run_id: str, dataset_version: str, category: str, batch_size: int = 16) -> EmbeddingIndexSummary`를 제공한다. Summary 필드는 `run_id`, `dataset_version`, `category`, `embedding_model`, `model_revision`, `total_chunk_count`, `embedded_chunk_count`, `elapsed_seconds`, `chunks_per_second`, `model_load_seconds`, `max_rss_mb`, `status`다.
- CLI 명령은 `env PYTHONPATH=src .venv/bin/python -m toss_ads.rag embed-model --run-id ... --dataset-version ... --category beauty --batch-size 16 --summary-output reports/rag-bge-m3-test-items2-beauty-2026-10-20-index.json`이다. 모델은 `BAAI/bge-m3`, 최대 입력 길이는 128로 고정한다.
- 기존 `index`와 `serve` 동작, `index_dataset()`의 새 run 생성·활성화 흐름은 수정하지 않는다.

- [ ] **Step 1: 실패하는 재임베딩 테스트 작성** — 대상 메타데이터가 일치하면 누락 청크만 16개 이하 배치로 임베딩하고, 이미 저장된 벡터는 건너뛰며, 모든 청크 완료 후 프로필을 `ready`로 표시하는 fake store 테스트를 작성한다. run/dataset/category 불일치는 embedder 호출과 쓰기 전에 실패해야 한다.
- [ ] **Step 2: 테스트가 실패하는지 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_embedding_indexer.py'`

  Expected: 새 모듈과 CLI 명령이 없어 실패한다.

- [ ] **Step 3: 재개 가능한 임베딩 루프 구현** — 배치마다 `missing_embedding_texts()`를 사용하고 결과를 즉시 upsert한다. 실패 시 프로필을 `failed`로 기록하되 저장된 벡터는 유지하여 같은 명령 재실행 시 누락분만 처리한다. 입력 텍스트는 DB의 기존 `embedding_text` 그대로 사용한다.
- [ ] **Step 4: CLI와 사전 검증 추가** — `--run-id`, `--dataset-version`, `--category`를 필수로 받고, 프로필과 run 메타데이터가 일치하지 않으면 작업을 중단한다. source API 호출이나 active run 변경은 하지 않는다.
- [ ] **Step 5: 재임베딩 테스트 통과 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_embedding_indexer.py'`

  Expected: 사전 중단, 누락분 재개, 완료 상태 테스트 PASS.

- [ ] **Step 6: 커밋** — 이 task의 세 파일만 스테이징한다.

  Commit: `feat: re-embed existing RAG chunks with BGE-M3`


# BGE-M3 Dense + BM25 Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 기존 `test_items2/beauty` 청크를 다시 만들지 않고 BGE-M3 벡터를 추가해 BM25 단독, BM25+BGE-M3, BGE-M3 dense 단독을 같은 질의로 비교한다.

**Architecture:** FastEmbed와 MiniLM 384차원 인덱스는 그대로 두고, BGE-M3용 임베더와 별도 1,024차원 저장 테이블을 추가한다. 대상 run의 기존 `embedding_text`만 재임베딩하고, 비교 전용 검색 경로에서 세 구성을 평가한다. 서비스 기본 검색과 활성 run은 바꾸지 않는다.

**Tech Stack:** Python 3.12, FlagEmbedding `BGEM3FlagModel`, PostgreSQL 16/pgvector, ParadeDB BM25, `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-20-rag-bge-m3-dense-hybrid-design.md`

## Global Constraints

- DB는 `5432/toss_rag`만 사용하고 `15436`에는 연결하지 않는다.
- BGE-M3 dense 벡터는 1,024차원이며 첫 비교의 입력 길이는 128 토큰으로 고정한다.
- 기존 `source-evidence-token-v2:max_tokens=96` 청크와 `embedding_text`를 그대로 사용한다. 이 작업에서는 재청킹하지 않는다.
- 기존 `rag.evidence_chunks.embedding vector(384)`, MiniLM 벡터와 현재 활성 서비스 설정을 보존한다.
- DB 변경은 새 테이블과 BGE-M3 벡터 행 추가로 제한한다. 기존 테이블의 MiniLM 열을 바꾸거나 데이터를 삭제하지 않는다.
- 비교 대상은 BM25 단독, BM25+BGE-M3 dense(RRF `k=60`), BGE-M3 dense 단독이다. BGE-M3 sparse/ColBERT, 리랭커, 답변 생성 모델은 포함하지 않는다.
- 평가 질의 10개와 OOD 질의 2개를 동일하게 사용한다. 규칙으로 만든 현재 라벨은 탐색용이므로 보고서에 라벨 한계를 표시한다.
- 비교 완료만으로 서비스 모델이나 활성 인덱스를 자동 전환하지 않는다.
- 단위 테스트와 로컬 평가 명령은 저장소별 `.venv/bin/python` 환경에서 실행한다. `.venv`는 Git에 커밋하지 않는다.

## Review Focus

- run ID·데이터 버전·카테고리가 기대값과 다르면 임베딩이나 DB 쓰기 전에 중단한다. (Task 3 테스트)
- 일부 벡터만 저장된 작업을 재개하면 완료 벡터는 건너뛰고 누락된 `beauty` 청크만 처리한다. (Task 3 테스트)
- 임베딩 차원이 1,024가 아니거나 프로필 차원이 요청 벡터와 다르면 쓰기와 검색을 거부한다. (Task 1·2 테스트)
- dense 단독은 BM25를 호출하지 않고, hybrid만 `k=60`의 상품 단위 RRF를 적용한다. (Task 4 테스트)
- OOD 질의의 반환 수를 별도 기록하고, 라벨이 비어 있다는 이유로 안전한 거절 동작이나 정확도를 주장하지 않는다. (Task 5 테스트)

---

### Task 1: BGE-M3 dense 임베딩 어댑터

**Files:**
- Create: `src/toss_ads/rag/bge_m3.py`
- Modify: `requirements-rag-service.txt`
- Modify: `deploy/product-rag.Dockerfile`
- Test: `tests/test_rag_bge_m3_embeddings.py`

**Interfaces:**
- Produces `BgeM3Embedder(model_name: str = "BAAI/bge-m3", max_length: int = 128, batch_size: int = 16, *, model: Any | None = None, model_revision: str | None = None, revision: str | None = None)`. `model`/`model_revision` inject a fake in unit tests; `revision` pins a real Hugging Face snapshot for reproducible query encoding.
- `BgeM3Embedder.embed_documents(texts: Sequence[str]) -> list[list[float]]`, `embed_query(text: str) -> list[float]`, `dimension: int = 1024`, `model_revision: str`를 제공한다. `model_revision`은 실제 로드한 Hugging Face snapshot commit이다.
- 기존 `create_embedder()`와 FastEmbed 설정은 수정하지 않는다. 테스트는 생성자에 fake `BGEM3FlagModel`을 주입한다.

- [x] **Step 1: 실패하는 어댑터 테스트 작성** — `test_embed_documents_returns_dense_vectors_in_input_order`, `test_embed_query_uses_dense_output_only`, `test_rejects_wrong_dimension`, `test_empty_document_list_does_not_call_model`을 추가한다. sparse/ColBERT 반환값이 있어도 `dense_vecs`만 반환하고, 문서 입력 순서가 유지되며, 길이가 1,024가 아니면 `ValueError("embedding_dimension_mismatch")`가 나는지 고정한다.
- [x] **Step 2: 테스트가 실패하는지 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_bge_m3_embeddings.py'`

  Expected: 새 어댑터가 없어 실패한다.

- [x] **Step 3: `BgeM3Embedder` 구현** — `FlagEmbedding.BGEM3FlagModel`을 CPU 모드로 초기화하고 `encode(..., max_length=128, return_dense=True, return_sparse=False, return_colbert_vecs=False)["dense_vecs"]`만 사용한다. 빈 문서 목록은 빈 결과를 반환하고, 모델 로드·인코딩 예외를 숨기지 않는다.
- [x] **Step 4: CPU 실행 의존성과 컨테이너 설정 추가** — `requirements-rag-service.txt`에 FlagEmbedding 의존성을 추가하고, Docker 이미지가 CPU 추론에 필요한 패키지를 설치하도록 한다. 로컬 평가용 `.venv`도 만들고 CPU PyTorch 및 service requirements를 설치한다. 기존 FastEmbed 의존성은 유지한다.
- [x] **Step 5: 어댑터 테스트 통과 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_bge_m3_embeddings.py'`

  Expected: 4개 테스트 PASS.

- [x] **Step 6: 커밋** — `tests/test_rag_bge_m3_embeddings.py`, `src/toss_ads/rag/bge_m3.py`, `requirements-rag-service.txt`, `deploy/product-rag.Dockerfile`만 스테이징한다.

  Commit: `feat: add BGE-M3 dense embedding adapter`

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

- [x] **Step 1: 실패하는 store 경계 테스트 작성** — 차원 1,023/1,025 벡터 거부, 같은 `(run_id, chunk_id, embedding_model)` upsert 중복 방지, run·model·category 범위 제한, 프로필의 총 청크 수와 저장 벡터 수 확인, 실패 상태에서도 저장 벡터가 유지되는지 테스트한다. DB 호출은 fake connection으로 검증한다.
- [x] **Step 2: 테스트가 실패하는지 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_embedding_store.py'`

  Expected: 새 store 메서드가 없어 실패한다.

- [x] **Step 3: additive DDL 작성** — 프로필은 `rag.index_runs(run_id)`를 참조하고 `dimension=1024`, `status IN ('building', 'ready', 'failed')`를 제한한다. 벡터 행은 프로필과 `rag.evidence_chunks(run_id, chunk_id)`를 외래 키로 참조하고, 키는 `(run_id, chunk_id, embedding_model)`, 열 타입은 `vector(1024)`로 둔다. 모든 생성 구문은 재실행 가능한 `IF NOT EXISTS`로 쓴다.
- [x] **Step 4: 프로필 등록·누락 청크 조회·벡터 upsert·완료 수 확인 구현** — 각 배치에서 `embedding_text`와 `chunk_id`만 읽고, 입력 차원과 카테고리 범위를 쓰기 전에 검증한다. 프로필은 대상 청크 전부가 저장됐을 때만 `ready`로 바꾼다.
- [x] **Step 5: 별도 임베딩 테이블 dense 검색 구현** — run/model/category/source_type을 모두 SQL 필터로 적용하고 cosine 거리 오름차순으로 결과를 반환한다. 벡터가 1,024차원이 아니면 SQL 실행 전에 거부한다.
- [x] **Step 6: store 테스트 통과 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_embedding_store.py'`

  Expected: 저장·재조회·범위·차원 테스트 PASS.

- [x] **Step 7: 커밋** — 이 task의 세 파일만 스테이징한다.

  Commit: `feat: store model-specific RAG embeddings`

### Task 3: 기존 beauty 청크 재임베딩 CLI

**Files:**
- Create: `src/toss_ads/rag/embedding_indexer.py`
- Modify: `src/toss_ads/rag/__main__.py`
- Modify: `src/toss_ads/rag/store.py`
- Test: `tests/test_rag_embedding_indexer.py`

**Interfaces:**
- `index_existing_chunks(store, embedder, *, run_id: str, dataset_version: str, category: str, batch_size: int = 16) -> EmbeddingIndexSummary`를 제공한다. Summary 필드는 `run_id`, `dataset_version`, `category`, `embedding_model`, `model_revision`, `total_chunk_count`, `preexisting_vector_count`, `embedded_chunk_count`, `document_embedding_seconds`, `elapsed_seconds`, `chunks_per_second`, `model_load_seconds`, `cpu_thread_count`, `max_rss_mb`, `status`다. 처리량은 DB 시간을 뺀 순수 문서 임베딩 시간으로 계산한다.
- `RagStore.embedding_target_chunk_count(run_id, dataset_version, category) -> int`는 run의 데이터 버전과 카테고리 청크 수를 읽고, run/데이터 버전 불일치 또는 빈 범위면 임베딩 전에 실패한다.
- CLI 명령은 `env PYTHONPATH=src .venv/bin/python -m toss_ads.rag embed-model --run-id ... --dataset-version ... --category beauty --batch-size 16 --summary-output reports/rag-bge-m3-test-items2-beauty-2026-10-20-index.json`이다. 모델은 `BAAI/bge-m3`, 최대 입력 길이는 128로 고정한다.
- 기존 `index`와 `serve` 동작, `index_dataset()`의 새 run 생성·활성화 흐름은 수정하지 않는다.

- [x] **Step 1: 실패하는 재임베딩 테스트 작성** — 대상 메타데이터가 일치하면 누락 청크만 16개 이하 배치로 임베딩하고, 이미 저장된 벡터는 건너뛰며, 모든 청크 완료 후 프로필을 `ready`로 표시하는 fake store 테스트를 작성한다. run/dataset/category 불일치는 embedder 호출과 쓰기 전에 실패해야 한다.
- [x] **Step 2: 테스트가 실패하는지 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_embedding_indexer.py'`

  Expected: 새 모듈과 CLI 명령이 없어 실패한다.

- [x] **Step 3: 재개 가능한 임베딩 루프 구현** — 배치마다 `missing_embedding_texts()`를 사용하고 결과를 즉시 upsert한다. 실패 시 프로필을 `failed`로 기록하되 저장된 벡터는 유지하여 같은 명령 재실행 시 누락분만 처리한다. 입력 텍스트는 DB의 기존 `embedding_text` 그대로 사용한다.
- [x] **Step 4: CLI와 사전 검증 추가** — `--run-id`, `--dataset-version`, `--category`를 필수로 받고, 프로필과 run 메타데이터가 일치하지 않으면 작업을 중단한다. source API 호출이나 active run 변경은 하지 않는다.
- [x] **Step 5: 재임베딩 테스트 통과 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_embedding_indexer.py'`

  Expected: 사전 중단, 누락분 재개, 완료 상태 테스트 PASS.

- [x] **Step 6: 커밋** — 이 task의 세 파일만 스테이징한다.

  Commit: `feat: re-embed existing RAG chunks with BGE-M3`

### Task 4: BM25·dense·hybrid 비교 검색

**Files:**
- Create: `src/toss_ads/rag/comparison.py`
- Test: `tests/test_rag_comparison.py`

**Interfaces:**
- `search_products(store, embedder, *, run_id: str, query: str, mode: Literal["bm25", "hybrid", "dense"], category: str, channel_depth: int = 20, rrf_k: int = 60) -> list[dict[str, Any]]`를 제공한다.
- BM25는 `search_bm25`, dense는 BGE query embedding과 `search_embedding_vector`, hybrid는 두 채널의 top 20을 받아 상품별 첫 chunk 순위를 각각 사용한 RRF로 정렬한다.
- 이 모듈은 오프라인 비교용이다. 기존 `hybrid_search()`와 API 기본 설정은 바꾸지 않는다.

- [x] **Step 1: 실패하는 검색 모드 테스트 작성** — BM25 mode가 임베더를 호출하지 않는지, dense mode가 BM25를 호출하지 않는지, hybrid mode가 둘 다 호출하고 `k=60` 상품 단위 RRF를 적용하는지 테스트한다. 동일 상품의 다중 chunk는 한 번만 순위에 반영한다.
- [x] **Step 2: 테스트가 실패하는지 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_comparison.py'`

  Expected: 비교 검색 함수가 없어 실패한다.

- [x] **Step 3: 모드별 검색과 상품 deduplication 구현** — 각 채널은 최대 20개 chunk를 가져오고, 제품 순위는 해당 채널 내 첫 chunk 순위로 계산한다. hybrid는 두 채널 순위를 `1 / (60 + rank)`로 합산하고 동점은 category와 product ID로 결정한다.
- [x] **Step 4: 검색 모드 테스트 통과 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_comparison.py'`

  Expected: BM25 미호출·dense 미호출·RRF·중복 제거 테스트 PASS.

- [x] **Step 5: 커밋** — 이 task의 두 파일만 스테이징한다.

  Commit: `feat: compare BM25 and BGE-M3 retrieval modes`

### Task 5: 고정 질의 평가와 결과 보고서

**Files:**
- Create: `evals/fixtures/test_items2_beauty_bge_m3.json`
- Create: `scripts/compare_rag_embeddings.py`
- Create: `tests/test_rag_embedding_evaluation.py`
- Modify: `src/toss_ads/rag/bge_m3.py` — pin evaluation queries to the indexed model revision.
- Modify: `src/toss_ads/rag/embedding_indexer.py`, `src/toss_ads/rag/__main__.py` — report pure document-embedding duration and throughput.
- Modify: `tests/test_rag_bge_m3_embeddings.py`, `tests/test_rag_embedding_indexer.py` — cover revision pinning and timing fields.
- Create after database evaluation: `reports/rag-bge-m3-test-items2-beauty-2026-10-20.json`
- Create after database evaluation: `docs/rag-bge-m3-test-items2-beauty-2026-10-20.md`

**Interfaces:**
- Fixture는 이전 비교의 동일 query 10개, OOD 2개, 고정 `expected_product_ids`, dataset version `test_items2:v6.1-review-refined:sha256=94681a28271ca9b1:products=1500:reviews=46100`, run ID `e925490f-4f34-4c03-9248-eb9ebdfcde48`, category `beauty`를 담는다. 이전 임시 라벨(`/tmp/test_items2_beauty_labels.json`)에서 ID와 기대 제목을 옮기고 라벨이 규칙 기반임을 표시한다.
- 평가기는 각 질의에 BM25 단독, BM25+BGE-M3 hybrid, BGE-M3 dense 단독을 실행하고 `Hit@1/5`, `Macro Recall@5`, `Macro MRR@5`, `Macro Precision@5`, OOD 반환 수, 질의별 Top 5를 산출한다.
- Recall은 질의별 `relevant in Top 5 / expected IDs`, MRR은 첫 관련 상품 reciprocal rank, Precision@5는 기존 보고서와 같게 항상 5를 분모로 쓴다. OOD는 결과를 반환한 질의 수/2다.
- 실행 명령은 `env PYTHONPATH=src .venv/bin/python scripts/compare_rag_embeddings.py --run-id e925490f-4f34-4c03-9248-eb9ebdfcde48 --dataset-version 'test_items2:v6.1-review-refined:sha256=94681a28271ca9b1:products=1500:reviews=46100' --category beauty --index-stats reports/rag-bge-m3-test-items2-beauty-2026-10-20-index.json --output reports/rag-bge-m3-test-items2-beauty-2026-10-20.json`이다.

- [x] **Step 1: 고정 query fixture 추가** — 이전 임시 label JSON의 10개 긍정 질의와 두 OOD 질의를 IDs·기대 제목과 함께 저장한다. 긍정 기대 개수는 순서대로 `12, 8, 5, 5, 3, 24, 4, 1, 1, 19`여야 하고, 두 OOD의 기대 ID 목록은 비어 있어야 한다.
- [x] **Step 2: 평가 단위 테스트 작성** — query 수, 라벨 수, fixture dataset/run/category 검증과 세 검색 구성의 지표 계산을 테스트한다. 10개 긍정 케이스 중 첫 케이스의 기대 ID 2개 중 1개를 rank 1, 둘째의 기대 ID 1개를 rank 2로 두고 나머지는 미검색 처리해 `Hit@1=0.1`, `Hit@5=0.2`, `Macro Recall@5=0.15`, `Macro MRR@5=0.15`, `Macro Precision@5=0.04`를 고정한다. OOD는 한 질의만 결과를 반환시켜 `1/2`로 확인한다.
- [x] **Step 3: 테스트가 실패하는지 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_embedding_evaluation.py'`

  Expected: 평가 runner와 지표 함수가 없어 실패한다.

- [x] **Step 4: 지표 계산 및 DB 평가 runner 구현** — 모든 mode에서 같은 query 순서·같은 run/category를 사용하고 DB snapshot 메타데이터 불일치 시 중단한다. 보고서에는 모델 revision, 청크·상품·리뷰 수, CPU 모델 로드/문서 임베딩 시간, 처리량, query embedding·검색 p50/p95, 프로세스 최대 메모리, 표본 수와 라벨 한계를 기록한다.
- [x] **Step 5: 결과 문서 작성** — 실행 후 JSON의 동일 수치를 표와 질의별 결과로 정리하고 OOD 두 질의 모두 결과가 반환되면 이를 그대로 보고한다. 결과는 탐색 평가로 표시하며 사람 검수 라벨이나 거절 임계값이 검증됐다고 쓰지 않는다.
- [x] **Step 6: 평가 단위 테스트 통과 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_embedding_evaluation.py'`

  Expected: fixture 검증과 지표 산출 테스트 PASS.

- [x] **Step 7: 전체 RAG 단위 테스트 실행**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_*.py'`

  Expected: 기존 RAG 테스트와 새 테스트 모두 PASS.

- [x] **Step 8: 대상 DB 확인 후 스키마 적용 및 평가 실행** — 먼저 `5432/toss_rag`와 지정 run의 dataset version·beauty 청크 78,595개를 확인한다. 일치할 때만 additive SQL을 적용하고 재임베딩 CLI를 실행해 index summary JSON을 남긴 뒤 세 구성을 평가한다. 다른 DB, 다른 run, 다른 데이터 버전이면 중단한다.
- [x] **Step 9: 커밋** — fixture, runner, 테스트와 생성된 두 결과 문서만 스테이징한다.

  Commit: `eval: compare BGE-M3 dense and hybrid retrieval`

## Plan Self-Review

- 설계 요구사항은 Task 1의 CPU BGE-M3 어댑터, Task 2의 별도 1,024차원 저장소, Task 3의 기존 청크 재임베딩, Task 4의 세 검색 모드, Task 5의 동일 질의 평가와 보고서로 모두 연결했다.
- DB 범위·중단 조건, 재개 가능성, 차원, dense-only의 BM25 배제, OOD 결과는 각각 Review Focus의 테스트로 고정했다.
- `index_dataset()`과 기존 API 기본 경로를 바꾸지 않아 사용자 검토 전 운영 전환은 발생하지 않는다.

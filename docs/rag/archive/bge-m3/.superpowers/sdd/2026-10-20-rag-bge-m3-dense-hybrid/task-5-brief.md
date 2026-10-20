### Task 5: 고정 질의 평가와 결과 보고서

**Files:**
- Create: `evals/fixtures/test_items2_beauty_bge_m3.json`
- Create: `scripts/compare_rag_embeddings.py`
- Create: `tests/test_rag_embedding_evaluation.py`
- Create after database evaluation: `reports/rag-bge-m3-test-items2-beauty-2026-10-20.json`
- Create after database evaluation: `docs/rag-bge-m3-test-items2-beauty-2026-10-20.md`

**Interfaces:**
- Fixture는 이전 비교의 동일 query 10개, OOD 2개, 고정 `expected_product_ids`, dataset version `test_items2:v6.1-review-refined:sha256=94681a28271ca9b1:products=1500:reviews=46100`, run ID `e925490f-4f34-4c03-9248-eb9ebdfcde48`, category `beauty`를 담는다. 이전 임시 라벨(`/tmp/test_items2_beauty_labels.json`)에서 ID와 기대 제목을 옮기고 라벨이 규칙 기반임을 표시한다.
- 평가기는 각 질의에 BM25 단독, BM25+BGE-M3 hybrid, BGE-M3 dense 단독을 실행하고 `Hit@1/5`, `Macro Recall@5`, `Macro MRR@5`, `Macro Precision@5`, OOD 반환 수, 질의별 Top 5를 산출한다.
- Recall은 질의별 `relevant in Top 5 / expected IDs`, MRR은 첫 관련 상품 reciprocal rank, Precision@5는 기존 보고서와 같게 항상 5를 분모로 쓴다. OOD는 결과를 반환한 질의 수/2다.
- 실행 명령은 `env PYTHONPATH=src .venv/bin/python scripts/compare_rag_embeddings.py --run-id e925490f-4f34-4c03-9248-eb9ebdfcde48 --dataset-version 'test_items2:v6.1-review-refined:sha256=94681a28271ca9b1:products=1500:reviews=46100' --category beauty --index-stats reports/rag-bge-m3-test-items2-beauty-2026-10-20-index.json --output reports/rag-bge-m3-test-items2-beauty-2026-10-20.json`이다.

- [ ] **Step 1: 고정 query fixture 추가** — 이전 임시 label JSON의 10개 긍정 질의와 두 OOD 질의를 IDs·기대 제목과 함께 저장한다. 긍정 기대 개수는 순서대로 `12, 8, 5, 5, 3, 24, 4, 1, 1, 19`여야 하고, 두 OOD의 기대 ID 목록은 비어 있어야 한다.
- [ ] **Step 2: 평가 단위 테스트 작성** — query 수, 라벨 수, fixture dataset/run/category 검증과 세 검색 구성의 지표 계산을 테스트한다. 10개 긍정 케이스 중 첫 케이스의 기대 ID 2개 중 1개를 rank 1, 둘째의 기대 ID 1개를 rank 2로 두고 나머지는 미검색 처리해 `Hit@1=0.1`, `Hit@5=0.2`, `Macro Recall@5=0.15`, `Macro MRR@5=0.15`, `Macro Precision@5=0.04`를 고정한다. OOD는 한 질의만 결과를 반환시켜 `1/2`로 확인한다.
- [ ] **Step 3: 테스트가 실패하는지 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_embedding_evaluation.py'`

  Expected: 평가 runner와 지표 함수가 없어 실패한다.

- [ ] **Step 4: 지표 계산 및 DB 평가 runner 구현** — 모든 mode에서 같은 query 순서·같은 run/category를 사용하고 DB snapshot 메타데이터 불일치 시 중단한다. 보고서에는 모델 revision, 청크·상품·리뷰 수, CPU 모델 로드/문서 임베딩 시간, 처리량, query embedding·검색 p50/p95, 프로세스 최대 메모리, 표본 수와 라벨 한계를 기록한다.
- [ ] **Step 5: 결과 문서 작성** — 실행 후 JSON의 동일 수치를 표와 질의별 결과로 정리하고 OOD 두 질의 모두 결과가 반환되면 이를 그대로 보고한다. 결과는 탐색 평가로 표시하며 사람 검수 라벨이나 거절 임계값이 검증됐다고 쓰지 않는다.
- [ ] **Step 6: 평가 단위 테스트 통과 확인**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_embedding_evaluation.py'`

  Expected: fixture 검증과 지표 산출 테스트 PASS.

- [ ] **Step 7: 전체 RAG 단위 테스트 실행**

  Run: `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_*.py'`

  Expected: 기존 RAG 테스트와 새 테스트 모두 PASS.

- [ ] **Step 8: 대상 DB 확인 후 스키마 적용 및 평가 실행** — 먼저 `5432/toss_rag`와 지정 run의 dataset version·beauty 청크 78,595개를 확인한다. 일치할 때만 additive SQL을 적용하고 재임베딩 CLI를 실행해 index summary JSON을 남긴 뒤 세 구성을 평가한다. 다른 DB, 다른 run, 다른 데이터 버전이면 중단한다.
- [ ] **Step 9: 커밋** — fixture, runner, 테스트와 생성된 두 결과 문서만 스테이징한다.

  Commit: `eval: compare BGE-M3 dense and hybrid retrieval`

## Plan Self-Review

- 설계 요구사항은 Task 1의 CPU BGE-M3 어댑터, Task 2의 별도 1,024차원 저장소, Task 3의 기존 청크 재임베딩, Task 4의 세 검색 모드, Task 5의 동일 질의 평가와 보고서로 모두 연결했다.
- DB 범위·중단 조건, 재개 가능성, 차원, dense-only의 BM25 배제, OOD 결과는 각각 Review Focus의 테스트로 고정했다.
- `index_dataset()`과 기존 API 기본 경로를 바꾸지 않아 사용자 검토 전 운영 전환은 발생하지 않는다.

# RAG 세 산출물 통합 결정

**상태:** Backend 브랜치의 구현 결정 기록. 팀 인터페이스 합의를 대신하지 않습니다.

## 통합한 세 입력

| 입력 | 확인한 내용 | Backend 통합 |
|---|---|---|
| 현재 RAG 청킹 작업 | `EvidenceChunk`, 원문 필드·Unicode 오프셋, 안정적인 chunk ID, user_id 제거, 표본 구조 점검 | `src/toss_ads/rag/chunker.py`, `types.py`, `source.py`에 생산 색인 흐름으로 가져옴 |
| 가온님 `kaon_rag_public_upload.zip` | 공개 초안은 `rank-bm25` JSON 스냅샷과 상품/리뷰 문서화, API 호출 제한·재시도 검증. ZIP의 예시는 mock이며 개인 실API 결과 파일은 포함되지 않음 | 입력 검증·bounded retry를 반영. `rank-bm25` 로컬 인덱스는 검색 품질 비교용으로 남기고 서비스 엔진으로 채택하지 않음 |
| AI Agent팀 산출물 | 원본/요청/응답 JSON Schema, 예시, 계약 검사기, tuning/holdout 질문 후보. 별도의 원문 프롬프트 파일은 이 Backend 저장소에서 찾지 못함 | 기존 요청/응답 JSON 모양, 상태, 평가 라벨을 유지하고 FastAPI 검색 경계에 연결 |

## 통합 기준

- 운영 검색은 기존 승인 설계대로 ParadeDB `pg_search` BM25와 pgvector cosine 검색을 병렬 실행하고, 상품별 최고 순위를 RRF k=60으로 결합합니다. 채널별 후보는 20개, 최종 상품은 `top_k`(기본 10, 최대 20), 상품별 근거는 최대 3개입니다.
- 가온님 `rank-bm25`의 별도 JSON 인덱스는 이 PostgreSQL 색인과 동시에 운영하지 않습니다. 그래야 서비스 색인/버전/근거가 한 경로로 유지됩니다. 오프라인 비교 결과를 추가할 때 별도 실험 결과로 기록합니다.
- 출처 경로는 JSON Pointer를 표준으로 했습니다. 현재 청커와 일치시키기 위해 Agent 응답 예시와 골든 라벨을 `/features/0`, `/text` 형태로 바꿨습니다. 계약 검사기는 이전 `features[0]` 표기를 마이그레이션 동안 읽습니다.
- `parent_asin`은 결과 `product_id`로 보존합니다. 이 값은 Amazon 상품 식별자이며 Toss/Commerce 내부 상품 ID라고 간주하지 않습니다.
- Agent가 준 `query`만 BM25와 임베딩에 사용합니다. `original_question`은 질의 재작성에 쓰지 않습니다. `required_conditions`와 `preferences`는 결과에 미확인 조건으로 반환합니다.
- 상품의 원본 `price`는 보존하되 통화가 명시되지 않으면 `price_currency`는 비워 둡니다. 가격 범위는 현재 하드 필터로 적용하지 않습니다.
- `low_relevance`는 `RAG_MIN_RRF_SCORE`가 설정된 경우에만 반환합니다. 기본값은 미설정이며, 평가 결과 없이 임의 임계값을 채택하지 않습니다.
- 청커의 기본 증거 최대 길이는 FastEmbed 토크나이저로 96 tokens입니다. 임베딩 모델 자체의 128-token 입력 길이보다 낮게 두고 제목/필드 문맥까지 포함해 세며, 글자 수를 토큰 수로 취급하지 않습니다.

## 담당자와 다시 합의할 항목

1. **DB 담당자 — 확장 설치 위치:** 현재 원본 API의 Compose는 `postgres:18.6` 이미지라 pgvector/pg_search 설치와 `shared_preload_libraries=pg_search` 설정이 없습니다. 기존 DB에 확장을 더할지, 별도의 RAG PostgreSQL 인스턴스를 둘지 결정해야 합니다. `deploy/amazon-reviews-rag.sql`은 vector 0.8.7과 pg_search 0.26.0이 설치된 DB에서만 실행됩니다.
2. **Agent 담당자 — `source_field`:** 기존 예시는 bracket 표기였고 통합 코드는 JSON Pointer를 반환합니다. Agent 소비 코드가 JSON Pointer로 전환 가능한지 확인해야 합니다.
3. **Agent/기획 담당자 — 저관련성 판정:** tuning/holdout 질문에 대한 관련성 판정과 `RAG_MIN_RRF_SCORE` 값이 아직 없습니다. 값이 승인되기 전에는 low-relevance 분류가 동작하지 않습니다.
4. **DB/API 담당자 — 가격:** 현재 source API에 권위 있는 통화 필드가 있는지 확정해야 합니다. 확인되면 통화가 일치하는 요청만 가격 필터에 사용할 수 있습니다.
5. **Agent/검색 담당자 — 한국어 BM25:** 원문은 주로 영어이고 한국어 질의의 교차언어 회수는 dense 검색이 담당합니다. 평가에서 lexical 누락이 크면 pg_search 토크나이저/질의 정규화를 비교합니다.
6. **AI Agent팀 — 프롬프트 산출물:** 현재 전달된 ZIP과 Backend 저장소에서 계약/평가 자료는 찾았지만 별도 prompting 원문은 찾지 못했습니다. 다른 프롬프트 파일을 뜻한 경우 그 파일도 통합 입력으로 추가해야 합니다.

## 근거 및 한계

- ZIP의 `examples/mock`은 합성 예시입니다. ZIP 상태 문서의 비공개 실 API 시험 수치는 공개 산출물만으로 재현할 수 없으므로 통합 성능 근거로 쓰지 않았습니다.
- Backend 질문 세트는 원본 출처를 확인한 후보입니다. 관련성 합의 전에는 완전한 정답 집합이 아닙니다.
- 코드와 DDL을 작성했지만 이 작업에서 실제 DB 확장 설치, 전체 데이터 색인, 실제 RAG 검색 요청, 검색 품질 측정은 수행하지 않았습니다.

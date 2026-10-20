# RAG 전체 자료 — BGE-M3 운영 기준

기준: **2026-10-20 20:49 KST**. BGE 모델을 유지한 API 0.3.1 호환 복구를 8002에 적용하고 검증했다.

## 자료 바로가기

| 내용 | 문서 |
|---|---|
| 장애 원인·복구·요청 예제·검증 결과 | **[BGE API 호환성 복구](bge-api-compat-recovery-2026-10-20.md)** |
| 구성·호출 흐름·메서드·LangChain | [현재 RAG 구성](current-system.md) |
| 데이터셋·원본/옵션/리뷰·청크·벡터 저장 | [데이터셋과 저장 구조](datasets-and-storage.md) |
| 96토큰 청킹·BGE 1,024차원·v2/v3 | [청킹과 임베딩](chunking-and-embeddings.md) |
| MiniLM/E5/BGE/Qwen 비교·비용·전체 전환 결과 | [모델 비교와 평가](model-comparisons-and-evaluation.md) |
| API 0.3.1·Brain 연결·남은 범위 | [API·Agent 연동](integration-and-gaps.md) |
| 전체 원문·PDF·JSON·과거 설계 찾기 | [전체 문서 목록](document-catalog.md) |
| 현재 실행 증거·스키마 | [상태 증거](evidence/runtime-snapshot-2026-10-20.json), [요청 스키마](evidence/current-bge-request.schema.json) |
| 실제 검증 | [후보·운영·외부·DB 대조 결과](evidence/rag-bge-api-compat-verification-2026-10-20.json) |
| 현재 실행 소스 사본 | [소스·해시·출처](reference-code/bge-api-compat/source-metadata.json) |
| 원문 출처·중복·SHA-256 | [source-manifest.json](source-manifest.json) |
| 18:25 당시 PDF, 복구 전 기록 | [BGE 전체 보고서 PDF](../../artifacts/rag-bge-m3-full-documentation-2026-10-20.pdf) |

## 현재 구성 요약

| 항목 | 현재 확인 결과 |
|---|---|
| 모델 | **BAAI/bge-m3**, dense **1,024차원**, 고정 revision |
| 검색 | ParadeDB BM25 + BGE dense → 상품별 RRF(k=60) |
| 검색 DB | **5432/toss_rag/rag** |
| 가격·재고 대조 | **5432/toss/test_items2**, 같은 variant 행 검증 |
| 기본 프로필 | **test_items2**, 명시적으로 선택 |
| 데이터 | 1,500상품·1,917옵션·46,100리뷰 |
| BGE 벡터 | **114,106개**, 전체 네 범주, scope=*, ready |
| 청킹 | 기존 v2, 최대 96토큰, overlap 없음 |
| 임베딩 입력 | 최대 128토큰, CPU FlagEmbedding |
| MiniLM | 기존 384차원 벡터 보존 |
| API | **0.3.1**, 8002, profile/product_type/in_stock 및 catalog 경로 복원 |
| LangChain | BGE 호환 Retriever 어댑터. HTTP는 hybrid_search 직접 호출 |

18:25의 BGE 배포는 이전 API 0.2.0 기반이라 기존 요청이 422로 거부됐다. 20:48에 0.3 기능을 BGE에 연결한 복구본을 적용했다. 원본·청크·벡터·프로필 포인터는 변경하지 않았다.

## 검증과 한계

회귀 테스트 9개, 8003/8002 HTTP 검사 각각 10개, LAN·두 HTTPS 경로의 health/search가 통과했다. 옵션 15건과 근거 관계 43건을 DB에 대조했다. **연결·제약 검증이며 추천 정확도나 웹/LLM E2E 평가는 아니다.** 임의 필수 스펙은 여전히 미검증 조건이다.

기존 test-items catalog는 180상품 전용이다. 기본 검색 test_items2 1,500개와 구분한다. 0.2 strict 응답 파서는 복원된 0.3 필드를 받아야 한다.

## 수집·이력·저장 상태

원문·평가·스키마·예제 **239개**, 발견 위치/버전 **300건**은 기존 수집 범위다. 새 복구 보고서·요약·실행 증거·읽기용 소스는 원문 집계에 포함하지 않는다.

이전 [14:47 MiniLM 기록](history/minilm-2026-10-20-1447/README.md)과 [18:25 BGE 복구 전 기록](history/bge-2026-10-20-1825/README.md)을 보존했다. archive·기존 PDF/ZIP의 서술은 작성 당시 기준이며, 현재 상태는 이 목차와 복구 보고서를 따른다. 기존 PDF/ZIP은 이번 복구 내용을 담도록 재생성하지 않았다.

문서는 **feature/rag-documentation-index**, 복구 코드는 **feature/rag-bge-api-compat**에 저장했다. 실행 서비스는 복구본으로 적용했다. 20:49 확인 당시에는 새 커밋·푸시 전이었으며 이후 공유 상태는 각 브랜치의 Git 이력과 원격 브랜치를 따른다. main에는 병합하지 않았다. [팀 Git 기준](../team-git-workflow.md)을 따른다.

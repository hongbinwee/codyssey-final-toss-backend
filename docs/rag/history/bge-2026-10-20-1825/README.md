# RAG 전체 자료 — BGE-M3 운영 기준

기준: **2026-10-20 18:25 KST**. 실제 컨테이너·HTTP 상태·실행 소스·DB를 읽어 갱신했다.

## 자료 바로가기

| 내용 | 문서 |
|---|---|
| 실제 BGE 구성·호출 흐름·메서드·LangChain | **[현재 RAG 구성](current-system.md)** |
| 데이터셋·원본/옵션/리뷰·청크·벡터 저장 | **[데이터셋과 저장 구조](datasets-and-storage.md)** |
| 96토큰 청킹·BGE 1,024차원·재임베딩·v2/v3 | **[청킹과 임베딩](chunking-and-embeddings.md)** |
| MiniLM/E5/BGE/Qwen 비교·비용·전체 전환 결과 | **[모델 비교와 평가](model-comparisons-and-evaluation.md)** |
| 현재 API 0.2.0 계약·Brain 연결·추천 정책 공백 | **[API·Agent 연동](integration-and-gaps.md)** |
| 전체 원문·PDF·JSON·계약·과거 설계 찾기 | **[전체 문서 목록](document-catalog.md)** |
| 통합 보고서 인쇄·공유 | **[BGE 전체 보고서 PDF](../../../../artifacts/rag-bge-m3-full-documentation-2026-10-20.pdf)** |
| 실행 상태·현재 요청 스키마 | [상태 증거](runtime-snapshot-2026-10-20.json), [요청 JSON Schema](current-bge-request.schema.json) |
| 원문 출처·버전·중복·SHA-256 | [source-manifest.json](../../source-manifest.json) |
| 실제 BGE 실행 소스 사본 | [소스 메타데이터](../../reference-code/bge-m3/source-metadata.json) |

## 현재 구성 요약

| 항목 | 현재 확인 결과 |
|---|---|
| 모델 | **BAAI/bge-m3**, dense **1,024차원**, 고정 revision |
| 검색 | **ParadeDB BM25 + BGE dense → 상품별 RRF(k=60)** |
| DB | **5432/toss_rag/rag** |
| 데이터 | test_items2: **1,500상품·1,917옵션·46,100리뷰** |
| BGE 벡터 | **114,106개**, 전체 네 범주, scope=*, ready |
| 청킹 | 기존 v2, **최대 96토큰**, overlap 없음. 재청킹 없이 BGE 재임베딩 |
| 입력 길이 | 현재 BGE 호출 최대 128토큰 |
| 기존 MiniLM | 복구용 384차원 벡터 보존 |
| LangChain | 현재 BGE 계산은 **FlagEmbedding 직접 호출**. HTTP도 hybrid_search 직접 호출 |
| API | 현재 **0.2.0** 계약. 이전 0.3.0 확장 필드와 구분 필요 |
| 가격/재고·유형 검증 | 이전 추천 품질 브랜치 기능 전체가 현재 BGE 실행본에 통합된 것은 아님 |

현재 BGE 모델 적용은 확인됐다. 전체 카테고리의 추천 정확도는 별도 평가이며, beauty의 소규모 비교 점수를 전체 정확도로 표시하지 않는다.

## 이번 갱신에서 달라진 내용

1. 이전 14:47 MiniLM 상태를 **18:25 BGE 실제 운영 상태**로 갱신했다.
2. 전체 범주 BGE 벡터 114,106개와 모델 설정·현재 API를 재확인했다.
3. 구성도를 BgeM3Embedder/FlagEmbedding/별도 벡터 테이블 기준으로 수정했다.
4. 전체 적재·전환·복구 보고서와 실행 소스/요청 스키마를 추가했다.
5. API 계약·가격/재고·유형 검사 등 브랜치 간 기능 차이를 표시했다.
6. 기존 비교 결과는 그대로 보존하고 새 전체 적용 기록을 추가했다.

## 수집 범위

원문·평가·스키마·예제 **239개**, 발견 위치/버전 **300건**을 수록했다. 같은 내용의 중복 61건은 사본을 합쳤다. 새로 작성한 통합 요약·실행 증거·읽기용 소스는 이 원문 수에 포함하지 않는다.

현재 파일, Backend worktree들, 이전 프로젝트 worktree, 로컬 Git ref의 문서 버전, 사용자 첨부, 데이터 ZIP의 README/DDL/manifest를 조사했다. 외부 팀 문서 저장소나 모든 중간 Git 커밋까지 포함하는 전사 문서 목록은 아니다.

archive는 작성 당시 원문이다. **과거 MiniLM/0.3.0/PDF 설명을 현재 BGE 상태로 읽지 않는다.** 이전 자료는 [14:47 상태 기록](../minilm-2026-10-20-1447/README.md)과 기존 ZIP으로 보존했다.

원본 데이터·전체 벡터 덤프·모델 가중치·실제 비밀 환경 파일은 새 문서 ZIP에 넣지 않았다. 특히 기존 test_items2 데이터 ZIP의 벡터는 MiniLM 384차원 스냅샷이며 최신 BGE 덤프로 바뀐 것이 아니다.

## 저장·반영 상태

문서 작업은 Backend **feature/rag-documentation-index**에 로컬 저장했다. 이 갱신에서 모델·서비스·DB를 수정하거나 새 검색 평가를 실행하지 않았다. BGE 전환은 기존 적용 기록과 현재 실행 증거로 확인했다.

문서의 새 커밋·GitHub 푸시·main 병합은 수행하지 않았다. 팀 Git 규칙은 [정본](../../../team-git-workflow.md)을 따른다. 이후 모델·run·계약·청커가 바뀌면 이 목차와 현재 구성·증거·평가 문서를 함께 갱신한다.

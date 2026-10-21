# QA13 추천 상품 후속 리뷰 RAG: 구현·배포 현황

기준일: 2026-10-21

대상 저장소: hongbinwee/codyssey-final-toss-backend
작업 브랜치: feature/rag-review-followups

> 이 문서는 코드 브랜치 상태와 현재 실행 중인 API 상태를 구분한다. QA13-B 상품 범위 리뷰 검색은 현재 호스트의 API 컨테이너에 배포되어 있다. QA13-A 전체 리뷰 속성 분류·집계는 코드만 구현되어 있고 실행 API와 DB에는 아직 적용되지 않았다.

## 1. 목적과 역할

사용자가 “아까 추천한 세 제품 중 몇 시간 뒤 건조해진다는 리뷰가 있는 제품은?”처럼 후속 질문하면, RAG 검색 결과 상위 몇 건을 전체 리뷰 통계로 잘못 해석하지 않도록 한다.

| 구성 요소 | 역할 |
|---|---|
| Brain Core | 이전 추천의 상품 ID를 보관하고 검색 범위를 RAG에 전달한다. 리뷰 원문을 Commerce와 대조하고 최종 의미 판단 및 답변을 맡는다. |
| RAG 검색 | 지정 상품 범위에서 BM25와 벡터 검색으로 리뷰 근거 발췌를 찾는다. 검색 결과 수를 전체 리뷰 수로 해석하지 않는다. |
| Commerce | 리뷰 전문과 상품·옵션 연결을 제공해 Brain Core가 근거 원문을 검증할 수 있게 한다. |
| QA13-A 라벨 집계 코드 | 오프라인 분류 결과가 전체 리뷰 모집단을 빠짐없이 덮었을 때만 속성별 리뷰 수를 집계하도록 설계됐다. 현재 API에는 배포되지 않았다. |

현재 RAG 응답은 리뷰 전문이 아니라 검색된 리뷰 청크의 발췌다. source_id로 Commerce 원문을 다시 조회해 앞뒤 문맥을 확인해야 한다. RRF 점수나 검색된 근거 개수는 보습 긍정 리뷰의 전체 개수가 아니다.

## 2. 데이터와 검색 모델

현재 활성 프로필은 test_items2이며 beauty, fashion, food, living 네 카테고리를 포함한다. test_items2/beauty는 전체 프로필 중 beauty 범위만 조회하는 것이고, 전체 상품 검색에는 test_items2 프로필을 사용한다.

| 항목 | 현재 값 |
|---|---|
| 활성 프로필 | test_items2 |
| 데이터셋 버전 | test_items2:v6.1-review-refined:sha256=94681a28271ca9b1:products=1500:reviews=46100 |
| 데이터 규모 | 상품 1,500개, 리뷰 46,100개 |
| 청킹 | source-evidence-token-v2, 최대 96 tokens |
| API 런타임 모델 | BAAI/bge-m3 |
| BGE-M3 벡터 프로필 | ready, 1,024차원, 전체 카테고리 범위, 114,106 청크 |
| 기본 index run 모델 필드 | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| 검색 방식 | BM25 + BGE-M3 벡터 검색 후 RRF 결합 |

기본 index run의 embedding_model 필드는 과거 MiniLM 인덱스 정보를 보존한다. 별도의 BGE-M3 벡터 프로필이 전체 114,106개 청크에 대해 ready 상태이고, API 런타임이 BGE-M3를 사용한다. 현재 검색은 BM25를 제거한 것이 아니라 BM25와 BGE-M3 벡터 검색을 함께 사용한다.

이번 컨테이너 배포에서는 데이터셋, 리뷰 청크, DB 스키마, 임베딩 벡터를 수정하거나 재생성하지 않았다.

## 3. 배포된 기능: QA13-B 상품 범위 리뷰 검색

### 3.1 실행 상태

| 항목 | 상태 |
|---|---|
| 실행 컨테이너 | product-rag-api |
| 실행 이미지 | toss-ads-product-rag-service:qa13b-scoped-review-20261021 |
| API 주소 | 현재 호스트의 127.0.0.1:8002 |
| 헬스 체크 | HTTP 200, profile=test_items2, model=BAAI/bge-m3 |
| 롤백 컨테이너 | product-rag-api-pre-qa13b-20261021로 보존 |
| DB·인덱스 변경 | 없음 |

현재 실행 API에는 기존 POST /v1/rag/search 경로가 유지되고, QA13-B 선택 필드가 추가됐다. 실행 API의 OpenAPI 경로를 확인했으며, QA13-A 리뷰 검색·집계 경로는 아직 실행 API에 없다.

### 3.2 요청 계약

Brain Core는 추천 결과 중 최대 3개의 ID를 최상위 product_ids에 넣는다. 리뷰 전용 검색에는 source_type을 review로 지정한다.

    {
      "request_id": "qa13b-review-search-001",
      "original_question": "이 중 바를 때 촉촉하지만 몇 시간 지나면 건조해진다는 리뷰가 있는 제품 찾아줘",
      "query": "바른 직후에는 촉촉하지만 몇 시간 지나 수분이 날아가 속건조와 당김이 느껴지는 크림 사용 후기",
      "category": "beauty",
      "profile": "test_items2",
      "filters": {},
      "required_conditions": [],
      "preferences": [],
      "product_ids": ["p-v4-o-0008", "p-v4-o-0281", "p-v4-o-0016"],
      "source_type": "review",
      "top_k": 3
    }

요청 규칙:

- product_ids는 중복 없이 1~3개의 문자열이어야 한다. 빈 값, 공백이 앞뒤에 있는 값, 잘못된 타입, 중복 또는 3개 초과는 HTTP 422 invalid_request다.
- source_type은 현재 review만 지원한다. review 요청에는 product_ids가 필수다.
- 필터는 DB 검색 전에 적용된다. BM25와 벡터 검색 모두 지정 product_id 및 review source_type으로 제한된다.
- 지정 ID가 활성 카탈로그에 없으면 빈 결과를 반환한다. 범위를 무시하고 전체 상품으로 재검색하지 않는다.
- top_k는 반환할 상품 수다. 리뷰 청크 수가 아니다. 결과별 리뷰 근거는 최대 3개다.
- 요청에 새 필드가 없으면 기존 일반 상품 검색 계약을 유지한다.

기존 응답의 dataset_version, items[].product_id, items[].rrf_score, items[].evidence[]를 유지한다. 리뷰 근거에는 source_id, source_type, source_version, evidence_text, source_metadata가 포함된다. 현재 데이터에서 옵션 연결 키는 source_metadata.variant_id다. source_id는 Commerce 원문을 확인할 리뷰 식별자다.

### 3.3 배포 후 실제 요청 확인

2026-10-21 실행 API에 실제 test_items2 ID 세 개로 복합 의미 질의를 보냈다.

- 응답: HTTP 200, status=ok
- 반환 상품: 지정한 세 상품만 반환
- 상품별 리뷰 근거 수: 3개, 2개, 3개
- 모든 근거의 source_type: review
- 근거에서 source_id와 variant_id 확인

예를 들어 p-v4-o-0281의 한 근거는 source_id r-v57-real-b277dcc4e1a93fe001fe, variant_id v-v4-o-0281-01을 포함했고, 발췌에 “속건조가 심해서 금방 건조해지는 것 같은 느낌”이라는 표현이 있었다.

이 스모크 확인은 요청 범위와 리뷰 출처가 지켜지는지를 확인한 것이다. 복합 의미 질의의 정답률을 측정한 평가가 아니며, RAG 후보에는 긍정·부정·비교 문맥이 함께 들어올 수 있다. 최종 의미 판단과 리뷰 전문 확인은 Brain Core 및 Commerce 단계에서 해야 한다.

## 4. 브랜치 코드만 있는 기능: QA13-A 전체 리뷰 속성 검색·집계

작업 브랜치에는 다음 API와 오프라인 분류 흐름이 구현되어 있다.

| 경로 또는 구성 | 기능 | 현재 실행 API |
|---|---|---|
| POST /v1/rag/reviews/search | 지정 상품의 보습 관련 리뷰 검색, 고유 리뷰 단위 정리, 인용 반환 | 미배포 |
| POST /v1/rag/reviews/aspect-aggregate | 전체 리뷰 모집단의 속성 감성 집계 및 라벨 커버리지 검증 | 미배포 |
| classify-review-aspects CLI | 로컬 Qwen 호환 모델로 리뷰별 속성 분류 JSONL 생성 | 로컬 코드만 있음 |
| review aspect annotation DB 테이블 | 전체 라벨 배치 저장 및 집계 | 마이그레이션 미적용 |

집계 단위는 상품 ID와 원본 리뷰 키의 조합당 리뷰 한 편이다. 극성은 positive, negative, mixed, neutral, not_mentioned, unclassified다. 전체 모집단 라벨이 완전하고 데이터셋·taxonomy 버전이 일치할 때만 수치를 반환하도록 했다. 상위 검색 결과 수를 전체 리뷰 수로 대체하지 않는다.

현재 DB에서 rag.review_aspect_annotation_batches 테이블은 확인되지 않았다. 전체 분류 JSONL도 생성·적재하지 않았다. 따라서 QA13-A의 리뷰별 감성이나 전체 보습 긍정 리뷰 수는 현재 실행 API에서 조회할 수 없다.

오프라인 분류 모델은 기본 설정상 Qwen 호환 로컬 서버를 사용한다. 별점이나 리뷰 전체 호감도를 보습 감성으로 대신하지 않는다. 불완전하게 복원되는 리뷰는 자르지 않고 unclassified로 처리한다. 전체 분류 전에 사람 기준 라벨 표본으로 품질을 평가해야 한다.

## 5. 리뷰 품질 평가 상태와 한계

실제 뷰티 리뷰 원문 12개를 키워드 층화 표본으로 읽고 로컬 분류 출력을 살펴본 이력이 있다. 보습 긍정 단서 4개는 모델이 positive 4개, 관련 단서가 없는 4개는 not_mentioned 4개, 건조·당김 단서 4개는 negative 3개와 positive 1개로 출력했다. 이는 구현 경로를 살펴본 작은 sanity check다.

표본은 무작위 대표 표본이 아니며 독립된 사람 기준 정답 라벨도 없다. 따라서 precision, recall, F1 또는 전체 리뷰 분류 정확도 수치로 해석할 수 없다. QA13-B의 실시간 검색 스모크 결과도 정확도 점수가 아니다.

| 검증 | 결과와 범위 |
|---|---|
| QA13-B 로컬 단위/API 테스트 | 이전 검증에서 unittest 19개 통과. 스키마, 필터, 범위 이탈 차단, 근거 필드 등을 확인 |
| 현재 API 헬스 체크 | HTTP 200 |
| 현재 API 리뷰 검색 스모크 | HTTP 200, 지정 상품 3개만 반환, 리뷰 근거 8개 확인 |
| BGE-M3 DB 프로필 | read-only 조회에서 전체 범위 114,106 청크 ready 확인 |
| 전체 리뷰 분류 품질 평가 | 사람 기준 라벨 평가 전이므로 정확도 미확정 |
| 운영 지연 시간 평가 | 이번 배포에서 측정하지 않음 |

## 6. 다음 단계

1. test_items2/beauty 리뷰의 긍정·부정·혼합·비언급 경계 사례를 포함하는 사람 기준 평가 표본을 만든다.
2. 오프라인 분류기 출력을 사람 라벨과 비교해 클래스별 precision, recall, F1과 오류 사례를 확인한다.
3. 평가 기준을 통과한 뒤 전체 리뷰 분류 JSONL의 데이터셋 범위와 완전성을 검사한다.
4. 별도 검토 후 annotation migration을 적용하고 완전한 라벨 배치를 적재한다. 이번 배포에서는 이 작업을 수행하지 않았다.
5. QA13-A API를 실행 환경에 배포하고, 전체 리뷰 모집단 집계·불완전 배치·Commerce 원문 대조를 확인한다.
6. Brain Core는 QA13-B 검색 요청에 product_ids와 source_type=review를 추가한다. QA13-A 집계 API는 배포와 라벨 적재가 끝난 뒤에만 연동한다.

현재 배포에서 가능한 것은 지정 상품 범위의 리뷰 근거 검색이다. 전체 리뷰를 분류해 상품별 보습 의견 수를 정확히 비교하는 기능은 아직 사용할 수 없다.

# RAG 카테고리 안전 처리

**상태:** 구현 반영; DB 재색인과 Agent 계약 수용 대기

## 문제

- 표본은 `Clothing_Shoes_and_Jewelry`, `Grocery_and_Gourmet_Food`, `Appliances`에서 각각 1만 건을 추출한다. 샘플러는 `parent_asin`만 확인하고 `main_category`는 필터링하지 않는다.
- `1942191537`은 의류 원본 파일에 있지만 `main_category=Books`, ISBN, Paperback 정보가 있다. 이 후기 때문에 RAG-017 평가 질의가 만들어졌다.
- 따라서 Books 표본을 별도로 가져온 것이 아니라 원본 카테고리 파일 안의 분류 충돌 건이다.

## 색인 규칙

- 알려진 상위 카테고리 간 충돌과 강한 Books 신호를 색인 전에 검사한다.
- 충돌 상품과 연결된 리뷰는 색인하지 않고 `rag.quarantined_products`에 `pending_review`로 기록한다.
- 기록 항목: 실행 ID, 데이터 버전, 원본 카테고리, 상품 ID, 사유, 정책 버전, 분류 근거.
- Books로 자동 재분류하지 않는다. `main_category`가 다르다는 이유만으로 격리하지 않는다.

## 검색 계약

- 요청 필드 `category`는 선택값이며 원본 API 카테고리 키를 사용한다. 생략하면 전체 활성 색인을 검색한다.
- 전달되면 BM25와 벡터 검색 SQL 모두 `LIMIT` 전에 해당 카테고리로 제한한다.
- 지원 목록은 활성 색인에 실제 상품이 있는 카테고리다.
- 미지원 카테고리는 검색 전에 HTTP 422 `unsupported_category`와 `supported_categories`를 반환한다. 다른 카테고리로 대체 검색하지 않는다.
- 지원 카테고리에 결과가 없으면 `no_results`를 반환한다.
- 계약 예시와 스키마는 `contracts/amazon-reviews-rag/v0.2/`에 둔다.

## 완료 기준

1. `1942191537`과 리뷰 청크가 검색 인덱스에 없고 격리 기록에 남는다.
2. `Books` 요청은 현재 지원 목록과 함께 `unsupported_category`를 반환한다.
3. 지정 카테고리 검색은 그 카테고리 결과만 반환한다.

## 범위 밖 및 미완료

- 사용자 질문에서 카테고리를 추출하는 Agent 변경.
- Books 데이터 추가 수집, 자동 재분류, Agent의 v0.2 연동.
- 실제 DB 재색인과 배포. 런타임 연결 환경이 준비되면 적용해야 한다.

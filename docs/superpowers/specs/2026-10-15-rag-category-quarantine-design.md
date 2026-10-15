# RAG 카테고리 필터와 상품 분류 격리 설계

**작성일:** 2026-10-15

**상태:** 스펙 검토 대기

**범위:** Backend RAG 색인기와 RAG → Agent 검색 API

## 1. 목적

원본 데이터의 카테고리와 상품 유형이 충돌하는 상품·리뷰가 검색 후보에 섞이지 않도록 한다. 색인기는 확인이 필요한 충돌 상품을 격리하고, 검색 API는 Agent가 전달한 카테고리를 BM25와 벡터 검색 모두에 강제 적용한다. 요청한 카테고리가 활성 색인에 없으면 그 사실과 현재 지원 카테고리를 응답한다.

Agent의 질문 해석이나 코드 변경은 이 설계 범위에 포함하지 않는다. Agent가 RAG 요청에 카테고리를 전달하는 방식은 이후 공동 계약 검토가 필요하다.

## 2. 확인된 현재 상태와 사례

현재 RAG 색인기는 원본 API의 카테고리 경로를 신뢰해 해당 상품과 리뷰를 색인한다. 검색 요청 스키마에는 카테고리 필드가 없고, BM25·벡터 SQL에도 카테고리 조건이 없다. 따라서 검색 후보는 활성 색인 전체에서 생성된다.

원본 API에서 `parent_asin=1942191537`을 조회한 결과:

- 원본 API 경로의 카테고리는 `Clothing_Shoes_and_Jewelry`다.
- 상품 `categories`는 `Clothing, Shoes & Jewelry`로 시작한다.
- 상품 `main_category`는 `Books`다.
- 상세 정보에 ISBN 10/13과 `Paperback, 320 pages`가 있다.

따라서 이 상품은 원본 카테고리 경로와 상품 유형 신호가 충돌한다. 현재 Books 상품 컬렉션은 별도로 색인되지 않았으므로, 이 상품을 자동으로 Books로 옮기지 않고 확인 전까지 격리한다.

단순히 `main_category`와 원본 카테고리 문자열이 다른 모든 상품을 격리해서는 안 된다. 확인한 가전 상품은 원본 카테고리가 `Appliances`여도 `main_category`가 `Industrial & Scientific`, `Tools & Home Improvement`, `Amazon Home`일 수 있다. 이 값만 비교하면 정상 가전 상품을 대량 격리할 수 있다.

## 3. 설계 원칙

1. 원본 카테고리 키와 상품의 원본 분류 필드를 보존한다.
2. 명시적이고 강한 상품 유형 충돌만 격리한다. 알 수 없는 값이나 단순 문자열 차이를 임의 분류로 취급하지 않는다.
3. 격리 상품과 그 리뷰는 검색 인덱스에 넣지 않는다.
4. 사용자가 요청한 카테고리는 검색 전에 BM25·벡터 검색 양쪽에 적용한다.
5. 요청 카테고리가 지원되지 않거나 검색 결과가 없으면 범위를 넓혀 다른 카테고리 결과로 대체하지 않는다.
6. 자동 재분류하지 않는다. 검토 후 승인된 매핑 변경만 새 색인 실행에 반영한다.

## 4. 색인 시 분류 검사와 격리

### 4.1 검사 입력과 규칙

검사기는 원본 API가 제공한 카테고리 키와 상품 payload의 `categories`, `main_category`, `details`를 사용한다. 알려진 데이터셋 카테고리와 표시용 최상위 카테고리 이름의 대응은 명시적인 별칭 표로 관리한다. 초기 별칭은 다음과 같다.

| 원본 카테고리 키 | 상품 카테고리 표시 이름 |
|---|---|
| `Clothing_Shoes_and_Jewelry` | `Clothing, Shoes & Jewelry` |
| `Grocery_and_Gourmet_Food` | `Grocery & Gourmet Food` |
| `Appliances` | `Appliances` |

검사기는 다음의 명확한 충돌을 격리한다.

- 상품의 알려진 최상위 `categories[0]` 값이 원본 카테고리 별칭과 맞지 않고 다른 상품군을 가리킨다.
- `main_category`가 `Books`와 같이 현재 원본 카테고리에서 명백히 벗어난 상품 유형을 지정한다. ISBN 및 제본/페이지 정보는 격리 기록에 함께 보존해 검토 근거로 사용한다.

`main_category`가 원본 카테고리와 다르다는 이유만으로는 격리하지 않는다. 검사 규칙과 별칭 표에는 버전을 부여해 어떤 정책으로 색인했는지 기록한다.

### 4.2 격리 동작과 기록

충돌 상품은 `rag.indexed_products`와 `rag.evidence_chunks`에 기록하지 않는다. 해당 상품에 연결된 리뷰도 청크화하거나 검색에 넣지 않는다. 리뷰 페이지는 원본 건수·연결 검증을 위해 계속 읽되, 격리 상품의 리뷰는 색인 건수에서 제외한다.

각 실행은 다음 정보를 포함하는 격리 기록을 남긴다.

- `run_id`, `dataset_version`, 원본 카테고리, `parent_asin`
- 격리 사유 코드와 검사 정책 버전
- 상품 제목, 관측된 `main_category`, `categories`, 적용된 유형 신호
- 검토 상태 `pending_review`

원본 payload 전체, 작성자 프로필, 이미지·영상 메타데이터는 격리 기록에 복사하지 않는다. 실행 요약에는 원본에서 읽은 건수, 실제 색인한 건수, 격리 상품 수를 카테고리별로 구분해 둔다.

격리 자체는 색인 실행 실패가 아니다. 다른 치명적 오류 없이 원본 버전·건수 검증이 끝나면 격리 항목을 제외한 실행을 활성화할 수 있다. 원본 버전 변경, DB 오류 등 기존 오류가 발생하면 이전 활성 색인을 유지한다.

### 4.3 검토와 재색인

격리 레코드는 운영자가 원본 분류와 상품 유형을 확인하기 위한 감사 자료다. 검토 UI나 임의 상품별 자동 수정은 이번 범위에 포함하지 않는다. 확인 후 수정이 필요하면 승인된 별칭/매핑 정책을 버전 관리하고 전체 색인을 다시 실행한다. Books 원본 카테고리가 활성 색인에 포함되지 않는 동안에는 이 상품을 Books로 자동 이동하지 않는다.

## 5. 카테고리 제한 검색 계약

### 5.1 요청

Agent → RAG 요청에 선택 필드 `category`를 추가한다. 값은 원본 API의 카테고리 키와 정확히 일치해야 하며, 별칭 변환은 RAG에서 하지 않는다. 필드가 없으면 현재 전체 활성 색인 검색 동작을 유지한다. 카테고리를 전달한 경우에는 그 범위 안에서만 검색한다.

지원 카테고리는 고정 JSON Schema enum으로 박아두지 않는다. 활성 RAG 색인에서 실제 색인 상품이 하나 이상 존재하는 카테고리를 실행 시점의 지원 목록으로 사용한다.

현재 v0.1 응답 스키마는 추가 필드를 허용하지 않는다. 따라서 `category`, `unsupported_category`, `supported_categories`를 포함하는 요청·응답 스키마는 v0.1을 조용히 변경하지 않고 v0.2 제안으로 발행한다. Agent 팀이 v0.2를 수용하기 전까지는 공동 인터페이스 승인 완료로 취급하지 않는다. HTTP 경로 `/v1/rag/search`와 계약 문서 버전은 별도 식별자다. 현재 검색 서비스와 v0.1 계약은 통합 전 제안 상태이므로 Agent 연동은 v0.2 검토 이후 진행한다.

### 5.2 검색과 응답

- 카테고리 조건은 BM25와 벡터 SQL 각각의 `WHERE`에 `LIMIT`보다 먼저 적용한다.
- 검색 결과 조립 단계에서도 요청 카테고리와 다른 항목이 발견되면 검색 오류로 처리한다.
- 성공 응답의 `applied_filters.category`에는 실제 적용한 원본 카테고리 키를 기록한다.
- 결과가 없으면 해당 카테고리의 `no_results`를 반환한다. 다른 카테고리로 재검색하지 않는다.
- 카테고리가 활성 색인에 없으면 임베딩·검색 전에 `status=error`, `error_code=unsupported_category`를 반환한다. 이 응답에는 현재 `supported_categories`와 활성 `dataset_version`을 포함한다. HTTP 상태는 422다.
- 응답과 `/healthz`에 현재 `supported_categories`를 제공한다. 활성 색인이 없으면 빈 목록이다.
- 요청한 카테고리가 활성 색인에 있으면 결과가 있든 없든 `applied_filters.category`에 그 키를 기록한다. 미지원 카테고리는 필터를 적용하지 않았으므로 `applied_filters`는 빈 객체다.
- `supported_categories`는 원본 카테고리 키의 사전순으로 정렬한다.

v0.2 요청 예시:

```json
{
  "request_id": "agent-req-001",
  "original_question": "Books 카테고리의 독서 후기를 찾아줘",
  "query": "The Would Be Queen magic romance review",
  "category": "Books",
  "filters": {},
  "required_conditions": [],
  "preferences": [],
  "top_k": 10
}
```

Books가 아직 색인되지 않았을 때의 응답 예시:

```json
{
  "request_id": "agent-req-001",
  "status": "error",
  "dataset_version": "<active-dataset-version>",
  "supported_categories": [
    "Appliances",
    "Clothing_Shoes_and_Jewelry",
    "Grocery_and_Gourmet_Food"
  ],
  "applied_filters": {},
  "unverified_conditions": [],
  "items": [],
  "error_code": "unsupported_category"
}
```

현재 원본 샘플에는 `Books` 카테고리가 없으므로 Books 요청은 `unsupported_category`가 된다. `The Would Be Queen`은 의류 결과에도 포함되지 않는다. 이 동작은 Agent가 사용자에게 Books가 아직 색인되지 않았다고 설명할 수 있게 한다.

## 6. 범위와 제외 사항

포함:

- Backend RAG 색인 시 분류 검사와 상품·리뷰 격리
- 실행별 격리 감사 자료와 색인 건수
- RAG 요청·응답 계약 v0.2 제안과 예시의 카테고리 필드, 지원 목록, 미지원 카테고리 상태
- BM25와 벡터 검색의 카테고리 하드 필터
- RAG 운영 문서 갱신

제외:

- Agent가 사용자의 “책”을 `Books`로 구조화하는 변경
- Agent의 계약 v0.2 연동 및 Agent 코드 변경
- 원본 Amazon API, `amzdata` 테이블, 원본 카테고리 샘플 구성 변경
- 두 팀 공동 회귀 스위트와 배포
- 이 한 상품을 Books에 자동 재매핑하거나 Books 전체를 새로 색인하는 작업
- 임의의 상품 분류 모델, LLM 판정, 검색 결과 사후 대체
- 전체 운영 DB 색인 및 배포

## 7. 완료 기준

1. `The Would Be Queen`은 source-category/type 충돌로 격리 기록에 남고 상품·리뷰 청크가 생성되지 않는다.
2. 격리 상품은 의류 검색과 Books 검색 결과에 포함되지 않는다.
3. `category=Books` 요청은 `unsupported_category`와 현재 지원 카테고리 목록을 반환한다.
4. 지원되는 카테고리 요청은 두 검색 채널에서 해당 카테고리 결과만 반환한다.
5. 해당 카테고리에 검색 결과가 없을 때 다른 카테고리 후보를 반환하지 않는다.
6. 불일치가 없는 대표 상품은 기존 색인·검색 동작을 유지한다.
7. 격리 건수와 사유를 색인 실행에서 확인할 수 있고, 기존 원본 버전·건수 검증 및 활성화 안전장치가 유지된다.

## 8. 검토가 필요한 선택

- 초기 명시적 상품 유형 충돌 규칙은 Books를 포함한 강한 원본 분류 신호에 한정한다. 다른 도메인 간 충돌 규칙은 실제 원본 필드와 오탐률을 확인한 뒤 별도로 추가한다.
- 지원 카테고리는 원본 데이터셋 전체 카테고리가 아니라 현재 활성 RAG 색인에 상품이 들어 있는 카테고리로 정의한다.
- RAG API 계약은 Agent 팀과 공동 검토가 필요하다. 이 설계는 RAG 측 동작을 제안하며 Agent 측 구현 완료를 뜻하지 않는다.

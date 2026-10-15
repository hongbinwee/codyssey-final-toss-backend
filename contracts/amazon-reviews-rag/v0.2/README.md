# Amazon Reviews RAG v0.2 카테고리 제한 계약 제안

이 디렉터리는 v0.1 요청·응답을 유지하면서 선택 카테고리 검색을 추가하는 제안이다. Agent 연동과 공동 계약 승인은 별도다.

## 카테고리 규칙

- 요청의 `category`는 원본 API의 카테고리 키와 정확히 일치해야 한다. 별칭 변환은 하지 않는다.
- `category`를 생략하면 현재 활성 색인의 전체 카테고리에서 검색한다.
- `supported_categories`는 활성 색인에 색인된 상품이 있는 카테고리 키의 사전순 목록이며 모든 v0.2 응답에 포함한다.
- 지원 카테고리를 요청하면 RAG가 BM25와 벡터 검색 모두에서 SQL `WHERE` 조건으로 결과 범위를 제한하고 `applied_filters.category`에 적용값을 반환한다.
- 요청한 카테고리가 `supported_categories`에 없으면 임베딩·검색 전에 HTTP 422와 `status=error`, `error_code=unsupported_category`를 반환한다. 이때 `applied_filters`는 빈 객체다. 다른 카테고리로 검색을 넓히지 않는다.
- 현재 색인 대상은 `Appliances`, `Clothing_Shoes_and_Jewelry`, `Grocery_and_Gourmet_Food`다. `Books`는 지원 목록에 없으면 검색되지 않는다.

`request-category.json`과 `response-category-ok.json`은 지원 카테고리 검색을 보여준다. `request-unsupported-category.json`과 `response-unsupported-category.json`은 색인되지 않은 Books 요청을 보여준다. `source.schema.json`은 v0.1과 동일한 원본 정규화 형식이다.

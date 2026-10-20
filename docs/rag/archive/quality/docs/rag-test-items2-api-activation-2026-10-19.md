# test_items2 RAG API 적용 기록

기준일: 2026-10-19 (Asia/Seoul)

## 실행 상태

- API: `http://127.0.0.1:8002`, `POST /v1/rag/search`, API 버전 `0.3.0`.
- 실행 컨테이너: `product-rag-api`.
- 이미지: `toss-ads-product-rag-service:24a1051-test-items2`.
- 적용 소스: 기존 개발 브랜치 커밋 `24a1051fff84bb4cf5441e90824e9e9be20e18ec`.
- 기본 프로필: `test_items2`. 허용 프로필: `test_items2`, `all_products`.
- 기본 색인: 상품 1,500개 / 기존 청크 114,106개 / beauty, fashion, food, living.
- 활성 run: `e925490f-4f34-4c03-9248-eb9ebdfcde48`.
- DB: 기존 `5432/toss_rag`, 가격·재고 조회는 같은 서버의 `5432/toss`.
- 기본 프로필은 컨테이너 환경변수에 저장했으며 재시작 후에도 유지된다.

## 요청 예시 — 사용법이며 실행한 검색 테스트 결과 아님

```http
POST /v1/rag/search
Content-Type: application/json
```

```json
{
  "request_id": "nipple-patch-example",
  "profile": "test_items2",
  "original_question": "니플패치 찾아줘",
  "query": "니플패치",
  "category": "fashion",
  "filters": {},
  "required_conditions": [],
  "preferences": [],
  "top_k": 5
}
```

`profile`을 생략하면 test_items2를 사용한다. `category`를 생략하면 해당 프로필의 전체 카테고리가 대상이다. Brain이 카테고리를 보내는 경우 니플패치는 fashion으로 전달해야 한다. beauty로 제한하면 fashion 상품은 검색 대상에서 제외된다. 이전 데이터가 필요하면 profile=all_products를 명시한다.

응답의 `profile_name`, `dataset_version`, `supported_categories`, `search_context`로 선택된 데이터와 검색 버전을 구분한다. 상태 확인은 `GET /healthz`를 사용한다. 기존 `/v1/catalog/test-items` 상품·리뷰 경로는 이전 all_products/test_items 데이터에 고정되어 있으며 새 전체 목록 API로 바뀐 것은 아니다.

현재 주소는 서버 내부용이다. 다른 PC의 기존 승인된 터널·프록시 경로는 같은 8002 목적지를 사용하면 된다. 새로운 외부 포트는 열지 않았다.

## 적용 범위와 권한

- 이미 푸시된 프로필 선택·상품 관련성·Commerce 읽기 지원 코드를 실제 API에 적용했다.
- 기존 이미지의 설치된 의존성을 재사용해 소스만 교체한 이미지를 만들었다. 모델 교체·원본 재적재·재청킹·재임베딩·색인 활성화 변경은 수행하지 않았다.
- rag_runtime은 test_items2 읽기 권한을 이미 가지고 있었다. all_products의 Commerce 연결도 유지하기 위해 toss.test_items 스키마 USAGE와 products/product_variants SELECT만 추가했다. 쓰기 권한은 추가하지 않았다.
- 원본·상품/리뷰 ID·기존 활성 run과 청크를 보존했다.
- 이번 작업에서는 제품 소스를 추가 수정하거나 새 커밋·푸시·main 병합을 하지 않았다. 이 적용 기록은 로컬 문서다.

## 확인 범위

- 새 이미지 빌드, 소스 구문/가져오기, 설정 로딩과 5432의 프로필·Commerce 읽기 연결을 확인했다.
- 실행 후 /healthz: status=ok, profile_name=test_items2, 네 카테고리, commerce_configured=true.
- /openapi.json에서 API 버전과 기존 POST 검색 경로를 확인했다.
- 실제 검색 요청·품질 평가·외부 화면 E2E는 이번 요청에서 실행하지 않았다. 이 기록은 니플패치 검색 품질이나 남성용 구분이 통과했다는 결과가 아니다.
- 외부 화면이 local RAG를 사용하거나 기존 어댑터가 beauty를 강제하면 Brain 측 연결 변경이 별도로 필요하다.

## 복구

이전 컨테이너는 `product-rag-api-before-test-items2-bbb66a2d` 이름으로 중지 보관했다. 신규 컨테이너를 중지·별도 이름으로 보관한 뒤 이전 컨테이너 이름을 product-rag-api로 복원하고 시작하면 이전 API 설정으로 돌아간다. 동시에 두 컨테이너를 기동하지 않는다. DB 원본/색인은 전환하지 않았으므로 복원할 데이터 변경은 없다.

인증정보를 포함한 실행 환경은 접근 제한된 로컬 상태 디렉터리에서만 관리하며 이 문서나 Git에 포함하지 않는다.

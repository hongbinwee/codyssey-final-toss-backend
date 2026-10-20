# Amazon Reviews'23 API 명세

읽기 전용 API로 Amazon Reviews'23 선별 샘플의 상품과 리뷰를 조회합니다. API 주소, 경로, 요청 매개변수와 정상 응답 형식은 PostgreSQL 전환 전과 같습니다.

## 접속 주소

| 용도 | 기본 주소 | 설명 |
|---|---|---|
| 내부망 | `http://172.30.1.53:8001` | 같은 네트워크에서 서버 간 호출에 사용합니다. |
| 외부 | `https://spark.chanuk.theworkpc.com` | Nginx Proxy Manager를 거칩니다. NPM Access List에서 허용한 IP만 호출할 수 있습니다. |

API는 `amazon-reviews-api` systemd 서비스로 실행됩니다. 애플리케이션 자체에는 API 키 인증이 없으며, 외부 접근 제어는 NPM Access List가 담당합니다. 내부 주소로 직접 접속하면 NPM Access List를 거치지 않으므로 신뢰할 수 있는 내부 네트워크에서만 사용하세요.

PostgreSQL 데이터베이스는 `127.0.0.1:5432`에만 바인딩되어 외부에 공개되지 않습니다. 외부 호출자는 HTTP API를 이용합니다.

## 대화형 문서와 OpenAPI

FastAPI는 Swagger UI와 OpenAPI JSON을 제공합니다.

- 내부망: [Swagger UI](http://172.30.1.53:8001/docs), [OpenAPI JSON](http://172.30.1.53:8001/openapi.json)
- 외부: [Swagger UI](https://spark.chanuk.theworkpc.com/docs), [OpenAPI JSON](https://spark.chanuk.theworkpc.com/openapi.json) — NPM Access List에서 허용된 IP로 호출해야 합니다.

## 데이터 범위

샘플에는 카테고리별 상품 10,000개, 전체 상품 30,000개와 리뷰 178,335개가 있습니다. 상품마다 최대 40개 리뷰를 보관하며 정수 평점(1–5)마다 최대 8개를 표본에 포함합니다. 평점별 리뷰가 충분하지 않은 상품은 40개보다 적을 수 있습니다.

URL에는 아래 카테고리 키를 그대로 사용합니다.

| 카테고리 키 | 상품 수 | 리뷰 수 |
|---|---:|---:|
| `Appliances` | 10,000 | 65,618 |
| `Clothing_Shoes_and_Jewelry` | 10,000 | 37,006 |
| `Grocery_and_Gourmet_Food` | 10,000 | 75,711 |

상품과 리뷰는 `(category, parent_asin)`으로 연결합니다. 리뷰 항목에는 안정적인 `review_key`가 포함되고 `user_id`는 반환하지 않습니다.

## API 경로

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/healthz` | API와 데이터 저장소 상태 |
| `GET` | `/v1/categories` | 카테고리별 상품·리뷰 수 |
| `GET` | `/v1/categories/{category}/products` | 카테고리 상품 목록 |
| `GET` | `/v1/categories/{category}/products/{parent_asin}` | 상품 상세 |
| `GET` | `/v1/categories/{category}/reviews` | 카테고리 또는 상품 리뷰 목록 |

### `GET /healthz`

정상 응답은 HTTP `200`입니다.

```json
{
  "status": "ok",
  "dataset_version": "amazon-reviews-2023:seed=20261014:processed_at=2026-10-14T10:41:15.143181+00:00"
}
```

데이터베이스를 사용할 수 없으면 HTTP `503`을 반환합니다.

### `GET /v1/categories`

카테고리별 집계와 데이터셋 버전을 반환합니다.

```json
{
  "dataset_version": "amazon-reviews-2023:seed=20261014:processed_at=2026-10-14T10:41:15.143181+00:00",
  "items": [
    {"category": "Appliances", "product_count": 10000, "review_count": 65618},
    {"category": "Clothing_Shoes_and_Jewelry", "product_count": 10000, "review_count": 37006},
    {"category": "Grocery_and_Gourmet_Food", "product_count": 10000, "review_count": 75711}
  ],
  "limit": 3,
  "offset": 0,
  "total": 3
}
```

### `GET /v1/categories/{category}/products`

상품 목록을 페이지 단위로 반환합니다.

| 매개변수 | 형식 | 기본값 | 제약 |
|---|---|---:|---|
| `limit` | 정수 | `50` | `1`–`200` |
| `offset` | 정수 | `0` | `0` 이상 |

응답의 `items`에는 원본 상품 메타데이터가 들어갑니다. 상품 필드는 원본 레코드에 따라 다를 수 있습니다.

### `GET /v1/categories/{category}/products/{parent_asin}`

요청한 카테고리의 상품 하나를 반환합니다. 필드는 원본 상품 메타데이터에 따릅니다.

### `GET /v1/categories/{category}/reviews`

카테고리 전체 또는 특정 상품의 리뷰를 페이지 단위로 반환합니다.

| 매개변수 | 형식 | 필수 | 기본값 | 제약 |
|---|---|---:|---:|---|
| `parent_asin` | 문자열 | 아니요 | — | 지정하면 해당 상품의 리뷰만 조회 |
| `rating` | 정수 | 아니요 | — | `1`–`5` |
| `limit` | 정수 | 아니요 | `50` | `1`–`200` |
| `offset` | 정수 | 아니요 | `0` | `0` 이상 |

리뷰 항목에는 `review_key`, `parent_asin`, `rating`과 원본 리뷰 필드가 포함됩니다. 개인정보 보호를 위해 `user_id`는 제거합니다.

## 페이지 응답

상품 목록과 리뷰 목록은 다음 형식을 사용합니다.

```json
{
  "dataset_version": "amazon-reviews-2023:seed=20261014:processed_at=2026-10-14T10:41:15.143181+00:00",
  "items": [],
  "limit": 50,
  "offset": 0,
  "total": 10000
}
```

다음 페이지는 `offset`에 앞 페이지의 `offset + limit`을 전달합니다. `offset >= total`이면 페이지가 끝난 것입니다. 상품은 `parent_asin`, 리뷰는 `review_key` 순서로 반환됩니다.

## 호출 예시

같은 내부망의 서버에서 호출하는 예시입니다. 외부 호출자는 `BASE_URL`을 `https://spark.chanuk.theworkpc.com`으로 설정하고 NPM Access List에서 허용된 IP로 호출합니다.

```bash
BASE_URL="http://172.30.1.53:8001"

curl --fail-with-body "$BASE_URL/healthz"
curl --fail-with-body "$BASE_URL/v1/categories"
curl --fail-with-body "$BASE_URL/v1/categories/Clothing_Shoes_and_Jewelry/products?limit=50&offset=0"

curl --fail-with-body --get \
  --data-urlencode "parent_asin=1942191537" \
  --data-urlencode "rating=5" \
  --data-urlencode "limit=8" \
  --data-urlencode "offset=0" \
  "$BASE_URL/v1/categories/Clothing_Shoes_and_Jewelry/reviews"
```

리뷰 항목 예시입니다.

```json
{
  "review_key": "<안정적인 리뷰 키>",
  "asin": "1942191537",
  "parent_asin": "1942191537",
  "rating": 5.0,
  "title": "<리뷰 제목>",
  "text": "<리뷰 본문>",
  "timestamp": 1674432242605,
  "verified_purchase": false,
  "helpful_vote": 0,
  "images": []
}
```

## 오류 응답

| HTTP 상태 | 의미 |
|---:|---|
| `403` | NPM Access List에서 호출자의 IP를 허용하지 않았습니다. |
| `404` | 존재하지 않는 카테고리, 상품 또는 `parent_asin`입니다. |
| `422` | `limit`, `offset`, `rating` 등 요청 값 검증에 실패했습니다. |
| `503` | PostgreSQL 데이터 저장소를 사용할 수 없습니다. |
| `502` | NPM reverse proxy가 API upstream에 연결하지 못했습니다. API 애플리케이션 응답이 아닌 프록시 구간 오류입니다. |

일반적인 API 오류는 `{"detail": "..."}` 형식입니다. FastAPI 요청 검증 오류(`422`)는 `detail` 배열을 반환합니다.

## 서비스 운영

```bash
sudo systemctl status amazon-reviews-api
sudo journalctl -u amazon-reviews-api -f
```

데이터베이스 컨테이너와 적재 방법은 [데이터 안내](../data/amzdata/README.md)를 참고하세요. 원본 데이터는 [Amazon Reviews'23](https://amazon-reviews-2023.github.io/)에서 제공하며, 활용 시 데이터셋 저자를 인용해 주세요.

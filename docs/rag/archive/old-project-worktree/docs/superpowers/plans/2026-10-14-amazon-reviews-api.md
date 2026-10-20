# Amazon Reviews API 구성 및 운영 기준

> 현재 프로젝트의 PostgreSQL 저장소, 읽기 전용 API, 데이터 적재 운영 기준을 정리합니다.

## 목표

Amazon Reviews'23 선별 스냅샷을 PostgreSQL에 적재하고 상품·리뷰 조회 API로 제공합니다. 향후 RAG 수집기는 같은 API로 원본을 읽고, 검색용 데이터는 toss_rag 데이터베이스의 rag 스키마에 저장합니다.

## 현재 구성

- 상품 30,000개와 리뷰 178,335개를 PostgreSQL 18.6에 저장합니다.
- 데이터베이스는 toss_rag, 원본 스키마는 amzdata입니다.
- API 서비스는 systemd에서 실행하고 내부 주소 172.30.1.53:8001에 바인딩합니다.
- PostgreSQL 호스트 포트는 127.0.0.1:5432에서만 접근할 수 있습니다.
- API 계정은 SELECT 전용이고 적재 계정은 별도 환경 파일을 사용합니다.
- 접속 비밀값은 Git에 저장하지 않습니다.

## 데이터 적재 기준

적재기는 data/amzdata/manifest.json과 선별 JSONL을 확인합니다. 상품 키는 category와 parent_asin이며 리뷰 키는 category와 review_key입니다. 원본 payload는 JSONB로 보관합니다. 데이터 전체를 단일 트랜잭션으로 적재하고 manifest 건수가 맞을 때 커밋합니다.

현재 카테고리별 건수는 다음과 같습니다.

| 카테고리 | 상품 수 | 리뷰 수 |
|---|---:|---:|
| Appliances | 10,000 | 65,618 |
| Clothing_Shoes_and_Jewelry | 10,000 | 37,006 |
| Grocery_and_Gourmet_Food | 10,000 | 75,711 |

## API 경로

- GET /healthz
- GET /v1/categories
- GET /v1/categories/{category}/products?limit=&offset=
- GET /v1/categories/{category}/products/{parent_asin}
- GET /v1/categories/{category}/reviews?parent_asin=&rating=&limit=&offset=

목록 응답에는 dataset_version, items, limit, offset, total이 포함됩니다. 목록 크기는 기본 50, 최대 200이며 리뷰 rating은 1부터 5까지입니다. 상품과 리뷰 연결 키는 category 및 parent_asin입니다. 리뷰 응답에서는 user_id를 제외합니다.

## RAG 연동 기준

RAG 수집기는 AMZDATA_DATABASE_URL에 접근하지 않고 HTTP API를 호출합니다. 상품을 페이지 단위로 읽은 뒤 각 평점에 최대 8개씩, 상품마다 최대 40개 리뷰를 수집할 수 있습니다. RAG 소유 테이블은 같은 toss_rag 데이터베이스의 rag 스키마에 두고 전용 역할로 관리합니다. 현재 rag 스키마는 아직 생성하지 않았습니다.

## 운영 점검

서비스의 /healthz와 /v1/categories를 확인하고 전체 상품·리뷰 건수와 dataset_version을 확인합니다. PostgreSQL 데이터는 data/amzdata/postgres/에 보관되며 접속 환경 파일은 소유자 전용 권한으로 관리합니다.

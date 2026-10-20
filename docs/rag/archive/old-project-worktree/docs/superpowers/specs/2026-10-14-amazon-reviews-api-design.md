# Amazon Reviews API 설계

**작성일:** 2026-10-14
**상태:** PostgreSQL 구성 및 API 운영 확인 완료

## 1. 목표

Amazon Reviews'23 선별 데이터의 상품과 리뷰를 읽기 전용 HTTP API로 제공한다. 원본 데이터는 PostgreSQL에 보관하고, API는 기존 RAG 수집기와 다른 호출자가 같은 응답 계약으로 사용할 수 있도록 한다.

## 2. 데이터와 저장 구조

선별 데이터는 상품 30,000개와 리뷰 178,335개로 구성된다.

| 카테고리 | 상품 수 | 리뷰 수 |
|---|---:|---:|
| Appliances | 10,000 | 65,618 |
| Clothing_Shoes_and_Jewelry | 10,000 | 37,006 |
| Grocery_and_Gourmet_Food | 10,000 | 75,711 |

데이터베이스는 toss_rag이며 원본 테이블은 amzdata 스키마에 저장한다. 원본 JSONL과 manifest를 기준으로 스냅샷을 적재한다. 향후 RAG 소유 테이블은 같은 데이터베이스의 rag 스키마에 둔다. 현재 rag 스키마와 벡터 검색 확장은 아직 생성하지 않았다.

## 3. 구성

선별 JSONL과 manifest를 적재기가 검증해 PostgreSQL에 저장한다. FastAPI 서비스는 읽기 전용 계정으로 amzdata를 조회한다. RAG 수집기는 같은 HTTP API에서 원본을 읽고, 전용 계정으로 rag 스키마를 갱신한다.

## 4. HTTP API 계약

- GET /healthz: 서비스와 데이터베이스 준비 상태 및 dataset_version 반환
- GET /v1/categories: 카테고리별 상품·리뷰 건수 반환
- GET /v1/categories/{category}/products?limit=&offset=: 상품 목록 반환
- GET /v1/categories/{category}/products/{parent_asin}: 상품 상세 반환
- GET /v1/categories/{category}/reviews?parent_asin=&rating=&limit=&offset=: 리뷰 목록 반환

목록 기본 크기는 50이며 최대 200이다. offset은 0 이상이고 rating은 1부터 5까지 허용한다. 목록 응답은 dataset_version, items, limit, offset, total을 포함한다. 상품과 리뷰는 category 및 parent_asin으로 연결한다. 리뷰에는 안정적인 review_key를 제공하고 user_id는 응답에서 제외한다.

## 5. 접근과 권한

API 데이터베이스 계정은 amzdata 스키마에서 SELECT만 수행할 수 있다. 적재 계정은 스냅샷 적재 권한을 가지며 rag 스키마를 수정하지 못한다. PostgreSQL 포트는 호스트의 127.0.0.1:5432에만 바인딩한다. API는 서비스 내부 주소 172.30.1.53:8001에서 실행하고, 외부 호출은 Nginx Proxy Manager의 도메인과 접근 목록을 거친다.

## 6. 운영 기준

적재기는 manifest와 실제 행 수를 확인하고 하나의 트랜잭션으로 스냅샷을 갱신한다. 연결 비밀값은 추적되지 않는 환경 파일에 저장한다. API 경로와 JSON 응답 계약은 데이터베이스 운영 설정 변경과 독립적으로 유지한다.

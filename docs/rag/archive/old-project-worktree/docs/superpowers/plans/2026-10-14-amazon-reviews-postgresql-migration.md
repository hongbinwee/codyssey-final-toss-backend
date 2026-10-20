# Amazon Reviews PostgreSQL 운영 구현 계획

**작성일:** 2026-10-14
**상태:** 구현 및 운영 검증 완료

## 목표

Amazon Reviews'23 선별 스냅샷을 PostgreSQL에 저장하고 읽기 전용 REST API로 제공한다. RAG 수집기는 같은 API로 원본을 읽으며, 검색용 데이터는 toss_rag 데이터베이스의 별도 rag 스키마에 둔다.

## 구성 기준

- PostgreSQL 18.6 Docker 컨테이너를 사용한다.
- 데이터베이스는 toss_rag, 원본 스키마는 amzdata다.
- PostgreSQL 호스트 포트는 127.0.0.1:5432에만 바인딩한다.
- API 서비스는 systemd에서 172.30.1.53:8001로 실행한다.
- API는 AMZDATA_DATABASE_URL을 사용하고 읽기 전용 역할로 접속한다.
- 적재기는 AMZDATA_IMPORT_DATABASE_URL을 사용하고 별도 역할로 적재한다.
- 비밀번호가 든 환경 파일은 Git에 포함하지 않고 소유자 전용 권한으로 저장한다.
- 원본 JSONL, manifest, 데이터베이스 간 행 수와 dataset_version을 대조한다.

## 데이터셋

| 카테고리 | 상품 수 | 리뷰 수 |
|---|---:|---:|
| Appliances | 10,000 | 65,618 |
| Clothing_Shoes_and_Jewelry | 10,000 | 37,006 |
| Grocery_and_Gourmet_Food | 10,000 | 75,711 |
| 전체 | 30,000 | 178,335 |

상품 payload와 리뷰 payload는 JSONB로 저장한다. 상품은 category 및 parent_asin으로 연결하고 리뷰에는 안정적인 review_key를 둔다. 리뷰 응답에서 user_id는 제외한다.

## API 계약

- GET /healthz
- GET /v1/categories
- GET /v1/categories/{category}/products?limit=&offset=
- GET /v1/categories/{category}/products/{parent_asin}
- GET /v1/categories/{category}/reviews?parent_asin=&rating=&limit=&offset=

목록은 기본 50개, 최대 200개이며 offset은 0 이상이다. 리뷰 rating은 1부터 5까지 허용한다. 목록 응답에는 dataset_version, items, limit, offset, total이 포함된다.

## 완료 항목

- manifest와 JSONL을 검증하는 전체 스냅샷 적재 구현
- 적재를 단일 트랜잭션으로 수행하고 오류 시 롤백
- amzdata_importer와 읽기 전용 amzdata_api 역할 분리
- FastAPI 저장소를 PostgreSQL 기반으로 구성
- systemd API 서비스의 PostgreSQL 환경 연결
- 상품, 리뷰, 카테고리 API 응답 확인
- 운영 문서와 실행 명령을 한국어로 정리

## 운영 확인

PostgreSQL 컨테이너의 준비 상태, API의 /healthz 응답, 카테고리별 데이터 건수를 확인한다. 현재 RAG용 rag 스키마와 검색 테이블은 아직 생성하지 않았다.

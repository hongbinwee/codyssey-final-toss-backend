# Amazon Reviews 백엔드 연동 설계

**작성일:** 2026-10-14
**상태:** 연동 구현 전 검토안

## 1. 배경

Toss Final Project의 Amazon Reviews API는 읽기 전용 FastAPI 서비스다. API는 PostgreSQL toss_rag 데이터베이스의 amzdata 스키마에서 카테고리, 상품, 리뷰를 조회한다. 현재 선별 스냅샷은 상품 30,000개와 리뷰 178,335개다.

제공 경로는 다음과 같다.

- GET /healthz
- GET /v1/categories
- GET /v1/categories/{category}/products?limit=&offset=
- GET /v1/categories/{category}/products/{parent_asin}
- GET /v1/categories/{category}/reviews?parent_asin=&rating=&limit=&offset=

목록 응답은 dataset_version, items, limit, offset, total을 제공하며 페이지 크기는 최대 200이다.

## 2. 목표 구조

백엔드는 서버 측 HTTP 클라이언트로 원본 API를 호출한다. 원본 API는 PostgreSQL amzdata 스키마를 읽고, 향후 RAG 수집 작업은 같은 toss_rag 데이터베이스의 rag 스키마에 전용 역할로 기록한다. 백엔드는 원본 데이터베이스 비밀번호를 받지 않는다.

백엔드 서비스와 API가 같은 사설 네트워크에 있으면 http://172.30.1.53:8001을 사용한다. 외부 역방향 프록시를 통과해야 하는 호출자는 https://spark.chanuk.theworkpc.com을 사용한다. 외부 주소의 접근 가능 여부는 Nginx Proxy Manager 접근 목록의 허용 IP에 따라 달라진다.

## 3. 연결 설정

- API 기본 주소는 AMAZON_REVIEWS_API_BASE_URL 환경 변수에서 읽는다.
- 환경별 호스트를 소스 코드에 고정하지 않는다.
- HTTP 연결 및 응답 제한 시간을 설정한다.
- 원본 API 데이터베이스 계정이나 PostgreSQL 비밀번호를 백엔드에 복사하지 않는다.

## 4. 수집 동작

1. 카테고리를 조회한 뒤 상품 목록을 limit과 offset으로 순회한다.
2. 각 상품에 대해 rating 1부터 5까지 리뷰를 요청한다.
3. 평점별 최대 8개, 상품별 최대 40개 리뷰를 저장한다. 특정 평점에 원본 리뷰가 부족하면 부족한 상태를 유지한다.
4. 상품은 category와 parent_asin으로, 리뷰는 category와 review_key로 식별한다.
5. dataset_version을 함께 저장하고 동일 스냅샷을 재수집해도 중복 레코드가 생기지 않게 한다.

## 5. 오류 처리와 접근 제어

연결 실패와 일시적인 502, 503, 504에는 제한된 횟수로 지수형 대기 후 재시도한다. 400과 404는 재시도하지 않는다. 리뷰 원문을 로그에 과도하게 남기지 않는다. /healthz는 연결 확인에 사용하며 원본 API 장애는 백엔드의 의존 서비스 오류로 전달한다.

외부 도메인은 Nginx Proxy Manager를 통과한다. 호출자의 공인 IP가 접근 목록에 허용되어야 한다. 이 작업 환경에서 외부 도메인을 확인한 요청은 HTTP 403을 반환했으므로, 실제 호출 서버의 허용 IP로 별도 연결 확인이 필요하다. 사설망 호출은 내부 기본 주소를 사용한다.

## 6. 범위

- API 호출 클라이언트와 페이지 수집 구현
- 평점별 리뷰 균형 수집과 멱등 저장
- 원본 API 인증이나 응답 계약 변경
- Nginx Proxy Manager 접근 목록 변경
- 임베딩 모델, 청킹 정책, 검색 색인 구현

검색 스키마와 수집 작업의 구현 계획은 백엔드의 실제 실행 구조가 정해진 뒤 별도로 작성한다.

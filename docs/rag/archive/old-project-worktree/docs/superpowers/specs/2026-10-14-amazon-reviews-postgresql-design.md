# Amazon Reviews PostgreSQL 저장소 설계

**작성일:** 2026-10-14
**상태:** 운영 구성 및 데이터 검증 완료

## 1. 목적

Amazon Reviews'23 원본 상품·리뷰를 PostgreSQL에 저장하고, 기존 읽기 전용 API와 향후 RAG 수집 작업이 안정적으로 사용할 저장 구조와 권한을 정의한다.

## 2. 서버와 데이터베이스

- PostgreSQL 18.6을 Docker 컨테이너 amazon-reviews-postgres로 실행한다.
- 데이터베이스 이름은 toss_rag이다.
- Amazon 원본 테이블은 amzdata 스키마에 둔다.
- 향후 RAG 테이블은 rag 스키마에 둔다. rag 스키마는 아직 생성하지 않았다.
- 데이터 파일은 프로젝트의 data/amzdata/postgres/에 영구 보관한다.
- 호스트 포트 5432는 127.0.0.1에만 바인딩한다.

## 3. 테이블

amzdata.metadata는 데이터셋 버전과 전체 건수를 저장한다. amzdata.products는 category와 parent_asin을 기본 키로 사용하고 원본 상품 JSON을 JSONB로 보관한다. amzdata.reviews는 category와 review_key를 기본 키로 사용하며 category와 parent_asin으로 상품에 연결한다. 리뷰 원본 JSON도 JSONB로 저장하고 rating, parent_asin 조회용 인덱스를 둔다.

현재 적재된 데이터는 상품 30,000개와 리뷰 178,335개다. Appliances는 상품 10,000개와 리뷰 65,618개, Clothing_Shoes_and_Jewelry는 상품 10,000개와 리뷰 37,006개, Grocery_and_Gourmet_Food는 상품 10,000개와 리뷰 75,711개다.

## 4. 역할과 접근

amzdata_importer는 데이터 적재에 사용한다. amzdata_api는 API 전용 읽기 역할이며 amzdata 스키마에서 SELECT 권한만 가진다. 기본 권한도 설정해 재적재 뒤 API 조회 권한이 유지되도록 한다. 각 계정의 비밀번호는 Git에 넣지 않고 별도 환경 파일로 관리한다.

## 5. 적재와 서비스

적재기는 manifest와 JSONL을 검증하고 상품·리뷰 전체 스냅샷을 단일 트랜잭션으로 저장한다. 행 수가 manifest와 일치할 때만 데이터셋 metadata를 갱신하고 커밋한다. 오류가 발생하면 트랜잭션을 롤백한다.

FastAPI 서비스는 AMZDATA_DATABASE_URL 환경 변수로 읽기 전용 연결을 설정한다. systemd 서비스는 data/amzdata/api.env를 읽고 내부 주소 172.30.1.53:8001에서 실행된다. API 경로, 응답 필드, 정렬, 페이지네이션, 오류 상태 코드는 저장소 구현과 분리해 유지한다.

## 6. 검증 기준

- PostgreSQL 컨테이너가 정상 상태이며 데이터가 재시작 후에도 유지된다.
- 카테고리별 건수의 합이 전체 적재 건수와 일치한다.
- API 역할은 원본 데이터를 읽을 수 있고 쓰기 권한은 없다.
- 상태 확인, 카테고리, 상품, 리뷰 API가 같은 기존 계약으로 응답한다.
- RAG 저장소는 rag 스키마와 별도 역할로 구성한다.

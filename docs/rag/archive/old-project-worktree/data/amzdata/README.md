# Amazon Reviews'23 선별 데이터

`curated/`에는 카테고리별로 균등하게 무작위 추출한 상품 메타데이터 10,000개와 상품별 최대 40개 리뷰가 있습니다. 전체 샘플은 상품 30,000개, 리뷰 178,335개입니다.

| 카테고리 | 상품 수 | 리뷰 수 |
|---|---:|---:|
| `Clothing_Shoes_and_Jewelry` | 10,000 | 37,006 |
| `Grocery_and_Gourmet_Food` | 10,000 | 75,711 |
| `Appliances` | 10,000 | 65,618 |

리뷰 표본은 정수 평점(1–5)마다 최대 8개를 유지합니다. 특정 평점의 리뷰가 충분하지 않은 상품은 40개보다 적을 수 있습니다. 상품과 리뷰는 `parent_asin`으로 연결합니다.

선별 JSONL 파일은 약 145 MiB입니다. 원본 압축 카테고리 파일(전체 약 13.45 GB)은 UCSD 공식 데이터 호스트에서 스트리밍으로 읽었으며 로컬에 보관하지 않았습니다. 상품 이미지 필드는 URL만 남겼고 이미지 파일은 내려받지 않았습니다. `manifest.json`에는 원본 주소와 크기, 행 수, 표본 추출 방법, 출력 파일명이 기록되어 있습니다.

`python3 extract_sample.py`를 실행하면 같은 난수 시드로 선별을 다시 수행합니다. 이 명령은 원본 압축 파일을 다시 읽으므로 일반적인 API 데이터 갱신에는 사용하지 않습니다.

## PostgreSQL과 데이터 구분

API가 조회하는 원본 데이터는 PostgreSQL `toss_rag` 데이터베이스의 `amzdata` 스키마에 있습니다. 향후 RAG 테이블은 별도 `rag` 스키마로 구분하도록 설계했습니다. 현재 전환에서는 RAG 테이블이나 벡터 확장을 만들지 않았습니다.

API 계정은 읽기 전용이고, JSONL 적재기는 별도 계정을 사용합니다. PostgreSQL은 `127.0.0.1:5432`에서만 접속할 수 있습니다. 외부에서 데이터를 요청할 때는 PostgreSQL에 직접 연결하지 말고 기존 HTTP API를 이용하세요.

비밀번호와 연결 주소가 들어 있는 `postgres.env`, `admin.env`, `importer.env`, `api.env`는 `data/amzdata/`에 로컬 전용으로 저장하며 Git에 포함하지 않습니다. 파일 권한은 소유자만 읽고 쓸 수 있도록 유지합니다. 예시 변수는 [Compose 환경 예시](../../deploy/amazon-reviews-postgres.env.example)를 참고하세요.

## PostgreSQL 시작과 스키마 준비

프로젝트 최상위 디렉터리에서 실행합니다.

```bash
docker compose \
  --env-file data/amzdata/postgres.env \
  -f deploy/amazon-reviews-postgres.yml up -d

set -a
. data/amzdata/admin.env
set +a
PYTHONPATH=src .venv/bin/python -m toss_ads.amzdata.bootstrap
```

첫 명령은 PostgreSQL 컨테이너를 시작합니다. 다음 명령은 `amzdata` 스키마, 적재 계정, 읽기 전용 API 계정과 권한을 준비합니다. 비밀번호는 명령행 인수로 전달되지 않습니다.

## JSONL 스냅샷 적재

`curated/`의 JSONL 파일이 재현 가능한 원본 스냅샷입니다. 전체 데이터 적재 명령은 다음과 같습니다.

```bash
set -a
. data/amzdata/importer.env
set +a
PYTHONPATH=src .venv/bin/python -m toss_ads.amzdata.importer \
  --source data/amzdata
```

적재기는 manifest와 JSONL 행을 확인한 뒤 PostgreSQL의 단일 트랜잭션에서 기존 `amzdata` 스냅샷을 교체합니다. 실패하면 변경 사항을 롤백하고 직전 스냅샷을 보존합니다. 완료되면 데이터셋 버전과 카테고리별 건수를 출력합니다.

## API와 서비스 확인

API 서버는 `amazon-reviews-api` systemd 서비스로 실행됩니다. 현재 API 조회는 PostgreSQL의 읽기 전용 계정을 사용합니다.

```bash
sudo systemctl status amazon-reviews-api
sudo journalctl -u amazon-reviews-api -f
curl --fail-with-body http://172.30.1.53:8001/healthz
```

API 주소와 모든 경로, 매개변수, 응답 예시는 [API 명세](../../docs/amazon-reviews-api.md)를 참고하세요.

PostgreSQL 데이터는 `data/amzdata/postgres/`에 영구 보관됩니다. 컨테이너를 재생성해도 이 디렉터리의 데이터는 유지됩니다. 접속 비밀값은 Git에서 제외된 환경 파일에 저장하고 파일 권한을 소유자 전용으로 제한합니다.

출처: [Amazon Reviews'23](https://amazon-reviews-2023.github.io/). 데이터를 사용할 때 데이터셋 저자를 인용해 주세요.

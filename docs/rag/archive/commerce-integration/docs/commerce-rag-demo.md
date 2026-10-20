# 격리된 전체 상품 Commerce RAG 데모

이 데모는 현재 Commerce `products`와 `reviews` 전체 활성 레코드를 읽고, 상품 ID와 카테고리를 유지해 별도 RAG DB에 색인합니다. 색인 단계의 Commerce DB 트랜잭션은 read-only이며, RAG 쓰기는 전용 색인 DB에만 적용합니다. 별도 Commerce API DB에는 상품·가격·옵션·재고를 조회할 때만 연결합니다.

- Commerce fixture: `hongbinwee/codyssey_final-mission-main` commit `781e78597843859299be2bb7278e06219595e9b7`
- 현재 검증된 카탈로그: 활성 상품 78개, 리뷰 1,089개, 7개 상품군
- Commerce PostgreSQL: `127.0.0.1:15436/commerce`
- RAG PostgreSQL: `127.0.0.1:15437/toss_rag`
- Existing earphone-only RAG API: `127.0.0.1:8002` (left unchanged)
- Isolated full-catalog RAG API: `127.0.0.1:18002`
- Commerce web/API: `127.0.0.1:13001`

## 1. Commerce 저장소 준비

별도 경로에 저장소 전체를 clone하고 지정된 fixture commit으로 고정합니다.

```bash
git clone https://github.com/hongbinwee/codyssey_final-mission-main.git /path/to/codyssey_final-mission-main
git -C /path/to/codyssey_final-mission-main checkout 781e78597843859299be2bb7278e06219595e9b7
```

## 2. 로컬 비밀값과 격리된 DB 시작

RAG 저장소 루트에서 실행합니다. 로컬 파일은 `.gitignore` 처리되어 있습니다. 비밀번호는 각각 새로 생성하고, 터미널 출력이나 Git에 남기지 마세요.

```bash
mkdir -p .commerce-rag-demo.local
cp deploy/commerce-rag-demo.env.example .commerce-rag-demo.local/compose.env
chmod 600 .commerce-rag-demo.local/compose.env
```

`compose.env`의 세 비밀번호를 채우고, `RAG_DATABASE_URL`과 `DATABASE_URL`의 사용자명/비밀번호를 percent-encode된 같은 값으로 갱신합니다. Compose 실행 전에 project `commerce-rag-demo-20261015`, 생성될 컨테이너·볼륨 이름, 그리고 loopback 포트 `15436`, `15437`, `13001`, `18002`가 사용 중이 아닌지 확인합니다. 하나라도 이미 사용 중이면 실행을 중단하고 project 이름과 포트를 새 값으로 바꿉니다. 기존 컨테이너나 볼륨을 중지·재사용하지 않습니다.

```bash
docker compose --env-file .commerce-rag-demo.local/compose.env \
  -f deploy/commerce-rag-demo.compose.yaml up -d
```

새 Commerce DB의 system identifier를 읽어 안전 preflight 기준값으로 기록합니다. 이 파일은 local-only이며 Commerce 웹 서버를 띄울 때 함께 로드합니다.

```bash
system_identifier=$(docker compose --env-file .commerce-rag-demo.local/compose.env \
  -f deploy/commerce-rag-demo.compose.yaml exec -T commerce-postgres \
  psql -U commerce_demo -d commerce -Atqc 'SELECT system_identifier FROM pg_control_system()')
case "$system_identifier" in ''|*[!0-9]*) echo 'Commerce DB identity 확인 실패' >&2; exit 1;; esac
umask 077
printf 'RAG_DEMO_EXPECTED_SYSTEM_IDENTIFIER=%s\n' "$system_identifier" \
  > .commerce-rag-demo.local/identity.env
chmod 600 .commerce-rag-demo.local/identity.env
```

RAG DB의 schema와 runtime role을 bootstrap합니다. Admin URL은 새 staging DB에만 연결합니다.

```bash
set -a
. .commerce-rag-demo.local/compose.env
set +a
export RAG_ADMIN_DATABASE_URL="postgresql://postgres:${RAG_POSTGRES_PASSWORD}@127.0.0.1:15437/toss_rag"
RAG_ROLE_PASSWORD="$RAG_ROLE_PASSWORD" PYTHONPATH=src python3 -m toss_ads.rag.bootstrap
```

Commerce DB에 migration과 합성 seed를 넣습니다. 이 명령은 위의 새 `commerce` 데이터베이스 URL을 사용합니다.

```bash
cd /path/to/codyssey_final-mission-main
npm ci
DATABASE_URL="$DATABASE_URL" npm run db:migrate -- --phase=6
DATABASE_URL="$DATABASE_URL" npm run db:seed -- --phase=4
DATABASE_URL="$DATABASE_URL" npm run db:seed:demo
```

## 3. 현재 Commerce 전체 카탈로그 색인과 API 실행

Commerce DB는 읽기 전용 transaction으로 조회하고 RAG DB만 색인합니다. 실제 색인에는 `--category`를 주지 않아야 현재 활성된 모든 카테고리가 포함됩니다. product source API URL은 필요하지 않습니다.

```bash
cd /path/to/toss-ads-project/codyssey-final-toss-backend
set -a
. .commerce-rag-demo.local/compose.env
set +a
export COMMERCE_DATABASE_URL="$DATABASE_URL"
FASTEMBED_CACHE_PATH=.commerce-rag-demo.local/fastembed \
  PYTHONPATH=src python3 -m toss_ads.rag index --commerce-database
```

같은 runtime DB URL로 RAG API를 시작합니다.

```bash
RAG_DATABASE_URL="$RAG_DATABASE_URL" \
FASTEMBED_CACHE_PATH=.commerce-rag-demo.local/fastembed \
PYTHONPATH=src python3 -m toss_ads.rag serve --host 127.0.0.1 --port 18002
```

Commerce app은 시작 전 `commerce-db-v1:full:` marker를 확인하므로 이어폰 전용 API `8002`는 통과하지 않습니다. 앱의 `DATABASE_URL`은 이 색인을 만든 같은 Commerce DB `15436`을 가리켜야 RAG 결과의 상품 ID를 실제 상품·variant로 hydrate할 수 있습니다. 리뷰 1,089개는 현재 모두 `SYNTHETIC`이므로 데모 데이터로 표시되며 실제 구매자 리뷰로 간주하지 않습니다. 브라우저 실행과 검증은 [Commerce RAG 데모 안내](../../commerce-storefront/docs/commerce-rag-demo.md)를 따릅니다. 검색, 상품 상세, variant, 장바구니를 확인하고 checkout은 진행하지 않습니다.

## 4. 종료

각 Compose 서비스는 고유 project에 속합니다. 데모를 멈출 때는 같은 env/config로 해당 project 서비스만 중지하고 볼륨은 보존합니다.

```bash
docker compose --env-file .commerce-rag-demo.local/compose.env \
  -f deploy/commerce-rag-demo.compose.yaml stop
```

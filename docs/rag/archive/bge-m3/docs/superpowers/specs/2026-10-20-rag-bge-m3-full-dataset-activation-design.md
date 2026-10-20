# test_items2 전체 BGE-M3 하이브리드 검색 활성화 설계

작성일: 2026-10-20
상태: 채팅 설계 승인 완료, 문서 검토 대기

## 목표

활성 `test_items2` 실행의 1,500개 상품 전체에서 BM25와 BGE-M3 dense 검색을 함께 사용한다. 기존 청크와 MiniLM 임베딩을 보존하고, 현재 준비된 BGE-M3 벡터를 재사용해 누락된 카테고리만 추가한다. 전체 BGE 프로필이 준비되기 전에는 서비스 검색 모델을 전환하지 않는다.

검색 요청은 기존과 같이 BM25를 실행하고, 설정된 임베딩 모델로 만든 질의 벡터를 dense 검색에 사용한다. BGE-M3 구성에서는 두 채널을 기존 상품 단위 RRF(`k=60`)로 합친다. BGE-M3의 sparse·ColBERT 출력은 사용하지 않는다.

## 확인된 현재 상태

읽기 전용으로 `5432/toss_rag`의 실행을 확인했다. `15436`에는 연결하지 않았다.

| 카테고리 | 상품 수 | 청크 수 | 현재 BGE-M3 벡터 |
| --- | ---: | ---: | --- |
| beauty | 781 | 78,595 | 준비 완료 |
| fashion | 269 | 11,566 | 없음 |
| food | 182 | 13,409 | 없음 |
| living | 268 | 10,536 | 없음 |
| **전체** | **1,500** | **114,106** | **35,511개 추가 필요** |

- 대상 실행 ID: `e925490f-4f34-4c03-9248-eb9ebdfcde48`
- 데이터 버전: `test_items2:v6.1-review-refined:sha256=94681a28271ca9b1:products=1500:reviews=46100`
- 현재 실행은 `active`이고 `index_runs.embedding_model`은 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`다.
- 현재 `product-rag-api` 컨테이너의 `RAG_EMBEDDING_MODEL`도 MiniLM이다.
- BGE 프로필은 `(run_id, embedding_model)` 키로 하나만 허용하며 현재 `category_scope=beauty`, `status=ready`, `chunk_count=78,595`다.
- BM25와 기존 384차원 MiniLM 임베딩은 같은 활성 실행의 모든 114,106개 청크에 유지돼 있다.
- 기존 BGE 비교는 beauty 범위의 긍정 질의 10개와 OOD 질의 2개만 다룬다. 다른 세 카테고리의 정답 라벨은 현재 비교 자료에 없다.

## 고려한 접근

| 접근 | 장점 | 비용 및 위험 | 선택 |
| --- | --- | --- | --- |
| 기존 실행의 BGE 프로필을 전체 범위로 넓히고 누락 벡터만 추가 | 이미 만든 beauty 벡터와 전체 BM25·MiniLM 인덱스를 재사용한다. 청크 경계와 데이터 버전이 동일하다. | 프로필 범위를 안전하게 넓히고, 전체 준비 전까지 BGE 검색을 차단해야 한다. | **선택** |
| 새 BGE 전용 활성 실행을 처음부터 다시 만든다 | 기존 실행과 모델별 실행을 완전히 분리한다. | 소스 재수집·청킹·MiniLM 재계산까지 중복되고 전환 작업이 더 크다. | 미선택 |
| 카테고리마다 모델과 프로필을 따로 전환한다 | 한 카테고리씩 점진 전환할 수 있다. | 프로필 키, 상태 확인, 검색 설정에 카테고리별 라우팅을 추가해 복잡성이 커진다. | 미선택 |

## 선택한 설계

### 전체 범위의 BGE 프로필

기존 `(run_id, embedding_model)` 프로필을 같은 실행·모델에서 전체 카테고리 범위로 확장한다. `category_scope='*'`를 전체 카테고리 표기로 정하고, 기존 beauty 프로필을 `building`으로 바꾸며 기대 청크 수를 114,106으로 갱신한다. 이 프로필 키 구조에서는 동일 실행·모델의 beauty 프로필과 전체 프로필을 동시에 둘 수 없으므로, 기존 beauty 비교 산출물은 보고서와 평가 JSON에 보존한다.

프로필 확장 전에 실행 ID와 데이터 버전을 확인하고, 기존 beauty 벡터 수가 78,595인지 확인한다. 기존 벡터 행은 삭제하거나 덮어쓰지 않는다. 임베더는 현재와 같은 `BAAI/bge-m3` revision `5617a9f61b028005a4858fdac845db406aefb181`, 1,024차원 dense 출력, 최대 128 입력 토큰을 사용한다.

인덱서는 전체 실행의 `embedding_text`를 읽고, 이미 벡터가 있는 청크는 건너뛰며 누락된 35,511개를 배치로 추가한다. 대상 청크 수와 저장 벡터 수가 모두 114,106일 때만 프로필을 `ready`로 만든다. 중단되면 기존 행을 보존하고, 누락분부터 재개한다. `building` 또는 `failed` 상태의 BGE 프로필로는 서비스가 검색하지 않는다. 현재 MiniLM 서비스는 프로필 확장 중에도 계속 사용할 수 있다.

### 서비스 검색과 모델 선택

- `RAG_EMBEDDING_MODEL=BAAI/bge-m3` 설정에서 BGE-M3 질의 임베더를 생성한다. 기본 환경은 명시적인 모델 설정을 사용해 다른 설치가 의도치 않게 바뀌지 않게 한다.
- 준비된 BGE 프로필에 대해 `RagStore.search_embedding_vector`로 1,024차원 dense 후보를 찾는다. 요청 카테고리 필터가 있으면 그 카테고리를 적용하고, 필터가 없으면 네 카테고리 전체에서 검색한다.
- BM25 검색은 기존 ParadeDB 인덱스를 사용한다. BM25와 dense 결과는 기존 상품 단위 RRF(`k=60`)로 합친다. 리뷰 의도에 따른 review 전용 채널도 동일한 BGE dense 검색을 사용한다.
- FastAPI readiness와 검색 경로는 `index_runs.embedding_model`의 생성 당시 기록만으로 BGE 사용을 거부하지 않는다. 활성 실행에 일치하는 전체 범위 BGE 프로필이 있고, 상태가 `ready`이며, 실제 벡터 수가 전체 청크 수와 일치하는지 확인한다. MiniLM 설정에서는 기존 384차원 검색과 활성 실행 모델 일치를 유지한다.
- 현재 컨테이너는 전체 BGE 적재와 애플리케이션 변경이 완료된 뒤 새 이미지로 교체하고 BGE 설정으로 시작한다. 완료 전에는 서비스 설정을 전환하지 않는다.

### 롤백

기존 MiniLM 벡터와 코드 경로는 유지한다. 문제가 발생하면 컨테이너의 `RAG_EMBEDDING_MODEL`을 MiniLM으로 되돌리고 기존 이미지 또는 새 이미지를 재시작한다. BGE 벡터는 삭제하지 않는다. `index_runs.embedding_model`과 활성 run 상태는 변경하지 않는다.

## 성공 기준 및 검증 범위

- 전체 네 카테고리의 BGE 프로필이 `ready`이고 저장 벡터 수가 114,106이다.
- `/healthz`가 BGE 설정과 전체 범위 프로필의 준비 여부를 반영한다.
- 각 카테고리 필터 검색과 카테고리 없는 전체 검색에서 BM25와 BGE dense 채널을 모두 사용한다.
- 전체 프로필이 준비되기 전까지 MiniLM 서비스가 계속 동작하고, BGE 부분 색인은 서비스 준비 상태로 보고되지 않는다.
- 기존 beauty 비교 결과는 보존한다. 현재 다른 카테고리의 평가 라벨이 없으므로, 이 전환만으로 전체 1,500개에 대한 검색 정확도를 주장하지 않는다. 전체 카테고리의 품질 비교는 카테고리별 질의와 정답 라벨을 마련한 별도 평가 작업으로 다룬다.

## 운영 비용과 제한

- 기존 처리량 7.018 청크/초를 적용하면 남은 35,511개는 순수 임베딩 기준 약 1시간 24분으로 추정된다. 이전 실행의 DB 저장·기타 경과를 포함한 처리량 기준으로는 약 1시간 30분이며, 실제 시간은 달라질 수 있다.
- 이전 12개 질의의 단일 비교에서 BGE query 임베딩 p50은 약 71ms, dense 검색 p50은 약 702ms, hybrid 검색 p50은 약 82ms였다. 작은 표본의 관측치이므로 SLA나 부하 성능으로 해석하지 않는다.
- 전체 BGE 프로필은 1,024차원 벡터 약 114,106개와 HNSW 인덱스를 사용한다. 기존 beauty 벡터 저장분 외에 fashion·food·living 약 35,511개 벡터의 DB 행과 인덱스 공간이 추가된다.
- 변경 범위는 기존 test_items2 실행의 검색 경로와 BGE 보조 프로필이다. 재청킹, 소스 데이터 재수집, MiniLM 데이터 삭제, BGE sparse·ColBERT 검색, 답변 생성기와 리랭커는 포함하지 않는다.
- DB 작업은 `5432/toss_rag`만 대상으로 한다. GitHub push와 main 병합은 별도 사용자 지시와 PR 절차를 따른다.

## 구현 시 주요 경계

- 프로필 확장 및 범위 계산은 `src/toss_ads/rag/store.py`와 `src/toss_ads/rag/embedding_indexer.py`에서 처리한다.
- 모델 선택, BGE dense 라우팅, readiness는 `src/toss_ads/rag/embeddings.py`, `src/toss_ads/rag/config.py`, `src/toss_ads/rag/retriever.py`, `src/toss_ads/rag/api.py`에 반영한다.
- 런타임 설정과 로컬 컨테이너 교체 절차는 `deploy/product-rag-runtime.env.example` 및 서비스 배포 지침에 기록한다.
- 기존 사용자 미커밋 변경은 구현·스테이징에서 분리해 보존한다.

## 참고 자료

- [beauty 범위 비교 보고서](../../rag-bge-m3-test-items2-beauty-2026-10-20.md)
- [전체 BGE 프로필 적재 요약](../../../reports/rag-bge-m3-test-items2-beauty-2026-10-20-index.json)
- [현재 BGE 저장 스키마](../../../deploy/product-rag-bge-m3-embeddings.sql)
- [기존 dense/hybrid 비교 설계](2026-10-20-rag-bge-m3-dense-hybrid-design.md)

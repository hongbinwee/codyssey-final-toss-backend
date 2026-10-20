# `test_items/beauty` 임베딩 모델 비교

작성일: 2026-10-19  
목적: 현재 BM25 검색에 임베딩 모델을 결합했을 때의 검색 품질과 로컬 CPU 비용 비교

## 요약

- 이 비교에서 E5-large가 Hit@1, Hit@5, MRR@5, Precision@5에서 가장 높았습니다. 다음 DB 색인을 만들 때 우선 재평가할 후보로 권합니다.
- BGE-M3는 Recall@5가 가장 높았지만 E5와 차이는 약 0.015이며, 10개 긍정 질의만으로 우열을 확정하기 어렵습니다. 로컬 문서 임베딩 시간은 E5보다 약 1.9배 길었습니다.
- 테스트한 세 대안(E5, BGE-M3, Qwen3)은 **BM25를 대체한 것이 아니라**, 고정한 BM25 결과와 각 임베딩 결과를 RRF로 합친 구성입니다.
- 모든 구성에서 범위 밖 질의 2개에도 상품을 반환했습니다. 임베딩 모델만 교체해서는 범위 밖 질의 거절 문제가 해결되지 않았습니다.
- 아래 수치는 DB 변경 전 고정한 `test_items/beauty` 스냅샷에 대한 탐색 결과입니다. 새 DB 색인에 대한 최종 수치로 해석하면 안 됩니다.

## 데이터와 평가 방법

| 항목 | 값 |
| --- | --- |
| 데이터 버전 | `test_items:sha256=4e9924492dcb536e:products=180:reviews=4737` |
| 범주·규모 | `beauty`, 상품 180개, 리뷰 4,737개, 청크 6,741개 |
| 평가 질의 | 긍정 10개, 범위 밖 2개, 총 12개 |
| 반환 수 | 상품 기준 Top 5 |
| BM25 스냅샷 | 이전 고정 run `49537fff-9b05-4b9c-aed1-c4e690a4f689`에서 저장한 질의별 BM25 Top 20 |
| 평가 라벨 | 기존 제목 정규식으로 만든 임시 정답 상품 ID. 사람 검수 라벨은 아님 |

긍정 질의는 컨실러, 블러셔, 아이라이너, 브로우, 립밤, 수분 크림, 트러블 토너, SPF 50 비비크림, 특정 상품명, 장벽 보습 크림입니다. 범위 밖 질의는 클렌징 오일과 기계식 키보드입니다. 라벨 생성 방식과 기존 결과는 [검색 품질 평가 JSON](../../reports/rag-search-quality-test-items-beauty-2026-10-17.json)에 있습니다.

각 임베딩 구성은 동일한 6,741개 청크를 임베딩한 뒤 벡터 유사도 Top 20을 뽑았습니다. 청크 결과를 상품 단위로 합치고, 고정 BM25 Top 20과 벡터 Top 20을 상품별 RRF(`k=60`)로 결합해 최종 Top 5를 만들었습니다. BM25 단독 행은 저장된 BM25 Top 20에서 중복 상품을 제거한 뒤 같은 평가 라벨로 Top 5를 계산한 기준선입니다.

E5에는 문서 `passage: `, 질의 `query: ` 접두어를 넣었습니다. 접두어 없이 돌린 초기 E5 결과는 제외했습니다. Qwen3 질의에는 모델 카드의 검색 지시문 템플릿을 적용했고, 문서에는 별도 접두어를 넣지 않았습니다. 비교 조건을 맞추기 위해 모든 모델의 입력 최대 길이는 128 토큰으로 제한했습니다.

## 검색 품질 결과

| 구성 | 차원 | Hit@1 | Hit@5 | Macro Recall@5 | Macro MRR@5 | Macro Precision@5 | OOD 상품 반환 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 단독 | — | 70% (7/10) | 80% (8/10) | 0.533 | 0.750 | 0.34 | 2/2 |
| BM25 + MiniLM-L12-v2 | 384 | 70% (7/10) | 80% (8/10) | 0.503 | 0.750 | 0.36 | 2/2 |
| BM25 + multilingual-e5-large | 1,024 | **80% (8/10)** | **90% (9/10)** | 0.583 | **0.850** | **0.44** | 2/2 |
| BM25 + BGE-M3 | 1,024 | 70% (7/10) | 90% (9/10) | **0.598** | 0.800 | 0.42 | 2/2 |
| BM25 + Qwen3-Embedding-0.6B | 1,024 | 70% (7/10) | 90% (9/10) | 0.536 | 0.800 | 0.42 | 2/2 |

`Hit@5`는 기대 상품이 하나라도 Top 5에 있던 질의 비율입니다. `Macro Recall@5`는 질의별 기대 상품 중 찾은 비율의 평균이고, `Macro MRR@5`는 첫 기대 상품의 순위를 반영합니다. `Macro Precision@5`는 질의마다 Top 5 중 기대 상품 수를 5로 나눈 뒤 평균한 값입니다.

기존 MiniLM 보고서의 Hit@1 7/10, Hit@5 8/10은 이 비교의 MiniLM 행과 일치합니다. BM25 단독도 같은 Hit 비율이지만, 이번 임시 라벨 기준 Recall@5는 0.533입니다. E5는 BM25 단독 대비 Hit@1과 Hit@5가 각각 10%p 높고 MRR도 높았습니다. BGE-M3의 Recall@5가 가장 높지만 E5와의 차이는 작습니다.

블러셔 질의는 BM25 단독과 MiniLM에서는 기대 상품을 찾지 못했지만 E5, BGE-M3, Qwen3에서는 찾았습니다. 립밤 질의는 BM25와 모든 임베딩 구성에서 기대 상품이 Top 5에 없었습니다. 립밤의 정답 라벨 범위와 상품명을 사람이 다시 확인할 필요가 있습니다.

## 임베딩 비용

아래 문서 임베딩 시간은 6,741개 청크의 임베딩 생성 시간입니다. 모델 시작 시간, DB 저장, pgvector 인덱스 생성은 포함하지 않습니다. 질의 시간은 12개 질의 임베딩의 p50/p95입니다.

| 모델 | 차원 | 문서 임베딩 시간 | 처리량 | 질의 임베딩 p50 / p95 |
| --- | ---: | ---: | ---: | ---: |
| MiniLM-L12-v2 | 384 | 33.8초 | 199.6 청크/초 | 5.7 / 10.2 ms |
| multilingual-e5-large | 1,024 | 456.3초 | 14.8 청크/초 | 55.6 / 67.4 ms |
| BGE-M3 | 1,024 | 879.6초 | 7.7 청크/초 | 145.6 / 167.9 ms |
| Qwen3-Embedding-0.6B | 1,024 | 894.6초 | 7.5 청크/초 | 92.8 / 154.5 ms |

측정은 이 작업 환경의 CPU에서 진행했습니다. MiniLM, E5, Qwen3는 FastEmbed ONNX 경로를 사용했고 BGE-M3는 Transformers CPU `bfloat16` 경로를 사용했습니다. 벡터 Top 20 검색 시간도 메모리에 올린 NumPy 행렬에서 쟀으므로 실제 DB 벡터 인덱스나 서비스 API 지연 시간으로 볼 수 없습니다. CPU 부하와 실행 경로가 완전히 통제된 운영 성능 시험도 아닙니다.

## 추천 구성과 모델 후보

### 검색 구성 5개

| 구성 | 추천 상황 | 검증 상태 |
| --- | --- | --- |
| BM25 단독 | 현재 색인과 호환되는 기준선, 키워드·상품명 검색 | 고정 스냅샷으로 계산 |
| BM25 + MiniLM 384 + RRF | 차원 변경 없이 기존 하이브리드 유지 | 테스트 완료 |
| BM25 + multilingual-e5-large 1,024 + RRF | 현재 결과 기준 품질 우선 후보 | 테스트 완료, 우선 재평가 권장 |
| BM25 + BGE-M3 dense 1,024 + RRF | Recall 우선 후보. BGE의 sparse 기능은 이번 비교에 포함되지 않음 | dense 경로 테스트 완료 |
| BM25 + Qwen3-Embedding-0.6B 1,024 + RRF | instruction-aware 임베딩을 비교할 때 | 테스트 완료 |

이 구성들에는 리랭커와 답변 생성기가 없습니다. BGE-M3는 dense, sparse, multi-vector 검색을 지원하지만 여기서는 dense 검색만 BM25와 합쳤습니다.

### 임베딩 모델 후보 5개

| 우선순위 | 모델 | 차원 | 이번 비교 |
| ---: | --- | ---: | --- |
| 1 | `intfloat/multilingual-e5-large` | 1,024 | 테스트 완료. 품질과 비용의 균형 후보 |
| 2 | `BAAI/bge-m3` | 1,024 | 테스트 완료. 소규모 평가에서 Recall@5 최고 |
| 3 | `Qwen/Qwen3-Embedding-0.6B` | 1,024 | 테스트 완료. 이번 데이터에서는 E5 대비 뚜렷한 이점 없음 |
| 4 | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 384 | 현재 구성 기준선. 가장 빠른 문서 임베딩 |
| 5 | `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` | 768 | 후보만 정리했고 직접 테스트하지 않음 |

## 검색·임베딩·리랭킹·답변 생성 역할

- **검색기:** BM25는 단어 일치 기반 검색 알고리즘입니다. 임베딩 모델은 질의와 문서를 벡터로 바꾸고, 벡터 유사도로 의미 검색을 합니다. 현재 하이브리드 실험은 두 검색 결과를 RRF로 결합했습니다.
- **리랭커:** 검색기가 모은 후보와 질의를 쌍으로 비교해 순위를 다시 매기는 별도 모델입니다. `BAAI/bge-reranker-v2-m3`를 후보로 볼 수 있지만 이번 측정에는 넣지 않았습니다.
- **답변 생성기:** 검색 근거를 자연어 답변으로 작성하는 별도 LLM입니다. 현재 상품 검색 비교에는 답변 생성 단계를 포함하지 않았습니다.

따라서 이번에 비교한 E5, BGE-M3, Qwen3는 BM25를 대체하는 모델이 아니라 검색 파이프라인의 **임베딩 모델 자리**에 들어가는 후보입니다.

## DB·코드 변경 영향

현재 Backend 작업 트리에는 임베딩 차원 384가 고정되어 있습니다.

- [`embeddings.py`](../src/toss_ads/rag/embeddings.py#L9): `EMBEDDING_DIMENSION = 384`
- [`product-rag.sql`](../deploy/product-rag.sql#L80): `embedding vector(384)`
- [`store.py`](../src/toss_ads/rag/store.py#L182): 저장 벡터 차원 검사
- [`store.py`](../src/toss_ads/rag/store.py#L329): 검색 질의 벡터 차원 검사
- [`retriever.py`](../src/toss_ads/rag/retriever.py#L101): 검색기 차원 검사

1,024차원 모델을 실제 서비스에 넣으려면 모델 설정과 위 차원 검사를 함께 바꾸고, 전체 문서 청크를 새 모델로 다시 임베딩해 벡터를 재색인해야 합니다. 기존 벡터를 새 모델 벡터와 섞어 쓸 수는 없습니다. DB 전체를 교체할 필요가 있다는 뜻은 아니며, 새 차원의 벡터 컬럼/테이블과 새 색인을 만든 뒤 활성 색인을 전환하는 방식으로 진행할 수 있습니다. E5는 질의와 문서의 접두어 처리도 서비스 코드에 반영해야 합니다.

## 한계와 다음 평가

긍정 질의가 10개뿐이라 Hit@1이나 Hit@5는 질의 하나에 따라 10%p씩 움직입니다. 임시 제목 정규식 라벨은 사람이 판단한 상품 관련성과 다를 수 있습니다. 이번 숫자는 모델의 최종 정확도나 통계적으로 확정된 우열이 아닙니다. 특히 Recall 차이 0.015는 후보 선정 신호 정도로만 봐야 합니다.

DB 색인 변경이 끝나면 새 `dataset_version`에서 같은 질의와 정답 목록으로 다시 비교해야 합니다. 먼저 사람이 승인한 긍정·범위 밖 질의 라벨을 만들고, BM25 단독과 BM25+E5를 포함해 반복 측정하는 것을 권합니다. 범위 밖 질의 거절은 임베딩 교체와 별도로 임계값 또는 범주 제한을 평가해야 합니다.

이번 비교 과정에서는 DB 쓰기나 DDL을 실행하지 않았습니다. 고정 BM25 결과를 만든 뒤 모델 임베딩 평가는 저장한 스냅샷으로 오프라인에서 수행했습니다.

## 공식 모델 자료

- [multilingual-e5-large 모델 카드](https://huggingface.co/intfloat/multilingual-e5-large) — 1,024차원과 `query:` / `passage:` 접두어 사용 지침
- [BGE-M3 모델 카드](https://huggingface.co/BAAI/bge-m3) — dense, sparse, multi-vector 기능과 1,024차원 사양
- [Qwen3-Embedding-0.6B 모델 카드](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) — 100개 이상 언어, 최대 1,024차원, instruction-aware 입력
- [MiniLM-L12-v2 모델 카드](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2) — 384차원
- [paraphrase-multilingual-mpnet-base-v2 모델 카드](https://huggingface.co/sentence-transformers/paraphrase-multilingual-mpnet-base-v2) — 768차원
- [BGE reranker v2 M3 모델 카드](https://huggingface.co/BAAI/bge-reranker-v2-m3) — 질의와 문서를 함께 점수화하는 multilingual cross-encoder

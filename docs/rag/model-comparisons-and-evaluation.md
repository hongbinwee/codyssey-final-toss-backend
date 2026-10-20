# 모델 비교와 RAG 평가 기록 — BGE 운영 기준

[목차](README.md) · [원문 전체 목록](document-catalog.md)

**현재 운영 모델은 BGE-M3이며 전체 114,106개 벡터가 ready다(2026-10-20 18:25 KST 확인).** 아래의 MiniLM/E5/Qwen 결과는 비교 기준선과 과거 실험 기록이다. 운영 전환 완료와 전체 추천 정확도 평가 완료는 구분한다.

20:48 API 0.3.1 호환 복구와 HTTP/가격·재고 검사는 [복구 보고서](bge-api-compat-recovery-2026-10-20.md)에 추가했다. 아래 모델 비교 점수를 새로 평가하거나 변경한 것은 아니다.

## 1. 결과를 읽는 기준

발견한 자료에는 **임베딩 모델 비교 2묶음**, **BGE-M3 DB 검색 비교 1묶음**, 그리고 여러 시점의 검색·정책·출처 검사가 있다. 데이터, 질문, 라벨, 코드, 검색 경로가 달라 점수를 한 개의 “현재 정확도”로 합칠 수 없다.

- 대부분 상품명/유형 규칙으로 만든 **임시 정답**이며 사람 검수 gold가 없다.
- 임베딩 비교는 긍정 질문 10개와 OOD(목록/범위 밖) 2개다. 긍정 질문 하나가 Hit 비율 10%p를 바꾼다.
- Hit@5는 관련 상품이 다섯 개 안에 하나 있다는 뜻이며, 가격·용도·필수 옵션을 모두 충족했다는 뜻은 아니다.
- 출처/오프셋 무결성과 사용자 요구에 맞는 추천은 다른 평가 항목이다.
- 아래 표는 **저장된 결과를 정리한 것**이다. 이번 문서 작업에서 모델 평가를 새로 실행하지 않았다.

## 2. 비교 A — test_items/beauty, 2026-10-19

상품 180개 / 리뷰 4,737개 / 기존 96토큰 청크 6,741개. 긍정 10 + OOD 2, 결과 Top 5. 저장한 BM25 Top 20과 모델별 dense Top 20을 상품 단위 RRF(k=60)로 합쳤다.

| 구성 | 차원 | Hit@1 | Hit@5 | Recall@5 | MRR@5 | Precision@5 | OOD 반환 |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 | — | 70% | 80% | .533 | .750 | .340 | 2/2 |
| BM25 + MiniLM | 384 | 70% | 80% | .503 | .750 | .360 | 2/2 |
| BM25 + multilingual-e5-large | 1,024 | **80%** | **90%** | .583 | **.850** | **.440** | 2/2 |
| BM25 + BGE-M3 dense | 1,024 | 70% | **90%** | **.598** | .800 | .420 | 2/2 |
| BM25 + Qwen3-Embedding-0.6B | 1,024 | 70% | **90%** | .536 | .800 | .420 | 2/2 |

표의 Recall/MRR/Precision은 질문별 값을 평균한 macro 지표다. 이 표본에서는 E5의 상위 순위가 좋고 BGE-M3의 Recall이 가장 높았지만, 최종 모델의 우열을 확정한 결과는 아니다.

원문: [test_items 임베딩 비교](archive/bge-m3/docs/rag-embedding-model-comparison-test-items-beauty-2026-10-19.md).

### 로컬 CPU 비용

| 모델 | 6,741청크 문서 임베딩 | 청크/초 | 질문 임베딩 p50 / p95 |
|---|---:|---:|---:|
| MiniLM | 33.8초 | 199.6 | 5.7 / 10.2ms |
| E5-large | 456.3초 | 14.8 | 55.6 / 67.4ms |
| BGE-M3 | 879.6초 | 7.7 | 145.6 / 167.9ms |
| Qwen3-Embedding-0.6B | 894.6초 | 7.5 | 92.8 / 154.5ms |

문서 임베딩 시간은 모델 시작·DB 저장·DB 인덱스 생성을 제외한다. MiniLM/E5/Qwen은 ONNX FastEmbed, BGE는 Transformers CPU bfloat16 경로다. Dense 검색은 NumPy 메모리 행렬이므로 서비스 API 지연으로 읽지 않는다.

## 3. 비교 B — test_items2/beauty, 2026-10-19

상품 781개 / 리뷰 34,545개 / 기존 96토큰 청크 78,595개. 전체 test_items2 1,500상품 중 beauty만 평가했다. 긍정 10 + OOD 2, 상품 Top 5, BM25/dense Top 20, RRF(k=60).

| 구성 | 차원 | Hit@1 | Hit@5 | Recall@5 | MRR@5 | Precision@5 | OOD 반환 |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 | — | 60% | 100% | .540 | .767 | .400 | 2/2 |
| BM25 + MiniLM | 384 | 40% | 100% | .451 | .595 | .360 | 2/2 |
| BM25 + E5-large | 1,024 | **80%** | 100% | .620 | .883 | **.580** | 2/2 |
| BM25 + BGE-M3 dense | 1,024 | **80%** | 100% | **.627** | **.900** | **.580** | 2/2 |
| BM25 + Qwen3-Embedding-0.6B | 1,024 | **80%** | 100% | .608 | .883 | **.580** | 2/2 |

E5/BGE/Qwen이 이 표본에서 MiniLM보다 상위 순위가 좋았지만 모든 구성에서 OOD 두 건에도 상품을 반환했다. 큰 임베딩 모델만으로 무관한 상품 차단을 해결한 결과는 아니다.

원문: [Markdown](archive/bge-m3/docs/rag-embedding-model-comparison-test-items2-beauty-2026-10-19.md), [공유 PDF](archive/bge-m3/docs/rag-embedding-model-comparison-test-items2-beauty-2026-10-19.pdf).

### 로컬 CPU 비용

| 모델 | 78,595청크 문서 임베딩 | 청크/초 | 질문 임베딩 p50 / p95 |
|---|---:|---:|---:|
| MiniLM | 기존 DB 벡터 재사용 | 미측정 | 4.2 / 12.4ms |
| E5-large | 90.3분 | 14.50 | 21.6 / 27.2ms |
| BGE-M3 | 48.9분 | 26.81 | 135.2 / 143.9ms |
| Qwen3-Embedding-0.6B | 173.2분 | 7.56 | 53.0 / 58.9ms |

CPU 8 threads, 모델별 실행 경로 차이가 있다. 문서 시간은 DB 적재를 제외하며 dense는 NumPy exact cosine이다. 비교 A와 다른 실행 시점/환경의 측정치를 합쳐 고정 처리량이나 운영 SLA로 사용하지 않는다.

### 두 비교의 공통 통제 조건

- 청크는 기존 96토큰으로 고정했다. **청크 길이 비교 실험이 아니다.**
- 모든 모델 호출의 최대 입력은 128토큰이었다. 모델의 전체 장문 처리 능력을 평가한 것이 아니다.
- E5는 문서 `passage:`, 질문 `query:`를 사용했다. Qwen 질문은 검색 지시문 템플릿을 사용했다.
- BGE는 dense만 사용했다. sparse/ColBERT, cross-encoder 리랭커, 답변 생성 LLM은 포함하지 않았다.
- 비교 A와 B는 일부 긍정 질문·OOD·정답 목록도 다르다. 이전 데이터 대비 개선율로 해석하지 않는다.
- 10/19 문서의 “test_items2가 API에 미연결” 문구는 작성 당시 상태다. 현재 API 기본 연결은 [현재 구성](current-system.md)을 따른다.

## 4. 비교 C — BGE-M3 DB 검색, 2026-10-20

같은 test_items2/beauty 78,595청크에 별도 BGE 1,024차원 벡터를 저장한 후, **BM25 / BM25+BGE / BGE 단독**을 DB 경로에서 비교했다. 긍정 10 + OOD 2, Top 5, RRF(k=60). 모델 revision은 `5617a9f61b028005a4858fdac845db406aefb181`, 최대 입력 128토큰이다.

| 지표 | BM25 | BM25+BGE | BGE dense |
|---|---:|---:|---:|
| Hit@1 | 60% | **80%** | **80%** |
| Hit@5 | **100%** | **100%** | 90% |
| Macro Recall@5 | .5403 | **.6064** | .4694 |
| Macro MRR@5 | .7667 | **.8833** | .8333 |
| Macro Precision@5 | .4000 | **.5400** | .5000 |
| OOD 결과 반환 | 2/2 | 2/2 | 2/2 |

| 시간 측정 | BM25 | BM25+BGE | BGE dense |
|---|---:|---:|---:|
| 질문 임베딩 p50 / p95 | — | 70.544 / 122.615ms | 71.472 / 102.733ms |
| 검색 p50 / p95 | 54.520 / 67.430ms | 81.858 / 3,266.474ms | 702.144 / 772.439ms |

검색 시간은 질문 임베딩을 제외한다. 12번 단발 측정이므로 특히 p95는 재측정이 필요하다. 하이브리드 p95 약 3.27초가 기록됐다. 부하·워밍업·반복을 통제한 운영 지연 수치는 아니다.

벡터 적재의 마지막 재개 구간은 75,235청크 임베딩에 약 2시간 58분 41초, 전체 경과 약 3시간 8분 59초였다. 기존 3,360벡터와 앞선 중단 실행 시간은 이 구간 비용에 포함되지 않는다. 이 비용을 10/19 NumPy 실험 시간과 같은 조건의 측정으로 비교하지 않는다.

평가 중 BM25 준비 쿼리의 `Unsupported query shape` 오류를 발견하고 `prepare=False`로 회귀 확인한 기록도 있다. 해당 수정의 기록과 현재 배포 반영 여부는 구분한다. 18:25까지의 문서 작업은 운영 코드를 바꾸지 않았다. 이후 호환성 복구는 별도 보고서에 기록했다.

원문: [Markdown](archive/bge-m3/docs/rag-bge-m3-test-items2-beauty-2026-10-20.md), [PDF](archive/bge-m3/docs/rag-bge-m3-test-items2-beauty-2026-10-20.pdf), [전체 질의/응답 JSON](archive/bge-m3/reports/rag-bge-m3-test-items2-beauty-2026-10-20.json), [적재 결과](archive/bge-m3/reports/rag-bge-m3-test-items2-beauty-2026-10-20-index.json), [고정 질문/정답 fixture](archive/bge-m3/evals/fixtures/test_items2_beauty_bge_m3.json).

## 5. 전체 BGE 적재·운영 전환 기록

전체 test_items2의 **1,500상품 / 46,100리뷰 / 114,106청크**에 BGE 벡터를 준비했다. 기존 beauty 78,595개를 재사용하고 fashion/food/living **35,511개**를 추가했다. 재청킹하지 않았고 기존 MiniLM 벡터도 보존했다.

| 항목 | 기록 |
|---|---:|
| BGE 벡터 전체 | 114,106개 |
| beauty / fashion / food / living | 78,595 / 11,566 / 13,409 / 10,536 |
| 모델·차원 | BAAI/bge-m3, 1,024 |
| 프로필 | scope=*, ready |
| 추가 35,511개 순수 임베딩 | 8,473.861초, 약 2시간 21분 14초 |
| 추가 구간 경과 | 8,954.353초, 약 2시간 29분 14초 |
| 순수 처리량 | 4.191청크/초 |
| 해당 작업 CPU threads / 최대 RSS | 20 / 2,541.86MB |
| 카테고리 4개 + 전체 검색 smoke | 기록상 5/5 HTTP 200, 각각 5상품 |
| MiniLM 복구 후 BGE 복원 smoke | 기록상 passed |

위 시간은 **추가분의 비용**이며 전체 114,106개를 처음부터 임베딩한 총시간이 아니다. 이전 중단 실행까지의 총비용도 아니다. 현재 실행 상태와 BGE 범주별 실제 벡터 수는 별도 읽기 전용 조회로 다시 확인했다.

원문: [전체 적재·전환 보고서](archive/bge-m3-activated/reports/rag-bge-m3-test-items2-full-2026-10-20-index.json), [운영 기록](archive/bge-m3-activated/docs/rag-bge-m3-test-items2-full-operations.md), [새 실행 증거](evidence/runtime-snapshot-2026-10-20.json).

**전체 카테고리의 정확도·Recall·최종 추천 품질은 새로 측정된 수치가 없다.** Fashion/food/living의 사람 승인 라벨이 없으며 연결 smoke를 정확도로 바꾸지 않는다. Beauty의 80% Hit@1을 전체 1,500상품의 80% 정확도로 표기하지 않는다.

## 6. 그 밖의 평가를 시간순으로 읽기

| 자료/시점 | 대상·주요 결과 | 해석 |
|---|---|---|
| 10/15 Amazon Appliances | 1만 상품, 65,618리뷰, 287,105청크. 관련성 8사례 중 상품 적중 7, 정확한 source 적중 4, 전체 통과 4 | 과거 가전 실험. 팀 의미 라벨 승인 대기, holdout 독립성 제한. 현재 정확도 아님 |
| 10/17 test_items API 초기/재실행 | 긍정 10 + OOD 2. Hit@1 60%, Hit@5 80%. OOD 2/2 반환. 근거 118건 일치 | 당시 all_products/beauty 검색 경로와 출처 검사 |
| 10/17 test_items 검색 품질 문서 | 같은 규모 긍정 10개에서 Hit@1 70%, Hit@5 80%, MRR .750, 근거 116건 일치 | 인덱스 재작성 후 순위 변동과 재현 기록. 이전 결과와 평균 내지 않음 |
| 10/17 개선 진단 | RRF k=10/가중치, 요청 표현 제거, 일부 별칭 확장 재생 비교 | 일부 질의에 직접 준 별칭으로 90%/100%가 나왔지만 전체 카테고리 일반 성능 아님 |
| 10/17 리뷰 추천 정책 | 5개 질의 smoke, 근거 16개 일치, 키보드/클렌징오일 제외, 모의 가격이면 예산 추천 보류 | 격리 브랜치의 정책 확인. 당시 운영 API 배포 결과 아님 |
| 10/18 LangChain HTTP 연결 | 요청 조건 보존·요청 격리·상태/오류·HTTP 경유 검증 기록 | 연결 동작 검사. 추천 정확도 평가 아님 |
| 10/19 test_items2 전체 범주 탐색 | 자연어 24 + 상품명 8 + 후기 대조 4 + OOD 4 + 예산 2 + 미지원 범주 1 = **43건** | 직접 hybrid_search 호출. 현재 배포본의 HTTP E2E 평가 아님 |

### test_items2 전체 범주 탐색 수치

| 지표 | 당시 결과 |
|---|---:|
| 자연어 Hit@1 / Hit@5 | 58.3% (14/24) / 91.7% (22/24) |
| Precision@5 / MRR@5 / nDCG@5 | .558 / .750 / .629 |
| Macro Recall@5 | .375 |
| 상품명 그대로 검색 | 8/8 1위 |
| 반환 근거 무결성 | 447건 중 ID·원문·출처·offset 불일치 0 |
| OOD | 4/4 무관 상품 반환 |
| 예산 | 당시 별도 Commerce 검증 전 경로에서 초과 상품 반환 |

추천 품질 기준 `24a1051`의 상품 관련성·옵션 가격/재고·근거 선별을 20:48 API 0.3.1 복구본에서 BGE와 연결했다. HTTP·제약 검증은 통과했지만 그 효과의 정확도 평가는 별도다. 과거 MiniLM 점수에 구현 효과를 더해 BGE 성능을 계산하지 않는다.

관련 원문:

- [test_items 품질 재평가](archive/project/docs/rag-search-quality-test-items-beauty-2026-10-17.md)
- [초기 API 평가](archive/multi-catalog/reports/rag-contracts/rag-performance-evaluation-2026-10-17.md)
- [API 재실행 평가](archive/multi-catalog/reports/rag-contracts/rag-performance-evaluation-rerun-2026-10-17.md)
- [개선 진단](archive/multi-catalog/reports/rag-contracts/rag-improvement-spike-2026-10-17.md)
- [리뷰 정책 검사](archive/multi-catalog/reports/rag-contracts/rag-review-policy-evaluation-2026-10-17.md)
- [test_items2 43건 평가 요약](archive/project/data/test_items2/search_quality_2026-10-19.md)
- [test_items2 질문/정답](archive/project/data/test_items2/search_quality_cases_2026-10-19.json)
- [test_items2 전체 상세 결과](archive/project/data/test_items2/search_quality_2026-10-19.json)

10/15 평가 manifest·tuning·holdout·출처 검사와 LangChain 검증 JSON은 [전체 평가 목록](document-catalog.md#02-evaluations)에서 찾을 수 있다.

## 7. 측정하지 않은 항목과 다음 비교의 기준

| 항목 | 확인된 공백 |
|---|---|
| 사람 검수 정답 | 상품·용도·근거를 사람이 판정한 충분한 gold/독립 holdout 부재 |
| 청크 길이 | 96 대비 다른 길이의 통제 실험 부재 |
| 범주 일반화 | 임베딩 모델 비교는 beauty. fashion/food/living 모델 우열은 미확인 |
| OOD 거절 | 모델 비교 경로에서 모두 상품 반환. 별도 유형/거절 정책 평가 필요 |
| 필수 옵션 | 임의 필수 문장의 사실 검증을 포괄하지 않음 |
| 리뷰 설명 품질 | 출처 무결성은 검사했으나 용도 적합성·반대 근거·최종 설명의 충실성은 별도 평가 필요 |
| API/Brain/웹 | 현재 배포본에서 가격·재고·상품명 순위가 최종 카드까지 유지되는 E2E 평가 필요 |
| 지연 | HTTP·DB·임베딩·LLM을 나눈 반복/동시 부하 p95 필요 |

모델 후보로는 기존 실험에서 E5와 BGE를 계속 비교할 근거가 있다. 운영 채택에는 같은 최신 데이터·사람 라벨·동일 검색 정책·거절 기준·비용 조건이 필요하다. MPNet과 BGE 리랭커는 후보 언급만 있고 실제 결과표는 발견하지 못했다.

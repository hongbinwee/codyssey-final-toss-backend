# RAG 전체 원문 목록 — BGE 기준 갱신

[통합 목차](README.md) · [현재 구성](current-system.md) · [출처/해시 manifest](source-manifest.json)

원문·평가·스키마·예제 **239개**, 발견 위치/버전 **300건**. 바이트가 같은 중복 61건은 사본을 합치고 출처를 보존했다.

**현재 모델은 BGE-M3, 전체 114,106벡터 ready(2026-10-20 18:25 KST)**다. 과거 MiniLM·API 0.3.0·초기 격리 설계도 원문으로 보존했다. 목록 수록은 현재 배포·정책 통과를 뜻하지 않는다.

## 분류 요약

| 분류 | 자료 수 |
|---|---:|
| [임베딩 모델·BGE 검색 비교](#01-model-comparisons) | 8 |
| [검색 평가·정책·질문/정답·검증](#02-evaluations) | 28 |
| [데이터셋·청킹/색인·전체 BGE 적재](#03-datasets-indexing) | 31 |
| [DB·BGE 운영·인수인계](#04-database-operations) | 20 |
| [API 계약·스키마·요청/응답 예제](#05-api-contracts) | 34 |
| [프롬프트·유저 스토리·수정요청서](#06-agent-requirements) | 15 |
| [설계·계획·진행 기록](#07-designs-plans-progress) | 44 |
| [구성·Commerce/LangChain 연동](#08-architecture-integration) | 52 |
| [팀 규칙의 현재/과거 사본](#09-team-rules) | 7 |

## 조사한 위치

| 출처 | 경로 | 브랜치/HEAD |
|---|---|---|
| quality | `/home/aiteam/projects/toss-ads-project/codyssey-final-toss-backend/.worktrees/rag-recommendation-quality` | `feature/rag-recommendation-quality` / `24a1051fff` |
| bge-m3 | `/home/aiteam/projects/toss-ads-project/codyssey-final-toss-backend/.worktrees/rag-bge-m3` | `feature/rag-bge-m3` / `db83e99981` |
| langchain-http | `/home/aiteam/projects/toss-ads-project/codyssey-final-toss-backend/.worktrees/rag-langchain-http` | `feature/rag-langchain-http` / `c51c8e6f0d` |
| backend | `/home/aiteam/projects/toss-ads-project/codyssey-final-toss-backend` | `codex/rag-contracts-validation` / `6d96c3b0f1` |
| multi-catalog | `/tmp/codyssey-rag-multi-catalog` | `codex/rag-multi-catalog` / `296518b6b4` |
| commerce-integration | `/home/aiteam/projects/toss-ads-project/codyssey-final-toss-backend/.worktrees/commerce-rag-integration` | `codex/commerce-rag-integration` / `4ccdcb4f51` |
| commerce-storefront | `/home/aiteam/projects/toss-ads-project/codyssey-final-toss-backend/.worktrees/commerce-storefront` | `codex/commerce-rag-storefront` / `898740c3ea` |
| project | `/home/aiteam/projects/toss-ads-project` | `main` / `6063db66de` |
| old-project-worktree | `/home/aiteam/.codex/worktrees/rag-langchain-http/toss-ads-project` | `feature/rag-langchain-http` / `6063db66de` |
| bge-m3-activated | `/home/aiteam/projects/toss-ads-project/codyssey-final-toss-backend/.worktrees/rag-bge-m3` | `feature/rag-bge-m3` / `f1b9ff3e57` |

첨부 두 텍스트와 data/exports ZIP의 README·DDL·manifest도 포함한다. Git 자료는 로컬 ref tip의 서로 다른 문서 내용이며 모든 중간 커밋이나 외부 Drive/채팅까지 조사한 전사 목록은 아니다.

archive의 원문과 내부 링크는 당시 내용을 유지했다. 현재 탐색에는 아래 링크를 사용한다. 원래 절대 경로·Git blob/ref·작업 트리 상태·SHA-256은 manifest에 있다. origin HEAD는 미커밋 문서까지 커밋/푸시됐다는 뜻이 아니다.

<a id="01-model-comparisons"></a>

## 임베딩 모델·BGE 검색 비교

| ID | 원문 | 형식 | 발견 위치/버전 |
|---|---|---|---|
| RAG-DOC-062 | [test_items2/beauty 검색 비교: BM25와 BGE-M3](archive/bge-m3/docs/rag-bge-m3-test-items2-beauty-2026-10-20.md) | MD | `bge-m3/docs/rag-bge-m3-test-items2-beauty-2026-10-20.md`<br>Git `645e744607` / `docs/rag-bge-m3-test-items2-beauty-2026-10-20.md`<br>`bge-m3-activated/docs/rag-bge-m3-test-items2-beauty-2026-10-20.md` |
| RAG-DOC-063 | [rag-bge-m3-test-items2-beauty-2026-10-20.pdf](archive/bge-m3/docs/rag-bge-m3-test-items2-beauty-2026-10-20.pdf) | PDF | `bge-m3/docs/rag-bge-m3-test-items2-beauty-2026-10-20.pdf`<br>Git `3e00cdc76b` / `docs/rag-bge-m3-test-items2-beauty-2026-10-20.pdf`<br>`bge-m3-activated/docs/rag-bge-m3-test-items2-beauty-2026-10-20.pdf` |
| RAG-DOC-064 | [`test_items/beauty` 임베딩 모델 비교](archive/bge-m3/docs/rag-embedding-model-comparison-test-items-beauty-2026-10-19.md) | MD | `bge-m3/docs/rag-embedding-model-comparison-test-items-beauty-2026-10-19.md`<br>`backend/docs/rag-embedding-model-comparison-test-items-beauty-2026-10-19.md`<br>`bge-m3-activated/docs/rag-embedding-model-comparison-test-items-beauty-2026-10-19.md` |
| RAG-DOC-065 | [`test_items2/beauty` 임베딩 모델 비교](archive/bge-m3/docs/rag-embedding-model-comparison-test-items2-beauty-2026-10-19.md) | MD | `bge-m3/docs/rag-embedding-model-comparison-test-items2-beauty-2026-10-19.md`<br>`backend/docs/rag-embedding-model-comparison-test-items2-beauty-2026-10-19.md`<br>`bge-m3-activated/docs/rag-embedding-model-comparison-test-items2-beauty-2026-10-19.md` |
| RAG-DOC-066 | [rag-embedding-model-comparison-test-items2-beauty-2026-10-19.pdf](archive/bge-m3/docs/rag-embedding-model-comparison-test-items2-beauty-2026-10-19.pdf) | PDF | `bge-m3/docs/rag-embedding-model-comparison-test-items2-beauty-2026-10-19.pdf`<br>`backend/docs/rag-embedding-model-comparison-test-items2-beauty-2026-10-19.pdf`<br>`bge-m3-activated/docs/rag-embedding-model-comparison-test-items2-beauty-2026-10-19.pdf` |
| RAG-DOC-072 | [test_items2_beauty_bge_m3.json](archive/bge-m3/evals/fixtures/test_items2_beauty_bge_m3.json) | JSON | `bge-m3/evals/fixtures/test_items2_beauty_bge_m3.json` |
| RAG-DOC-073 | [rag-bge-m3-test-items2-beauty-2026-10-20-index.json](archive/bge-m3/reports/rag-bge-m3-test-items2-beauty-2026-10-20-index.json) | JSON | `bge-m3/reports/rag-bge-m3-test-items2-beauty-2026-10-20-index.json`<br>Git `012ef9a9d3` / `reports/rag-bge-m3-test-items2-beauty-2026-10-20-index.json`<br>`bge-m3-activated/reports/rag-bge-m3-test-items2-beauty-2026-10-20-index.json` |
| RAG-DOC-074 | [rag-bge-m3-test-items2-beauty-2026-10-20.json](archive/bge-m3/reports/rag-bge-m3-test-items2-beauty-2026-10-20.json) | JSON | `bge-m3/reports/rag-bge-m3-test-items2-beauty-2026-10-20.json`<br>Git `0c95ea5319` / `reports/rag-bge-m3-test-items2-beauty-2026-10-20.json`<br>`bge-m3-activated/reports/rag-bge-m3-test-items2-beauty-2026-10-20.json` |

<a id="02-evaluations"></a>

## 검색 평가·정책·질문/정답·검증

| ID | 원문 | 형식 | 발견 위치/버전 |
|---|---|---|---|
| RAG-DOC-204 | [search-tuning-appliances-2026-10-15.json](archive/git-history/0345be12ff/reports/rag-contracts/search-tuning-appliances-2026-10-15.json) | JSON | Git `0345be12ff` / `reports/rag-contracts/search-tuning-appliances-2026-10-15.json`<br>Git `0345be12ff` / `reports/rag-contracts/search-tuning-appliances-review-channels-2026-10-15.json` |
| RAG-DOC-193 | [amazon_reviews_rag_cases.json](archive/git-history/1e5c44c000/evals/amazon_reviews_rag_cases.json) | JSON | Git `1e5c44c000` / `evals/amazon_reviews_rag_cases.json` |
| RAG-DOC-202 | [search-holdout-appliances-review-channels-2026-10-15.json](archive/git-history/2954174a07/reports/rag-contracts/search-holdout-appliances-review-channels-2026-10-15.json) | JSON | Git `2954174a07` / `reports/rag-contracts/search-holdout-appliances-review-channels-2026-10-15.json` |
| RAG-DOC-203 | [search-tuning-after-chunk-dedup.json](archive/git-history/57d5a5b8c2/reports/rag-contracts/search-tuning-after-chunk-dedup.json) | JSON | Git `57d5a5b8c2` / `reports/rag-contracts/search-tuning-after-chunk-dedup.json` |
| RAG-DOC-195 | [amazon_reviews_rag_sources.json](archive/git-history/70dc17ff1e/evals/fixtures/amazon_reviews_rag_sources.json) | JSON | Git `70dc17ff1e` / `evals/fixtures/amazon_reviews_rag_sources.json` |
| RAG-DOC-199 | [label-review-2026-10-15.json](archive/git-history/75e98aa6da/reports/rag-contracts/label-review-2026-10-15.json) | JSON | Git `75e98aa6da` / `reports/rag-contracts/label-review-2026-10-15.json` |
| RAG-DOC-196 | [evaluation-manifest-2026-10-15.json](archive/git-history/8020ed1294/reports/rag-contracts/evaluation-manifest-2026-10-15.json) | JSON | Git `8020ed1294` / `reports/rag-contracts/evaluation-manifest-2026-10-15.json` |
| RAG-DOC-194 | [amazon_reviews_rag_negative_proposals.json](archive/git-history/9cc654e1c6/evals/amazon_reviews_rag_negative_proposals.json) | JSON | Git `9cc654e1c6` / `evals/amazon_reviews_rag_negative_proposals.json` |
| RAG-DOC-215 | [amazon_reviews_rag_cases.json](archive/git-history/aa2eded1a0/evals/amazon_reviews_rag_cases.json) | JSON | Git `aa2eded1a0` / `evals/amazon_reviews_rag_cases.json` |
| RAG-DOC-201 | [search-holdout-appliances-retry-2026-10-15.json](archive/git-history/cd2aa762d6/reports/rag-contracts/search-holdout-appliances-retry-2026-10-15.json) | JSON | Git `cd2aa762d6` / `reports/rag-contracts/search-holdout-appliances-retry-2026-10-15.json` |
| RAG-DOC-205 | [search-tuning-appliances-final-2026-10-15.json](archive/git-history/e873d585f6/reports/rag-contracts/search-tuning-appliances-final-2026-10-15.json) | JSON | Git `e873d585f6` / `reports/rag-contracts/search-tuning-appliances-final-2026-10-15.json` |
| RAG-DOC-206 | [search-tuning-first-run.json](archive/git-history/fe82d146cd/reports/rag-contracts/search-tuning-first-run.json) | JSON | Git `fe82d146cd` / `reports/rag-contracts/search-tuning-first-run.json` |
| RAG-DOC-200 | [search-holdout-appliances-final-2026-10-15.json](archive/git-history/fef133aa71/reports/rag-contracts/search-holdout-appliances-final-2026-10-15.json) | JSON | Git `fef133aa71` / `reports/rag-contracts/search-holdout-appliances-final-2026-10-15.json` |
| RAG-DOC-079 | [langchain-http-verification-2026-10-18.json](archive/langchain-http/reports/langchain-http-verification-2026-10-18.json) | JSON | `langchain-http/reports/langchain-http-verification-2026-10-18.json`<br>Git `581cfaac3a` / `reports/langchain-http-verification-2026-10-18.json` |
| RAG-DOC-088 | [catalog-profile-smoke-2026-10-17.json](archive/multi-catalog/reports/rag-contracts/catalog-profile-smoke-2026-10-17.json) | JSON | `multi-catalog/reports/rag-contracts/catalog-profile-smoke-2026-10-17.json` |
| RAG-DOC-089 | [RAG 개선 진단 — 2026-10-17](archive/multi-catalog/reports/rag-contracts/rag-improvement-spike-2026-10-17.md) | MD | `multi-catalog/reports/rag-contracts/rag-improvement-spike-2026-10-17.md` |
| RAG-DOC-090 | [rag-performance-evaluation-2026-10-17.json](archive/multi-catalog/reports/rag-contracts/rag-performance-evaluation-2026-10-17.json) | JSON | `multi-catalog/reports/rag-contracts/rag-performance-evaluation-2026-10-17.json` |
| RAG-DOC-091 | [RAG retrieval evaluation — 2026-10-17](archive/multi-catalog/reports/rag-contracts/rag-performance-evaluation-2026-10-17.md) | MD | `multi-catalog/reports/rag-contracts/rag-performance-evaluation-2026-10-17.md` |
| RAG-DOC-092 | [rag-performance-evaluation-rerun-2026-10-17.json](archive/multi-catalog/reports/rag-contracts/rag-performance-evaluation-rerun-2026-10-17.json) | JSON | `multi-catalog/reports/rag-contracts/rag-performance-evaluation-rerun-2026-10-17.json` |
| RAG-DOC-093 | [RAG 실시간 재평가 — 2026-10-17](archive/multi-catalog/reports/rag-contracts/rag-performance-evaluation-rerun-2026-10-17.md) | MD | `multi-catalog/reports/rag-contracts/rag-performance-evaluation-rerun-2026-10-17.md` |
| RAG-DOC-094 | [rag-review-policy-evaluation-2026-10-17.json](archive/multi-catalog/reports/rag-contracts/rag-review-policy-evaluation-2026-10-17.json) | JSON | `multi-catalog/reports/rag-contracts/rag-review-policy-evaluation-2026-10-17.json` |
| RAG-DOC-095 | [리뷰 기반 추천 정책 재검증 — 2026-10-17](archive/multi-catalog/reports/rag-contracts/rag-review-policy-evaluation-2026-10-17.md) | MD | `multi-catalog/reports/rag-contracts/rag-review-policy-evaluation-2026-10-17.md` |
| RAG-DOC-152 | [langchain-http-verification-2026-10-18.json](archive/old-project-worktree/reports/langchain-http-verification-2026-10-18.json) | JSON | `old-project-worktree/reports/langchain-http-verification-2026-10-18.json` |
| RAG-DOC-126 | [search_quality_2026-10-19.json](archive/project/data/test_items2/search_quality_2026-10-19.json) | JSON | `project/data/test_items2/search_quality_2026-10-19.json` |
| RAG-DOC-127 | [test_items2 RAG 탐색 평가 — 2026-10-19](archive/project/data/test_items2/search_quality_2026-10-19.md) | MD | `project/data/test_items2/search_quality_2026-10-19.md` |
| RAG-DOC-128 | [search_quality_cases_2026-10-19.json](archive/project/data/test_items2/search_quality_cases_2026-10-19.json) | JSON | `project/data/test_items2/search_quality_cases_2026-10-19.json` |
| RAG-DOC-132 | [`test_items/beauty` 검색 품질 재평가](archive/project/docs/rag-search-quality-test-items-beauty-2026-10-17.md) | MD | `project/docs/rag-search-quality-test-items-beauty-2026-10-17.md` |
| RAG-DOC-138 | [rag-search-quality-test-items-beauty-2026-10-17.json](archive/project/reports/rag-search-quality-test-items-beauty-2026-10-17.json) | JSON | `project/reports/rag-search-quality-test-items-beauty-2026-10-17.json` |

<a id="03-datasets-indexing"></a>

## 데이터셋·청킹/색인·전체 BGE 적재

| ID | 원문 | 형식 | 발견 위치/버전 |
|---|---|---|---|
| RAG-DOC-239 | [rag-bge-m3-test-items2-full-2026-10-20-index.json](archive/bge-m3-activated/reports/rag-bge-m3-test-items2-full-2026-10-20-index.json) | JSON | `bge-m3-activated/reports/rag-bge-m3-test-items2-full-2026-10-20-index.json` |
| RAG-DOC-216 | [test_items2 청킹·임베딩 공유 자료](archive/export-test_items2_chunked_full_2026-10-19/README_KO.md) | MD | `export-test_items2_chunked_full_2026-10-19` ZIP 내부 `README_KO.md` |
| RAG-DOC-217 | [65a34cbcf3348d1c65ca626eeeb44fb29320ccecc050582906c786a17a5e059e  README_KO.md](archive/export-test_items2_chunked_full_2026-10-19/SHA256SUMS.txt) | TXT | `export-test_items2_chunked_full_2026-10-19` ZIP 내부 `SHA256SUMS.txt` |
| RAG-DOC-218 | [schema.sql](archive/export-test_items2_chunked_full_2026-10-19/database_exports/toss/test_items2/schema.sql) | SQL | `export-test_items2_chunked_full_2026-10-19` ZIP 내부 `database_exports/toss/test_items2/schema.sql` |
| RAG-DOC-219 | [schema.sql](archive/export-test_items2_chunked_full_2026-10-19/database_exports/toss_rag/rag/schema.sql) | SQL | `export-test_items2_chunked_full_2026-10-19` ZIP 내부 `database_exports/toss_rag/rag/schema.sql` |
| RAG-DOC-220 | [export_manifest.json](archive/export-test_items2_chunked_full_2026-10-19/metadata/export_manifest.json) | JSON | `export-test_items2_chunked_full_2026-10-19` ZIP 내부 `metadata/export_manifest.json` |
| RAG-DOC-221 | [test_items 전체 데이터 묶음](archive/export-test_items_complete_2026-10-18/README_KO.md) | MD | `export-test_items_complete_2026-10-18` ZIP 내부 `README_KO.md` |
| RAG-DOC-222 | [b0ccd5e498d88fad8da5eb60903d4cb370d1baa779afc9f95e9256425848f697  README_KO.md](archive/export-test_items_complete_2026-10-18/SHA256SUMS.txt) | TXT | `export-test_items_complete_2026-10-18` ZIP 내부 `SHA256SUMS.txt` |
| RAG-DOC-223 | [schema.sql](archive/export-test_items_complete_2026-10-18/database_exports/toss/test_items/schema.sql) | SQL | `export-test_items_complete_2026-10-18` ZIP 내부 `database_exports/toss/test_items/schema.sql` |
| RAG-DOC-224 | [schema.sql](archive/export-test_items_complete_2026-10-18/database_exports/toss_rag/rag/schema.sql) | SQL | `export-test_items_complete_2026-10-18` ZIP 내부 `database_exports/toss_rag/rag/schema.sql` |
| RAG-DOC-225 | [export_metadata.json](archive/export-test_items_complete_2026-10-18/export_metadata.json) | JSON | `export-test_items_complete_2026-10-18` ZIP 내부 `export_metadata.json` |
| RAG-DOC-226 | [Shopping Brain v4 — 실제 상품 통계 기반 시연용 데이터셋 (검증 범위 명시)](archive/export-test_items_complete_2026-10-18/shopping_brain_v4_demo_final/README.md) | MD | `export-test_items_complete_2026-10-18` ZIP 내부 `shopping_brain_v4_demo_final/README.md` |
| RAG-DOC-227 | [v4 Commerce / RAG 데이터 계약](archive/export-test_items_complete_2026-10-18/shopping_brain_v4_demo_final/docs/DATA_CONTRACT.md) | MD | `export-test_items_complete_2026-10-18` ZIP 내부 `shopping_brain_v4_demo_final/docs/DATA_CONTRACT.md` |
| RAG-DOC-228 | [Release Gates (2026-10-16)](archive/export-test_items_complete_2026-10-18/shopping_brain_v4_demo_final/docs/RELEASE_GATES.md) | MD | `export-test_items_complete_2026-10-18` ZIP 내부 `shopping_brain_v4_demo_final/docs/RELEASE_GATES.md` |
| RAG-DOC-229 | [Holdout 정책](archive/export-test_items_complete_2026-10-18/shopping_brain_v4_demo_final/eval/README.md) | MD | `export-test_items_complete_2026-10-18` ZIP 내부 `shopping_brain_v4_demo_final/eval/README.md` |
| RAG-DOC-230 | [v4 모의 시연용 데이터 QA](archive/export-test_items_complete_2026-10-18/shopping_brain_v4_demo_final/qa/DATA_QUALITY_REPORT.md) | MD | `export-test_items_complete_2026-10-18` ZIP 내부 `shopping_brain_v4_demo_final/qa/DATA_QUALITY_REPORT.md` |
| RAG-DOC-231 | [SHA256_MANIFEST.json](archive/export-test_items_complete_2026-10-18/shopping_brain_v4_demo_final/qa/SHA256_MANIFEST.json) | JSON | `export-test_items_complete_2026-10-18` ZIP 내부 `shopping_brain_v4_demo_final/qa/SHA256_MANIFEST.json` |
| RAG-DOC-198 | [full-index-2026-10-15.json](archive/git-history/66cf818bbb/reports/rag-contracts/full-index-2026-10-15.json) | JSON | Git `66cf818bbb` / `reports/rag-contracts/full-index-2026-10-15.json` |
| RAG-DOC-208 | [source-validation-2026-10-15.json](archive/git-history/6d610a0cfe/reports/rag-contracts/source-validation-2026-10-15.json) | JSON | Git `6d610a0cfe` / `reports/rag-contracts/source-validation-2026-10-15.json`<br>Git `6d610a0cfe` / `reports/rag-contracts/source-validation.json` |
| RAG-DOC-209 | [source-validation-appliances-2026-10-15.json](archive/git-history/8fde4ae586/reports/rag-contracts/source-validation-appliances-2026-10-15.json) | JSON | Git `8fde4ae586` / `reports/rag-contracts/source-validation-appliances-2026-10-15.json` |
| RAG-DOC-207 | [source-privacy-audit-2026-10-15.json](archive/git-history/d9103730db/reports/rag-contracts/source-privacy-audit-2026-10-15.json) | JSON | Git `d9103730db` / `reports/rag-contracts/source-privacy-audit-2026-10-15.json` |
| RAG-DOC-140 | [Amazon Reviews'23 선별 데이터](archive/old-project-worktree/data/amzdata/README.md) | MD | `old-project-worktree/data/amzdata/README.md` |
| RAG-DOC-141 | [manifest.json](archive/old-project-worktree/data/amzdata/manifest.json) | JSON | `old-project-worktree/data/amzdata/manifest.json` |
| RAG-DOC-121 | [test_items2 데이터 적재 및 색인](archive/project/data/test_items2/README.md) | MD | `project/data/test_items2/README.md` |
| RAG-DOC-122 | [index_report.json](archive/project/data/test_items2/index_report.json) | JSON | `project/data/test_items2/index_report.json`<br>`export-test_items2_chunked_full_2026-10-19` ZIP 내부 `metadata/index_report.json` |
| RAG-DOC-123 | [load_report.json](archive/project/data/test_items2/load_report.json) | JSON | `project/data/test_items2/load_report.json`<br>`export-test_items2_chunked_full_2026-10-19` ZIP 내부 `metadata/load_report.json` |
| RAG-DOC-124 | [run.json](archive/project/data/test_items2/run.json) | JSON | `project/data/test_items2/run.json` |
| RAG-DOC-125 | [schema_validation_2026-10-19.json](archive/project/data/test_items2/schema_validation_2026-10-19.json) | JSON | `project/data/test_items2/schema_validation_2026-10-19.json` |
| RAG-DOC-129 | [Shopping Brain V6.1 — Review Language Refinement (CANDIDATE)](archive/project/data/test_items2/source/shopping_brain_v6_1_common_dataset/README.md) | MD | `project/data/test_items2/source/shopping_brain_v6_1_common_dataset/README.md`<br>`export-test_items2_chunked_full_2026-10-19` ZIP 내부 `shopping_brain_v6_1_common_dataset/README.md` |
| RAG-DOC-130 | [zip_export_report.json](archive/project/data/test_items2/zip_export_report.json) | JSON | `project/data/test_items2/zip_export_report.json` |
| RAG-DOC-012 | [model-cache-manifest.json](archive/quality/docs/handover/rag-db-operations-2026-10-19/model-cache-manifest.json) | JSON | `quality/docs/handover/rag-db-operations-2026-10-19/model-cache-manifest.json` |

<a id="04-database-operations"></a>

## DB·BGE 운영·인수인계

| ID | 원문 | 형식 | 발견 위치/버전 |
|---|---|---|---|
| RAG-DOC-236 | [BGE-M3 Full-Dataset Operations](archive/bge-m3-activated/docs/rag-bge-m3-test-items2-full-operations.md) | MD | `bge-m3-activated/docs/rag-bge-m3-test-items2-full-operations.md` |
| RAG-DOC-008 | [0. 가장 먼저 알아둘 사항 : PDF 1쪽](archive/quality/docs/handover/rag-db-operations-2026-10-19/PDF_PAGE_INDEX.txt) | TXT | `quality/docs/handover/rag-db-operations-2026-10-19/PDF_PAGE_INDEX.txt` |
| RAG-DOC-009 | [운영 인수인계 자료](archive/quality/docs/handover/rag-db-operations-2026-10-19/README.md) | MD | `quality/docs/handover/rag-db-operations-2026-10-19/README.md` |
| RAG-DOC-010 | [data-archive-locator.json](archive/quality/docs/handover/rag-db-operations-2026-10-19/data-archive-locator.json) | JSON | `quality/docs/handover/rag-db-operations-2026-10-19/data-archive-locator.json` |
| RAG-DOC-011 | [fastembed-supported-models-runtime.json](archive/quality/docs/handover/rag-db-operations-2026-10-19/fastembed-supported-models-runtime.json) | JSON | `quality/docs/handover/rag-db-operations-2026-10-19/fastembed-supported-models-runtime.json` |
| RAG-DOC-013 | [observed-inventory.json](archive/quality/docs/handover/rag-db-operations-2026-10-19/observed-inventory.json) | JSON | `quality/docs/handover/rag-db-operations-2026-10-19/observed-inventory.json` |
| RAG-DOC-014 | [rag-api-tailscale.postman_collection.json](archive/quality/docs/handover/rag-db-operations-2026-10-19/rag-api-tailscale.postman_collection.json) | JSON | `quality/docs/handover/rag-db-operations-2026-10-19/rag-api-tailscale.postman_collection.json` |
| RAG-DOC-015 | [PostgreSQL · RAG 운영 인수인계서](archive/quality/docs/handover/rag-db-operations-2026-10-19/rag-db-operations-handover-2026-10-19.md) | MD | `quality/docs/handover/rag-db-operations-2026-10-19/rag-db-operations-handover-2026-10-19.md` |
| RAG-DOC-016 | [PyYAML==6.0.3](archive/quality/docs/handover/rag-db-operations-2026-10-19/requirements-runtime-snapshot.txt) | TXT | `quality/docs/handover/rag-db-operations-2026-10-19/requirements-runtime-snapshot.txt` |
| RAG-DOC-017 | [01_toss_inventory.sql](archive/quality/docs/handover/rag-db-operations-2026-10-19/sql/01_toss_inventory.sql) | SQL | `quality/docs/handover/rag-db-operations-2026-10-19/sql/01_toss_inventory.sql` |
| RAG-DOC-018 | [02_test_items2_catalog.sql](archive/quality/docs/handover/rag-db-operations-2026-10-19/sql/02_test_items2_catalog.sql) | SQL | `quality/docs/handover/rag-db-operations-2026-10-19/sql/02_test_items2_catalog.sql` |
| RAG-DOC-019 | [03_rag_active_profile.sql](archive/quality/docs/handover/rag-db-operations-2026-10-19/sql/03_rag_active_profile.sql) | SQL | `quality/docs/handover/rag-db-operations-2026-10-19/sql/03_rag_active_profile.sql` |
| RAG-DOC-020 | [04_rag_product_chunks.sql](archive/quality/docs/handover/rag-db-operations-2026-10-19/sql/04_rag_product_chunks.sql) | SQL | `quality/docs/handover/rag-db-operations-2026-10-19/sql/04_rag_product_chunks.sql` |
| RAG-DOC-021 | [05_toss_linkage_checks.sql](archive/quality/docs/handover/rag-db-operations-2026-10-19/sql/05_toss_linkage_checks.sql) | SQL | `quality/docs/handover/rag-db-operations-2026-10-19/sql/05_toss_linkage_checks.sql` |
| RAG-DOC-022 | [06_rag_model_baseline.sql](archive/quality/docs/handover/rag-db-operations-2026-10-19/sql/06_rag_model_baseline.sql) | SQL | `quality/docs/handover/rag-db-operations-2026-10-19/sql/06_rag_model_baseline.sql` |
| RAG-DOC-023 | [toss.test_items2.schema.sql](archive/quality/docs/handover/rag-db-operations-2026-10-19/toss.test_items2.schema.sql) | SQL | `quality/docs/handover/rag-db-operations-2026-10-19/toss.test_items2.schema.sql` |
| RAG-DOC-024 | [toss_rag.rag.schema.sql](archive/quality/docs/handover/rag-db-operations-2026-10-19/toss_rag.rag.schema.sql) | SQL | `quality/docs/handover/rag-db-operations-2026-10-19/toss_rag.rag.schema.sql` |
| RAG-DOC-025 | [Nginx Proxy Manager → RAG LAN 연결 적용](archive/quality/docs/rag-npm-lan-2026-10-19.md) | MD | `quality/docs/rag-npm-lan-2026-10-19.md` |
| RAG-DOC-042 | [rag-db-operations-handover-2026-10-19.pdf](archive/quality/docs/reports/rag-db-operations-handover-2026-10-19.pdf) | PDF | `quality/docs/reports/rag-db-operations-handover-2026-10-19.pdf` |
| RAG-DOC-043 | [rag-db-operations-handover-2026-10-19.zip](archive/quality/docs/reports/rag-db-operations-handover-2026-10-19.zip) | ZIP | `quality/docs/reports/rag-db-operations-handover-2026-10-19.zip` |

<a id="05-api-contracts"></a>

## API 계약·스키마·요청/응답 예제

| ID | 원문 | 형식 | 발견 위치/버전 |
|---|---|---|---|
| RAG-DOC-174 | [response-unsupported-category.json](archive/git-history/04f04ff5b5/contracts/amazon-reviews-rag/v0.2/examples/response-unsupported-category.json) | JSON | Git `04f04ff5b5` / `contracts/amazon-reviews-rag/v0.2/examples/response-unsupported-category.json` |
| RAG-DOC-178 | [RAG 규격·공통 질문과 검증 실행](archive/git-history/07e42d2558/docs/amazon-reviews-rag-contracts.md) | MD | Git `07e42d2558` / `docs/amazon-reviews-rag-contracts.md` |
| RAG-DOC-158 | [response-error.json](archive/git-history/0d3303110c/contracts/amazon-reviews-rag/v0.1/examples/response-error.json) | JSON | Git `0d3303110c` / `contracts/amazon-reviews-rag/v0.1/examples/response-error.json` |
| RAG-DOC-171 | [response-low-relevance.json](archive/git-history/16d6b175d7/contracts/amazon-reviews-rag/v0.2/examples/response-low-relevance.json) | JSON | Git `16d6b175d7` / `contracts/amazon-reviews-rag/v0.2/examples/response-low-relevance.json` |
| RAG-DOC-211 | [response-ok.json](archive/git-history/19bb2322b1/contracts/amazon-reviews-rag/v0.1/examples/response-ok.json) | JSON | Git `19bb2322b1` / `contracts/amazon-reviews-rag/v0.1/examples/response-ok.json` |
| RAG-DOC-159 | [response-low-relevance.json](archive/git-history/1a3024aeb2/contracts/amazon-reviews-rag/v0.1/examples/response-low-relevance.json) | JSON | Git `1a3024aeb2` / `contracts/amazon-reviews-rag/v0.1/examples/response-low-relevance.json` |
| RAG-DOC-167 | [request-category.json](archive/git-history/1b6b558e68/contracts/amazon-reviews-rag/v0.2/examples/request-category.json) | JSON | Git `1b6b558e68` / `contracts/amazon-reviews-rag/v0.2/examples/request-category.json` |
| RAG-DOC-170 | [response-error.json](archive/git-history/23bcb368f5/contracts/amazon-reviews-rag/v0.2/examples/response-error.json) | JSON | Git `23bcb368f5` / `contracts/amazon-reviews-rag/v0.2/examples/response-error.json` |
| RAG-DOC-210 | [Amazon Reviews RAG v0.1 공동 계약](archive/git-history/2cbd090e93/contracts/amazon-reviews-rag/v0.1/README.md) | MD | Git `2cbd090e93` / `contracts/amazon-reviews-rag/v0.1/README.md` |
| RAG-DOC-164 | [response.schema.json](archive/git-history/33a0a79344/contracts/amazon-reviews-rag/v0.1/response.schema.json) | JSON | Git `33a0a79344` / `contracts/amazon-reviews-rag/v0.1/response.schema.json` |
| RAG-DOC-165 | [source.schema.json](archive/git-history/4ab2e38a13/contracts/amazon-reviews-rag/v0.1/source.schema.json) | JSON | Git `4ab2e38a13` / `contracts/amazon-reviews-rag/v0.1/source.schema.json` |
| RAG-DOC-212 | [RAG 규격·공통 질문과 검증 실행](archive/git-history/5c844d4d9e/docs/amazon-reviews-rag-contracts.md) | MD | Git `5c844d4d9e` / `docs/amazon-reviews-rag-contracts.md` |
| RAG-DOC-166 | [Amazon Reviews RAG v0.2 카테고리 제한 계약 제안](archive/git-history/5f29a6c9af/contracts/amazon-reviews-rag/v0.2/README.md) | MD | Git `5f29a6c9af` / `contracts/amazon-reviews-rag/v0.2/README.md` |
| RAG-DOC-197 | [examples-validation.json](archive/git-history/660169d177/reports/rag-contracts/examples-validation.json) | JSON | Git `660169d177` / `reports/rag-contracts/examples-validation.json` |
| RAG-DOC-175 | [request.schema.json](archive/git-history/6ad82de320/contracts/amazon-reviews-rag/v0.2/request.schema.json) | JSON | Git `6ad82de320` / `contracts/amazon-reviews-rag/v0.2/request.schema.json` |
| RAG-DOC-163 | [request.schema.json](archive/git-history/7ee376fd26/contracts/amazon-reviews-rag/v0.1/request.schema.json) | JSON | Git `7ee376fd26` / `contracts/amazon-reviews-rag/v0.1/request.schema.json` |
| RAG-DOC-156 | [Amazon Reviews RAG v0.1 공동 계약](archive/git-history/8135511f1c/contracts/amazon-reviews-rag/v0.1/README.md) | MD | Git `8135511f1c` / `contracts/amazon-reviews-rag/v0.1/README.md` |
| RAG-DOC-157 | [request.json](archive/git-history/8495f4d0ff/contracts/amazon-reviews-rag/v0.1/examples/request.json) | JSON | Git `8495f4d0ff` / `contracts/amazon-reviews-rag/v0.1/examples/request.json`<br>Git `8495f4d0ff` / `contracts/amazon-reviews-rag/v0.2/examples/request.json` |
| RAG-DOC-177 | [source.schema.json](archive/git-history/9c5ec5f569/contracts/amazon-reviews-rag/v0.2/source.schema.json) | JSON | Git `9c5ec5f569` / `contracts/amazon-reviews-rag/v0.2/source.schema.json` |
| RAG-DOC-168 | [request-unsupported-category.json](archive/git-history/9db3c57812/contracts/amazon-reviews-rag/v0.2/examples/request-unsupported-category.json) | JSON | Git `9db3c57812` / `contracts/amazon-reviews-rag/v0.2/examples/request-unsupported-category.json` |
| RAG-DOC-176 | [response.schema.json](archive/git-history/afee1fc841/contracts/amazon-reviews-rag/v0.2/response.schema.json) | JSON | Git `afee1fc841` / `contracts/amazon-reviews-rag/v0.2/response.schema.json` |
| RAG-DOC-162 | [source.json](archive/git-history/c521d422a5/contracts/amazon-reviews-rag/v0.1/examples/source.json) | JSON | Git `c521d422a5` / `contracts/amazon-reviews-rag/v0.1/examples/source.json`<br>Git `c521d422a5` / `contracts/amazon-reviews-rag/v0.2/examples/source.json` |
| RAG-DOC-173 | [response-ok.json](archive/git-history/deb0d2f57d/contracts/amazon-reviews-rag/v0.2/examples/response-ok.json) | JSON | Git `deb0d2f57d` / `contracts/amazon-reviews-rag/v0.2/examples/response-ok.json` |
| RAG-DOC-172 | [response-no-results.json](archive/git-history/e10c13dd15/contracts/amazon-reviews-rag/v0.2/examples/response-no-results.json) | JSON | Git `e10c13dd15` / `contracts/amazon-reviews-rag/v0.2/examples/response-no-results.json` |
| RAG-DOC-169 | [response-category-ok.json](archive/git-history/e790eaf2ac/contracts/amazon-reviews-rag/v0.2/examples/response-category-ok.json) | JSON | Git `e790eaf2ac` / `contracts/amazon-reviews-rag/v0.2/examples/response-category-ok.json` |
| RAG-DOC-161 | [response-ok.json](archive/git-history/f43b626227/contracts/amazon-reviews-rag/v0.1/examples/response-ok.json) | JSON | Git `f43b626227` / `contracts/amazon-reviews-rag/v0.1/examples/response-ok.json` |
| RAG-DOC-160 | [response-no-results.json](archive/git-history/f4ffb80217/contracts/amazon-reviews-rag/v0.1/examples/response-no-results.json) | JSON | Git `f4ffb80217` / `contracts/amazon-reviews-rag/v0.1/examples/response-no-results.json` |
| RAG-DOC-002 | [request.schema.json](archive/quality/contracts/product-rag/v0.3/request.schema.json) | JSON | `quality/contracts/product-rag/v0.3/request.schema.json`<br>`quality/docs/api/rag-search.request.schema.json`<br>`quality/docs/handover/rag-db-operations-2026-10-19/rag-search.request.schema.json`<br>Git `af6ba0926c` / `contracts/product-rag/v0.3/request.schema.json` |
| RAG-DOC-004 | [rag-search.request.json](archive/quality/docs/api/examples/rag-search.request.json) | JSON | `quality/docs/api/examples/rag-search.request.json`<br>`quality/docs/handover/rag-db-operations-2026-10-19/examples/rag-search.request.json` |
| RAG-DOC-005 | [rag-search.response.example.json](archive/quality/docs/api/examples/rag-search.response.example.json) | JSON | `quality/docs/api/examples/rag-search.response.example.json`<br>`quality/docs/handover/rag-db-operations-2026-10-19/examples/rag-search.response.example.json` |
| RAG-DOC-006 | [Product RAG API 연동 문서](archive/quality/docs/api/rag-api-guide-2026-10-19.md) | MD | `quality/docs/api/rag-api-guide-2026-10-19.md` |
| RAG-DOC-007 | [rag-api.postman_collection.json](archive/quality/docs/api/rag-api.postman_collection.json) | JSON | `quality/docs/api/rag-api.postman_collection.json` |
| RAG-DOC-028 | [rag-api-docs-2026-10-19.zip](archive/quality/docs/reports/rag-api-docs-2026-10-19.zip) | ZIP | `quality/docs/reports/rag-api-docs-2026-10-19.zip` |
| RAG-DOC-029 | [rag-api-guide-2026-10-19.pdf](archive/quality/docs/reports/rag-api-guide-2026-10-19.pdf) | PDF | `quality/docs/reports/rag-api-guide-2026-10-19.pdf` |

<a id="06-agent-requirements"></a>

## 프롬프트·유저 스토리·수정요청서

| ID | 원문 | 형식 | 발견 위치/버전 |
|---|---|---|---|
| RAG-DOC-133 | [rag-system-prompt-share-2026-10-19.pdf](archive/project/docs/rag-system-prompt-share-2026-10-19.pdf) | PDF | `project/docs/rag-system-prompt-share-2026-10-19.pdf` |
| RAG-DOC-030 | [rag-change-requests-2026-10-19-v1.1.json](archive/quality/docs/reports/rag-change-requests-2026-10-19-v1.1.json) | JSON | `quality/docs/reports/rag-change-requests-2026-10-19-v1.1.json` |
| RAG-DOC-031 | [Shopping Brain · RAG 추천 품질 수정요청서](archive/quality/docs/reports/rag-change-requests-2026-10-19-v1.1.md) | MD | `quality/docs/reports/rag-change-requests-2026-10-19-v1.1.md` |
| RAG-DOC-032 | [rag-change-requests-2026-10-19-v1.1.pdf](archive/quality/docs/reports/rag-change-requests-2026-10-19-v1.1.pdf) | PDF | `quality/docs/reports/rag-change-requests-2026-10-19-v1.1.pdf` |
| RAG-DOC-033 | [rag-change-requests-2026-10-19-v1.2.json](archive/quality/docs/reports/rag-change-requests-2026-10-19-v1.2.json) | JSON | `quality/docs/reports/rag-change-requests-2026-10-19-v1.2.json` |
| RAG-DOC-034 | [Shopping Brain · RAG 추천 품질 수정요청서](archive/quality/docs/reports/rag-change-requests-2026-10-19-v1.2.md) | MD | `quality/docs/reports/rag-change-requests-2026-10-19-v1.2.md` |
| RAG-DOC-035 | [rag-change-requests-2026-10-19-v1.2.pdf](archive/quality/docs/reports/rag-change-requests-2026-10-19-v1.2.pdf) | PDF | `quality/docs/reports/rag-change-requests-2026-10-19-v1.2.pdf` |
| RAG-DOC-036 | [rag-change-requests-2026-10-19-v1.3.json](archive/quality/docs/reports/rag-change-requests-2026-10-19-v1.3.json) | JSON | `quality/docs/reports/rag-change-requests-2026-10-19-v1.3.json` |
| RAG-DOC-037 | [Shopping Brain · RAG 추천 품질 수정요청서](archive/quality/docs/reports/rag-change-requests-2026-10-19-v1.3.md) | MD | `quality/docs/reports/rag-change-requests-2026-10-19-v1.3.md` |
| RAG-DOC-038 | [rag-change-requests-2026-10-19-v1.3.pdf](archive/quality/docs/reports/rag-change-requests-2026-10-19-v1.3.pdf) | PDF | `quality/docs/reports/rag-change-requests-2026-10-19-v1.3.pdf` |
| RAG-DOC-039 | [rag-change-requests-2026-10-19.json](archive/quality/docs/reports/rag-change-requests-2026-10-19.json) | JSON | `quality/docs/reports/rag-change-requests-2026-10-19.json` |
| RAG-DOC-040 | [Shopping Brain · RAG 추천 품질 수정요청서](archive/quality/docs/reports/rag-change-requests-2026-10-19.md) | MD | `quality/docs/reports/rag-change-requests-2026-10-19.md` |
| RAG-DOC-041 | [rag-change-requests-2026-10-19.pdf](archive/quality/docs/reports/rag-change-requests-2026-10-19.pdf) | PDF | `quality/docs/reports/rag-change-requests-2026-10-19.pdf` |
| RAG-DOC-153 | [Toss Shopping Brain — Agent 기본 지침 v0.6](archive/user-attachments/agent-guidance-v0.6.txt) | TXT | `user-attachments/agent-guidance-v0.6.txt` |
| RAG-DOC-154 | [토스 brain 쇼핑 AI 에이전트 유저 스토리](archive/user-attachments/shopping-agent-user-stories.txt) | TXT | `user-attachments/shopping-agent-user-stories.txt` |

<a id="07-designs-plans-progress"></a>

## 설계·계획·진행 기록

| ID | 원문 | 형식 | 발견 위치/버전 |
|---|---|---|---|
| RAG-DOC-080 | [SDD ledger — plan: docs/superpowers/plans/2026-10-15-rag-service-integration.md](archive/backend/.superpowers/sdd/2026-10-15-rag-service-integration/progress.md) | MD | `backend/.superpowers/sdd/2026-10-15-rag-service-integration/progress.md` |
| RAG-DOC-232 | [SDD ledger — plan: docs/superpowers/plans/2026-10-20-rag-bge-m3-full-dataset-activation.md](archive/bge-m3-activated/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/progress.md) | MD | `bge-m3-activated/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/progress.md` |
| RAG-DOC-233 | [Task 4: Document and safely switch the local API runtime](archive/bge-m3-activated/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/task-4-brief.md) | MD | `bge-m3-activated/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/task-4-brief.md` |
| RAG-DOC-234 | [Task 5: Populate the full profile and activate BGE-M3](archive/bge-m3-activated/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/task-5-brief.md) | MD | `bge-m3-activated/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/task-5-brief.md` |
| RAG-DOC-237 | [test_items2 Full-Dataset BGE-M3 Activation Implementation Plan](archive/bge-m3-activated/docs/superpowers/plans/2026-10-20-rag-bge-m3-full-dataset-activation.md) | MD | `bge-m3-activated/docs/superpowers/plans/2026-10-20-rag-bge-m3-full-dataset-activation.md` |
| RAG-DOC-238 | [BGE-M3 dense 검색 전환 및 비교 설계](archive/bge-m3-activated/docs/superpowers/specs/2026-10-20-rag-bge-m3-dense-hybrid-design.md) | MD | `bge-m3-activated/docs/superpowers/specs/2026-10-20-rag-bge-m3-dense-hybrid-design.md` |
| RAG-DOC-047 | [SDD ledger — plan: docs/superpowers/plans/2026-10-20-rag-bge-m3-dense-hybrid.md](archive/bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-dense-hybrid/progress.md) | MD | `bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-dense-hybrid/progress.md` |
| RAG-DOC-048 | [Task 1: BGE-M3 dense 임베딩 어댑터](archive/bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-dense-hybrid/task-1-brief.md) | MD | `bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-dense-hybrid/task-1-brief.md` |
| RAG-DOC-049 | [Task 2: 추가 임베딩 프로필·벡터 저장소](archive/bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-dense-hybrid/task-2-brief.md) | MD | `bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-dense-hybrid/task-2-brief.md` |
| RAG-DOC-050 | [Task 3: 기존 beauty 청크 재임베딩 CLI](archive/bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-dense-hybrid/task-3-brief.md) | MD | `bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-dense-hybrid/task-3-brief.md` |
| RAG-DOC-051 | [Task 4: BM25·dense·hybrid 비교 검색](archive/bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-dense-hybrid/task-4-brief.md) | MD | `bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-dense-hybrid/task-4-brief.md` |
| RAG-DOC-052 | [Task 5: 고정 질의 평가와 결과 보고서](archive/bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-dense-hybrid/task-5-brief.md) | MD | `bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-dense-hybrid/task-5-brief.md` |
| RAG-DOC-053 | [SDD ledger — plan: docs/superpowers/plans/2026-10-20-rag-bge-m3-full-dataset-activation.md](archive/bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/progress.md) | MD | `bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/progress.md` |
| RAG-DOC-054 | [Task 1: Add safe whole-run BGE profile scope](archive/bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/task-1-brief.md) | MD | `bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/task-1-brief.md`<br>`bge-m3-activated/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/task-1-brief.md` |
| RAG-DOC-055 | [Task 2: Index every missing BGE vector with resume support](archive/bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/task-2-brief.md) | MD | `bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/task-2-brief.md`<br>`bge-m3-activated/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/task-2-brief.md` |
| RAG-DOC-056 | [Task 3: Route BGE queries through hybrid search and readiness](archive/bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/task-3-brief.md) | MD | `bge-m3/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/task-3-brief.md`<br>`bge-m3-activated/.superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/task-3-brief.md` |
| RAG-DOC-068 | [BGE-M3 Dense + BM25 Comparison Implementation Plan](archive/bge-m3/docs/superpowers/plans/2026-10-20-rag-bge-m3-dense-hybrid.md) | MD | `bge-m3/docs/superpowers/plans/2026-10-20-rag-bge-m3-dense-hybrid.md`<br>Git `0a64003a54` / `docs/superpowers/plans/2026-10-20-rag-bge-m3-dense-hybrid.md`<br>`bge-m3-activated/docs/superpowers/plans/2026-10-20-rag-bge-m3-dense-hybrid.md` |
| RAG-DOC-069 | [test_items2 Full-Dataset BGE-M3 Activation Implementation Plan](archive/bge-m3/docs/superpowers/plans/2026-10-20-rag-bge-m3-full-dataset-activation.md) | MD | `bge-m3/docs/superpowers/plans/2026-10-20-rag-bge-m3-full-dataset-activation.md`<br>Git `74f2e78bfc` / `docs/superpowers/plans/2026-10-20-rag-bge-m3-full-dataset-activation.md` |
| RAG-DOC-070 | [BGE-M3 dense 검색 전환 및 비교 설계](archive/bge-m3/docs/superpowers/specs/2026-10-20-rag-bge-m3-dense-hybrid-design.md) | MD | `bge-m3/docs/superpowers/specs/2026-10-20-rag-bge-m3-dense-hybrid-design.md`<br>Git `38fd645ba3` / `docs/superpowers/specs/2026-10-20-rag-bge-m3-dense-hybrid-design.md` |
| RAG-DOC-071 | [test_items2 전체 BGE-M3 하이브리드 검색 활성화 설계](archive/bge-m3/docs/superpowers/specs/2026-10-20-rag-bge-m3-full-dataset-activation-design.md) | MD | `bge-m3/docs/superpowers/specs/2026-10-20-rag-bge-m3-full-dataset-activation-design.md`<br>Git `aef36ab159` / `docs/superpowers/specs/2026-10-20-rag-bge-m3-full-dataset-activation-design.md`<br>`bge-m3-activated/docs/superpowers/specs/2026-10-20-rag-bge-m3-full-dataset-activation-design.md` |
| RAG-DOC-101 | [Commerce + RAG Full-Flow Implementation Plan](archive/commerce-integration/docs/superpowers/plans/2026-10-15-commerce-rag-full-flow.md) | MD | `commerce-integration/docs/superpowers/plans/2026-10-15-commerce-rag-full-flow.md` |
| RAG-DOC-102 | [Commerce Frontend + RAG Full-Flow Integration Design](archive/commerce-integration/docs/superpowers/specs/2026-10-15-commerce-rag-full-flow-design.md) | MD | `commerce-integration/docs/superpowers/specs/2026-10-15-commerce-rag-full-flow-design.md` |
| RAG-DOC-103 | [SDD ledger — plan: /home/aiteam/projects/toss-ads-project/docs/superpowers/plans/2026-10-17-rag-required-intake.md](archive/commerce-storefront/.superpowers/sdd/2026-10-17-rag-required-intake/progress.md) | MD | `commerce-storefront/.superpowers/sdd/2026-10-17-rag-required-intake/progress.md` |
| RAG-DOC-104 | [Task 1: Enforce intake and Commerce price filtering in the RAG service](archive/commerce-storefront/.superpowers/sdd/2026-10-17-rag-required-intake/task-1-brief.md) | MD | `commerce-storefront/.superpowers/sdd/2026-10-17-rag-required-intake/task-1-brief.md` |
| RAG-DOC-105 | [Task 2: Add the Shopping Agent RAG tool and required clarification prompt](archive/commerce-storefront/.superpowers/sdd/2026-10-17-rag-required-intake/task-2-brief.md) | MD | `commerce-storefront/.superpowers/sdd/2026-10-17-rag-required-intake/task-2-brief.md` |
| RAG-DOC-106 | [Task 3: Require budget and use case in the direct RAG search screen](archive/commerce-storefront/.superpowers/sdd/2026-10-17-rag-required-intake/task-3-brief.md) | MD | `commerce-storefront/.superpowers/sdd/2026-10-17-rag-required-intake/task-3-brief.md` |
| RAG-DOC-190 | [Amazon Reviews RAG Service Integration Plan](archive/git-history/0c6729b4e6/docs/superpowers/plans/2026-10-15-rag-service-integration.md) | MD | Git `0c6729b4e6` / `docs/superpowers/plans/2026-10-15-rag-service-integration.md` |
| RAG-DOC-155 | [Amazon Reviews 백엔드 연동 설계](archive/git-history/395e2e4231/docs/superpowers/specs/2026-10-14-amazon-reviews-backend-integration-design.md) | MD | Git `395e2e4231` / `docs/superpowers/specs/2026-10-14-amazon-reviews-backend-integration-design.md` |
| RAG-DOC-189 | [RAG Evaluation and Full Index Plan](archive/git-history/465fdf9b4a/docs/superpowers/plans/2026-10-15-rag-evaluation-and-full-index.md) | MD | Git `465fdf9b4a` / `docs/superpowers/plans/2026-10-15-rag-evaluation-and-full-index.md` |
| RAG-DOC-187 | [Commerce + RAG Full-Flow Implementation Plan](archive/git-history/78794f409d/docs/superpowers/plans/2026-10-15-commerce-rag-full-flow.md) | MD | Git `78794f409d` / `docs/superpowers/plans/2026-10-15-commerce-rag-full-flow.md` |
| RAG-DOC-191 | [Commerce Frontend + RAG Full-Flow Integration Design](archive/git-history/870faa314d/docs/superpowers/specs/2026-10-15-commerce-rag-full-flow-design.md) | MD | Git `870faa314d` / `docs/superpowers/specs/2026-10-15-commerce-rag-full-flow-design.md` |
| RAG-DOC-188 | [RAG 공동 규격과 원본 근거 검증 구현 계획](archive/git-history/8a27f4ef0c/docs/superpowers/plans/2026-10-15-rag-contracts-and-evaluation.md) | MD | Git `8a27f4ef0c` / `docs/superpowers/plans/2026-10-15-rag-contracts-and-evaluation.md` |
| RAG-DOC-192 | [RAG 카테고리 안전 처리](archive/git-history/99e60bb01d/docs/superpowers/specs/2026-10-15-rag-category-quarantine-design.md) | MD | Git `99e60bb01d` / `docs/superpowers/specs/2026-10-15-rag-category-quarantine-design.md` |
| RAG-DOC-086 | [5432 RAG 인덱스 프로필 연결 계획](archive/multi-catalog/docs/superpowers/plans/2026-10-17-rag-only-catalog-profiles.md) | MD | `multi-catalog/docs/superpowers/plans/2026-10-17-rag-only-catalog-profiles.md` |
| RAG-DOC-087 | [전체 상품 RAG 카탈로그 프로필 설계](archive/multi-catalog/docs/superpowers/specs/2026-10-17-rag-catalog-profiles-design.md) | MD | `multi-catalog/docs/superpowers/specs/2026-10-17-rag-catalog-profiles-design.md`<br>Git `9796338348` / `docs/superpowers/specs/2026-10-17-rag-catalog-profiles-design.md` |
| RAG-DOC-145 | [Amazon Reviews API 구성 및 운영 기준](archive/old-project-worktree/docs/superpowers/plans/2026-10-14-amazon-reviews-api.md) | MD | `old-project-worktree/docs/superpowers/plans/2026-10-14-amazon-reviews-api.md` |
| RAG-DOC-146 | [Amazon Reviews PostgreSQL 운영 구현 계획](archive/old-project-worktree/docs/superpowers/plans/2026-10-14-amazon-reviews-postgresql-migration.md) | MD | `old-project-worktree/docs/superpowers/plans/2026-10-14-amazon-reviews-postgresql-migration.md` |
| RAG-DOC-147 | [Amazon Reviews RAG 구현 계획](archive/old-project-worktree/docs/superpowers/plans/2026-10-15-amazon-reviews-rag-implementation.md) | MD | `old-project-worktree/docs/superpowers/plans/2026-10-15-amazon-reviews-rag-implementation.md` |
| RAG-DOC-148 | [Amazon Reviews API 설계](archive/old-project-worktree/docs/superpowers/specs/2026-10-14-amazon-reviews-api-design.md) | MD | `old-project-worktree/docs/superpowers/specs/2026-10-14-amazon-reviews-api-design.md` |
| RAG-DOC-149 | [Amazon Reviews PostgreSQL 저장소 설계](archive/old-project-worktree/docs/superpowers/specs/2026-10-14-amazon-reviews-postgresql-design.md) | MD | `old-project-worktree/docs/superpowers/specs/2026-10-14-amazon-reviews-postgresql-design.md` |
| RAG-DOC-150 | [Amazon Reviews 하이브리드 RAG 검색 설계](archive/old-project-worktree/docs/superpowers/specs/2026-10-14-amazon-reviews-rag-design.md) | MD | `old-project-worktree/docs/superpowers/specs/2026-10-14-amazon-reviews-rag-design.md` |
| RAG-DOC-134 | [Required Intake Before Shopping RAG Search Implementation Plan](archive/project/docs/superpowers/plans/2026-10-17-rag-required-intake.md) | MD | `project/docs/superpowers/plans/2026-10-17-rag-required-intake.md` |
| RAG-DOC-135 | [Required Intake Before Shopping RAG Search](archive/project/docs/superpowers/specs/2026-10-17-rag-required-intake-design.md) | MD | `project/docs/superpowers/specs/2026-10-17-rag-required-intake-design.md` |
| RAG-DOC-045 | [RAG recommendation quality implementation](archive/quality/docs/superpowers/plans/2026-10-19-rag-recommendation-quality.md) | MD | `quality/docs/superpowers/plans/2026-10-19-rag-recommendation-quality.md`<br>Git `042d4e245d` / `docs/superpowers/plans/2026-10-19-rag-recommendation-quality.md` |

<a id="08-architecture-integration"></a>

## 구성·Commerce/LangChain 연동

| ID | 원문 | 형식 | 발견 위치/버전 |
|---|---|---|---|
| RAG-DOC-235 | [Product RAG Service](archive/bge-m3-activated/docs/product-rag-service.md) | MD | `bge-m3-activated/docs/product-rag-service.md` |
| RAG-DOC-057 | [Product RAG Backend](archive/bge-m3/README.md) | MD | `bge-m3/README.md`<br>`backend/README.md` |
| RAG-DOC-058 | [product-rag-bge-m3-embeddings.sql](archive/bge-m3/deploy/product-rag-bge-m3-embeddings.sql) | SQL | `bge-m3/deploy/product-rag-bge-m3-embeddings.sql`<br>Git `f166e81374` / `deploy/product-rag-bge-m3-embeddings.sql` |
| RAG-DOC-059 | [product-rag.sql](archive/bge-m3/deploy/product-rag.sql) | SQL | `bge-m3/deploy/product-rag.sql`<br>`backend/deploy/product-rag.sql`<br>`commerce-integration/deploy/product-rag.sql`<br>Git `83c04210e5` / `deploy/amazon-reviews-rag.sql` |
| RAG-DOC-061 | [Product RAG Service](archive/bge-m3/docs/product-rag-service.md) | MD | `bge-m3/docs/product-rag-service.md`<br>`backend/docs/product-rag-service.md` |
| RAG-DOC-067 | [RAG 검색의 현재 방향](archive/bge-m3/docs/rag-overall-direction.md) | MD | `bge-m3/docs/rag-overall-direction.md`<br>`backend/docs/rag-overall-direction.md`<br>`bge-m3-activated/docs/rag-overall-direction.md` |
| RAG-DOC-096 | [Product RAG Integration](archive/commerce-integration/README.md) | MD | `commerce-integration/README.md` |
| RAG-DOC-097 | [commerce-rag-demo.compose.yaml](archive/commerce-integration/deploy/commerce-rag-demo.compose.yaml) | YAML | `commerce-integration/deploy/commerce-rag-demo.compose.yaml` |
| RAG-DOC-098 | [격리된 전체 상품 Commerce RAG 데모](archive/commerce-integration/docs/commerce-rag-demo.md) | MD | `commerce-integration/docs/commerce-rag-demo.md` |
| RAG-DOC-099 | [Product RAG Service](archive/commerce-integration/docs/product-rag-service.md) | MD | `commerce-integration/docs/product-rag-service.md` |
| RAG-DOC-100 | [RAG Search Direction](archive/commerce-integration/docs/rag-overall-direction.md) | MD | `commerce-integration/docs/rag-overall-direction.md` |
| RAG-DOC-107 | [CORE_TASK_SCOPE — Shopping Brain + CS Agent](archive/commerce-storefront/CORE_TASK_SCOPE.md) | MD | `commerce-storefront/CORE_TASK_SCOPE.md` |
| RAG-DOC-108 | [최소 DB / Commerce State / Agent Tool 설계](archive/commerce-storefront/DATA_TOOL_DESIGN.md) | MD | `commerce-storefront/DATA_TOOL_DESIGN.md` |
| RAG-DOC-109 | [AI Commerce P0 Implementation Plan](archive/commerce-storefront/IMPLEMENTATION_PLAN.md) | MD | `commerce-storefront/IMPLEMENTATION_PLAN.md` |
| RAG-DOC-110 | [코디세이 AI 네이티브 Final Project 미션 요약](archive/commerce-storefront/MISSION_REQUIREMENTS.md) | MD | `commerce-storefront/MISSION_REQUIREMENTS.md` |
| RAG-DOC-111 | [프로젝트 컨텍스트 — 목표·방향·로드맵](archive/commerce-storefront/PROJECT_CONTEXT.md) | MD | `commerce-storefront/PROJECT_CONTEXT.md` |
| RAG-DOC-112 | [AI Commerce Environment](archive/commerce-storefront/README.md) | MD | `commerce-storefront/README.md` |
| RAG-DOC-113 | [핵심 와이어프레임 설계 — Shopping Brain + CS Agent](archive/commerce-storefront/WIREFRAME_PLAN.md) | MD | `commerce-storefront/WIREFRAME_PLAN.md` |
| RAG-DOC-114 | [Commerce Environment 감사 — 2026-10-07](archive/commerce-storefront/docs/COMMERCE_AUDIT.md) | MD | `commerce-storefront/docs/COMMERCE_AUDIT.md` |
| RAG-DOC-115 | [Implementation Decisions](archive/commerce-storefront/docs/IMPLEMENTATION_DECISIONS.md) | MD | `commerce-storefront/docs/IMPLEMENTATION_DECISIONS.md` |
| RAG-DOC-116 | [Verification Log](archive/commerce-storefront/docs/VERIFICATION_LOG.md) | MD | `commerce-storefront/docs/VERIFICATION_LOG.md` |
| RAG-DOC-117 | [Commerce RAG 데모](archive/commerce-storefront/docs/commerce-rag-demo.md) | MD | `commerce-storefront/docs/commerce-rag-demo.md` |
| RAG-DOC-118 | [화면 / Commerce Action ↔ 향후 Agent Tool — 누적 분석](archive/commerce-storefront/reference/toss-shopping/docs/AGENT_ACTION_MAP.md) | MD | `commerce-storefront/reference/toss-shopping/docs/AGENT_ACTION_MAP.md` |
| RAG-DOC-119 | [토스 AI Engineer 채용 공고 — 제공 원문](archive/commerce-storefront/references/TOSS_AI_ENGINEER.md) | MD | `commerce-storefront/references/TOSS_AI_ENGINEER.md` |
| RAG-DOC-185 | [RAG 진행 근거 — 2026-10-15](archive/git-history/17764ec271/docs/rag-progress-2026-10-15.md) | MD | Git `17764ec271` / `docs/rag-progress-2026-10-15.md` |
| RAG-DOC-186 | [RAG 작업 진행 현황 — 공유용](archive/git-history/3217153c62/docs/rag-progress-share-2026-10-15.md) | MD | Git `3217153c62` / `docs/rag-progress-share-2026-10-15.md` |
| RAG-DOC-214 | [RAG 진행 근거 — 2026-10-15](archive/git-history/44b23c7997/docs/rag-progress-2026-10-15.md) | MD | Git `44b23c7997` / `docs/rag-progress-2026-10-15.md` |
| RAG-DOC-179 | [Amazon Reviews RAG 서비스](archive/git-history/51afef7b6d/docs/amazon-reviews-rag-service.md) | MD | Git `51afef7b6d` / `docs/amazon-reviews-rag-service.md` |
| RAG-DOC-183 | [RAG 세 산출물 통합 결정](archive/git-history/93b5af7842/docs/rag-integration-decisions.md) | MD | Git `93b5af7842` / `docs/rag-integration-decisions.md` |
| RAG-DOC-184 | [RAG 전체 흐름과 방향](archive/git-history/a44991d664/docs/rag-overall-direction.md) | MD | Git `a44991d664` / `docs/rag-overall-direction.md` |
| RAG-DOC-180 | [격리된 Commerce RAG 데모](archive/git-history/bc4bd056a3/docs/commerce-rag-demo.md) | MD | Git `bc4bd056a3` / `docs/commerce-rag-demo.md` |
| RAG-DOC-182 | [RAG 검색 근거와 Agent 연동 개선 제안](archive/git-history/c6ec3e4038/docs/rag-improvement-collaboration-2026-10-15.md) | MD | Git `c6ec3e4038` / `docs/rag-improvement-collaboration-2026-10-15.md` |
| RAG-DOC-075 | [Codyssey Final Toss Backend](archive/langchain-http/README.md) | MD | `langchain-http/README.md` |
| RAG-DOC-076 | [LangChain HTTP retrieval](archive/langchain-http/deploy/product-rag-runtime/README.md) | MD | `langchain-http/deploy/product-rag-runtime/README.md`<br>Git `d0533e6022` / `deploy/product-rag-runtime/README.md` |
| RAG-DOC-077 | [LangChain 구성도 — HTTP 검색 연결 후](archive/langchain-http/deploy/product-rag-runtime/docs/langchain-architecture.md) | MD | `langchain-http/deploy/product-rag-runtime/docs/langchain-architecture.md`<br>`old-project-worktree/deploy/product-rag-runtime/docs/langchain-architecture.md`<br>Git `803c81ee69` / `deploy/product-rag-runtime/docs/langchain-architecture.md` |
| RAG-DOC-081 | [Product RAG Backend](archive/multi-catalog/README.md) | MD | `multi-catalog/README.md` |
| RAG-DOC-082 | [product-rag.sql](archive/multi-catalog/deploy/product-rag.sql) | SQL | `multi-catalog/deploy/product-rag.sql` |
| RAG-DOC-084 | [Product RAG Service](archive/multi-catalog/docs/product-rag-service.md) | MD | `multi-catalog/docs/product-rag-service.md` |
| RAG-DOC-085 | [RAG Search Direction](archive/multi-catalog/docs/rag-overall-direction.md) | MD | `multi-catalog/docs/rag-overall-direction.md` |
| RAG-DOC-139 | [Toss Final Project](archive/old-project-worktree/README.md) | MD | `old-project-worktree/README.md` |
| RAG-DOC-142 | [amazon-reviews-postgres.yml](archive/old-project-worktree/deploy/amazon-reviews-postgres.yml) | YML | `old-project-worktree/deploy/amazon-reviews-postgres.yml` |
| RAG-DOC-143 | [LangChain HTTP retrieval](archive/old-project-worktree/deploy/product-rag-runtime/README.md) | MD | `old-project-worktree/deploy/product-rag-runtime/README.md` |
| RAG-DOC-144 | [Amazon Reviews'23 API 명세](archive/old-project-worktree/docs/amazon-reviews-api.md) | MD | `old-project-worktree/docs/amazon-reviews-api.md` |
| RAG-DOC-120 | [Toss Ads AI Project](archive/project/README.md) | MD | `project/README.md` |
| RAG-DOC-131 | [product-rag-postgres.yml](archive/project/deploy/product-rag-postgres.yml) | YML | `project/deploy/product-rag-postgres.yml` |
| RAG-DOC-136 | [RAG 데이터 출처 범위](archive/project/presentations/rag-data-source-context.md) | MD | `project/presentations/rag-data-source-context.md` |
| RAG-DOC-137 | [rag-overview-2026-10-17.pdf](archive/project/presentations/rag-overview-2026-10-17.pdf) | PDF | `project/presentations/rag-overview-2026-10-17.pdf` |
| RAG-DOC-001 | [Product RAG recommendation quality](archive/quality/README.md) | MD | `quality/README.md` |
| RAG-DOC-003 | [product-rag.sql](archive/quality/deploy/product-rag.sql) | SQL | `quality/deploy/product-rag.sql`<br>Git `e2b16d235d` / `deploy/product-rag.sql` |
| RAG-DOC-026 | [추천 품질 개선 구현](archive/quality/docs/rag-recommendation-quality.md) | MD | `quality/docs/rag-recommendation-quality.md`<br>Git `30d0097376` / `docs/rag-recommendation-quality.md` |
| RAG-DOC-027 | [test_items2 RAG API 적용 기록](archive/quality/docs/rag-test-items2-api-activation-2026-10-19.md) | MD | `quality/docs/rag-test-items2-api-activation-2026-10-19.md` |
| RAG-DOC-044 | [rag-recommendation-quality-summary-2026-10-19.pdf](archive/quality/docs/reports/rag-recommendation-quality-summary-2026-10-19.pdf) | PDF | `quality/docs/reports/rag-recommendation-quality-summary-2026-10-19.pdf`<br>Git `86b2487c16` / `docs/reports/rag-recommendation-quality-summary-2026-10-19.pdf` |

<a id="09-team-rules"></a>

## 팀 규칙의 현재/과거 사본

| ID | 원문 | 형식 | 발견 위치/버전 |
|---|---|---|---|
| RAG-DOC-060 | [공통 작업 규칙과 RAG 적용 상태](archive/bge-m3/docs/common-work-rules.md) | MD | `bge-m3/docs/common-work-rules.md`<br>`backend/docs/common-work-rules.md`<br>`bge-m3-activated/docs/common-work-rules.md` |
| RAG-DOC-213 | [공통 작업 규칙과 RAG 적용 상태](archive/git-history/3c7ab872bd/docs/common-work-rules.md) | MD | Git `3c7ab872bd` / `docs/common-work-rules.md` |
| RAG-DOC-181 | [공통 작업 규칙과 RAG 적용 상태](archive/git-history/f2115a2a55/docs/common-work-rules.md) | MD | Git `f2115a2a55` / `docs/common-work-rules.md` |
| RAG-DOC-078 | [공통 작업 규칙 참조](archive/langchain-http/docs/common-work-rules.md) | MD | `langchain-http/docs/common-work-rules.md`<br>Git `e610d59fbc` / `docs/common-work-rules.md` |
| RAG-DOC-083 | [공통 작업 규칙과 RAG 적용 상태](archive/multi-catalog/docs/common-work-rules.md) | MD | `multi-catalog/docs/common-work-rules.md`<br>`commerce-integration/docs/common-work-rules.md` |
| RAG-DOC-151 | [팀 공통 Git 협업 기준 위치](archive/old-project-worktree/docs/team-git-workflow.md) | MD | `old-project-worktree/docs/team-git-workflow.md` |
| RAG-DOC-046 | [팀 공통 Git 협업 기준 — 정본](archive/quality/docs/team-git-workflow.md) | MD | `quality/docs/team-git-workflow.md`<br>`bge-m3/docs/team-git-workflow.md`<br>`langchain-http/docs/team-git-workflow.md`<br>`backend/docs/team-git-workflow.md`<br>Git `79b2bd6c32` / `docs/team-git-workflow.md`<br>`bge-m3-activated/docs/team-git-workflow.md` |

## 버전별 해석

- 현재 BGE 운영은 최신 실행 증거와 bge-m3-activated 출처의 전체 적재·운영 기록을 따른다.
- 14:47 MiniLM 구성은 [이전 기록](history/minilm-2026-10-20-1447/README.md)에 보존했다. BGE 전체 적용 이후의 현재 상태를 대신하지 않는다.
- 현재 API는 20:48 복구된 **0.3.1**이다. profile/product_type/가격·재고 검증을 BGE와 연결했다. [실제 복구·검증](bge-api-compat-recovery-2026-10-20.md). 기존 원문/PDF는 작성 당시 상태다.
- 현재 복구본은 가격·재고·유형·근거 선별을 BGE에 연결했다. HTTP LangChain invoke와 v3 전체 재청킹은 별도이며 아직 적용하지 않았다.
- 초기 가전 1만/이어폰/test_items와 test_items2의 평가 점수를 합산하지 않는다. BGE beauty 수치를 전체 정확도로 사용하지 않는다.
- 과거 rag-required-intake의 강제 입력 폼은 이후 사용자 제거 요청이 있었던 기록이다.
- 과거 서버/DB/포트는 역사적 기록이다. 현재 검색 DB 연결 기준은 5432/toss_rag다.
- 팀 규칙은 [Git 정본](../team-git-workflow.md)을 따른다. 과거 브랜치 접두사를 현 규칙으로 추정하지 않는다.

## 데이터 원본 ZIP

아래 기존 데이터 ZIP은 MiniLM 스냅샷이다. 최신 BGE 원시 벡터 내보내기로 바뀐 것이 아니다. 이 문서 묶음에는 위치와 메타데이터를 넣었다.

| 기존 자료 | 크기 | 내부 파일 |
|---|---:|---:|
| [test_items2_chunked_full_2026-10-19.zip](/home/aiteam/projects/toss-ads-project/data/exports/test_items2_chunked_full_2026-10-19.zip) | 273,558,559 bytes | 19 |
| [test_items_complete_2026-10-18.zip](/home/aiteam/projects/toss-ads-project/data/exports/test_items_complete_2026-10-18.zip) | 15,934,615 bytes | 40 |

## 제외 범위·검사

실제 .env/인증정보·DB 볼륨·모델 가중치·원본 행/벡터 덤프·의존성 캐시·RAG와 무관한 광고 기획서는 복사하지 않았다. 실행 코드 사본은 별도 reference-code에 포함하며 원문 문서 수에는 포함하지 않는다.

[문서 검사 기록](evidence/documentation-checks-2026-10-20.json)은 새 탐색 링크·사본 해시·수량 검사다. 과거 원문의 내부 상대 링크 전체 보증이나 새 검색 품질 평가가 아니다.

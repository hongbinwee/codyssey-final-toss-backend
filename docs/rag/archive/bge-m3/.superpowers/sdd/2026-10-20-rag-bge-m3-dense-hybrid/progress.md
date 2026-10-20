# SDD ledger — plan: docs/superpowers/plans/2026-10-20-rag-bge-m3-dense-hybrid.md

## Todos

- [x] Task 1: BGE-M3 dense embedding adapter
- [x] Task 2: additive embedding profile and vector storage
- [x] Task 3: resumable existing-chunk embedding CLI
- [x] Task 4: BM25/dense/hybrid comparison retrieval
- [x] Task 5: fixed-query evaluation and result report

## Pre-flight

- Workspace: `.worktrees/rag-bge-m3`; branch `feature/rag-bge-m3`; remote is `origin` for `hongbinwee/codyssey-final-toss-backend`.
- The worktree already contains unrelated user changes. In particular, `src/toss_ads/rag/__main__.py` is modified and `deploy/product-rag.Dockerfile` is untracked; preserve their existing contents and edit only what this plan needs.
- Task 1 -> Task 3: Task 1 produces `BgeM3Embedder` with `embed_documents`, `embed_query`, `dimension=1024`, and a model revision. Task 3 consumes it for document batches; names and dimensions match.
- Task 1 -> Task 4: Task 4 consumes the same `embed_query` method and 1,024-dimensional output; names and dimensions match.
- Task 2 -> Task 3: Task 3 consumes `register_embedding_profile`, `missing_embedding_texts`, `upsert_embedding_vectors`, `embedding_profile_counts`, and `mark_embedding_profile_ready`; method names and arguments match the plan.
- Task 2 -> Task 4: Task 4 consumes `search_embedding_vector` with run/model/vector/category and a `ready` profile; method names and arguments match the plan.
- Task 3 -> Task 5: Task 3 emits index summary JSON at the path Task 5 accepts as `--index-stats`; names match.
- Ruling: Store profile scope includes `category_scope=beauty` and `expected_chunk_count` because this run contains other categories while only beauty is embedded; this keeps `ready` scoped to the evaluated category without changing the approved `(run_id, embedding_model)` key. Cost if wrong: a future multi-category BGE backfill would need to expand or separately version this profile scope.

## Task Results

- Task 1: Ruling: use `python3` in run commands — this container has no `python` executable, while `python3` is available — cost if wrong: an alternate developer environment may need the command adjusted.
- Task 2: Ruling: run project tests in a repo-local `.venv` and install the declared service dependencies — system Python lacks `psycopg`, so the new store test stopped during import before reaching the feature behavior — cost if wrong: environment setup adds local disk use and package-install time.
Task 1: complete (commits e957afb..f5a7070, tests: env PYTHONPATH=src python3 -m unittest discover -s tests -p test_rag_bge_m3_embeddings.py → OK)
Task 2: complete (commits f5a7070..e97f133, tests: env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_rag_embedding_store.py → OK)
Task 3: complete (commits e97f133..5df1d8d, tests: env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_rag_embedding_indexer.py → OK)
Task 4: complete (commits 5df1d8d..fe96f70, tests: env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_rag_comparison.py → OK)

- Task 5 Ruling: RagStore.search_bm25 executes the repeated BM25 statement with prepare=False after the default Psycopg execution produced 3 failures in 40 repetitions and the unprepared path produced 0; this prevents the observed ParadeDB query-shape error during evaluation — cost if wrong: the BM25 statement gives up Psycopg automatic prepared-statement reuse.
- Task 5 Ruling: the installed executing-plans package has task-brief but no task-start or task-done; read the generated task brief, then record completion manually only after fresh test and commit evidence — cost if wrong: the ledger is not written by the helper script.
Task 5: complete (commits c609306..233f34f, tests: env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_rag_*.py' → 35 tests OK)
- Task 5 evaluation evidence: 5432/toss_rag, run e925490f-4f34-4c03-9248-eb9ebdfcde48, 78,595 beauty chunks; BM25, hybrid, and dense evaluation completed; Markdown/PDF extracted text and page layout checked.

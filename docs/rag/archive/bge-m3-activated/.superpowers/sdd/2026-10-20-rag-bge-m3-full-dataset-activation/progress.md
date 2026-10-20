# SDD ledger — plan: docs/superpowers/plans/2026-10-20-rag-bge-m3-full-dataset-activation.md

Base commit for implementation: `4eead41` (`docs: plan full-dataset BGE-M3 activation`).

Workspace: existing linked worktree `.worktrees/rag-bge-m3`, branch `feature/rag-bge-m3`; Git root and remote verified as `codyssey-final-toss-backend` / `https://github.com/hongbinwee/codyssey-final-toss-backend.git`.

Pre-flight interface scan:
- Task 1 → Task 2: `prepare_full_embedding_profile`, wildcard `*` store methods, and category counts match the all-category indexer preflight.
- Task 1 → Task 3: `embedding_profile_info`, wildcard dense search, and profile counts provide the metadata and readiness checks the API/retriever need.
- Task 2 → Task 5: the explicit `--all-categories` CLI and summary format match the full-run indexing and report steps.
- Task 3 → Tasks 4–5: BGE model/cache settings and readiness behavior match the runtime documentation and activation sequence.
- Task 4 → Task 5: docs retain MiniLM as the shared example default and describe only the local explicit BGE switch after indexing completes.
- Schema check: `category_scope` accepts text and has no constraint that excludes `*`; existing vector/profile foreign keys permit updating scope without deleting rows.

Pre-flight worktree note: pre-existing user changes include broad product-source/Amazon removals plus edits in `src/toss_ads/rag/__main__.py`, `api.py`, `config.py`, and `tests/test_rag_retriever.py`. Preserve those edits and stage only implementation hunks for this plan.

Tooling note: `task-start`, `task-brief`, and `task-done` are installed under the executing-plans/subagent-driven-development skills; use those scripts to create briefs and record final test runs.

## Tasks
- [x] Task 1: Add safe whole-run BGE profile scope — complete; `4eead41..e0bf6a6`.
- Task 1 evidence: RED `test_prepare_full_profile_promotes_complete_beauty_profile_to_building` and related whole-scope cases failed because the behavior was absent; focused store suite passed 14/14; full suite passed 43/43 with `env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests`.
- [x] Task 2: Index every missing BGE vector with resume support — complete; `e0bf6a6..db83e99`.
- Task 2 evidence: RED all-category tests failed before implementation; focused indexer suite passed 11/11; store suite passed 14/14; full suite passed 49/49. Added exact target run/version/category-count preflight, pinned BGE revision, `--all-categories` selection, resume behavior, and wildcard missing-text selection. `git diff --check` passed.
- Task 2: Ruling: Task 1's wildcard missing-text query still filtered `c.category = '*'` — changed it to select every category when scope is `*`, with a regression assertion. This adds `store.py` and its tests to the Task 2 commit because full-run embedding otherwise cannot make progress.
- [ ] Task 3: Route BGE queries through hybrid search and readiness — implementation complete, final task-done run and commit pending.
- Task 3 evidence so far: RED BGE factory/cache/routing and API readiness tests failed before implementation; focused indexer/retriever/API suites passed 12/12, 8/8, and 3/3; full suite passed 57/57. BGE readiness checks pinned revision, `*` scope, dimension, input length, expected chunk count, and actual vector count before query encoding.
- Task 3: Ruling: the shared factory also serves the source `index` command, whose active-run schema still writes 384D MiniLM vectors — reject source indexing when BGE is configured before loading the model or opening the DB. This prevents creation of a partial run; BGE remains an additional profile for an existing run.
- Task 3: Ruling: `deploy/product-rag-runtime.env.example` was already an untracked user-owned product-source file — added the BGE cache setting in the worktree but kept the file unstaged to preserve its existing contents; `Settings.from_env` derives the same path by default.
- [ ] Task 4: Document and safely switch the local API runtime — documentation and report prepared; final check and task-done record pending.
- Task 4 evidence so far: report JSON parses with `status=pending`, contains no credentials/source text; all 3 relative Markdown links resolve; `git diff --check` passed. Report-only commit: `c57d453`.
- Task 4: Ruling: `docs/product-rag-service.md` was a pre-existing untracked user-owned file — updated its full-run target and safe activation/rollback section in the worktree but committed only the new report, preserving the existing document from accidental whole-file staging. The documentation update remains available locally; cost if wrong is that it is absent from the Git commit.
- [ ] Task 5: Populate the full profile and activate BGE-M3.
Task 2: complete (commits e0bf6a6..db83e99, tests: env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests → OK)
Task 3: complete (commits db83e99..38e7c4f, tests: env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests → OK)
Task 4: complete (commits 38e7c4f..c57d453, tests: .venv/bin/python .superpowers/sdd/2026-10-20-rag-bge-m3-full-dataset-activation/task-4-check.py → documentation checks passed: 3 relative links, report JSON valid)
Task 5: complete (commits 987e304..61c8453, tests: env PYTHONPATH=src .venv/bin/python -m unittest discover -s tests → OK)

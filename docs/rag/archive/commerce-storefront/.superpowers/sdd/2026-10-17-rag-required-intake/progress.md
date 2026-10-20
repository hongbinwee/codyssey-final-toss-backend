# SDD ledger — plan: /home/aiteam/projects/toss-ads-project/docs/superpowers/plans/2026-10-17-rag-required-intake.md

Starting HEAD: 898740c3ea1dbf18247dcb210e9cda044a08134f
Worktree: codex/commerce-rag-storefront (already linked; preserve all pre-existing dirty files)

Ruling: make no commits — the approved plan and project WIP instruction prohibit commits; keep implementation reviewable as working-tree changes.

Pre-flight: Task 1 produces RagSearchRequest with required budget/use_case and Commerce-hydrated RagSearchResult; Task 2 consumes both in the Shopping-only search_rag tool. Signatures align.
Pre-flight: Task 1 produces shared FLAT_SHIPPING_FEE_WON and the RAG result shipping_fee_won; Task 3 consumes both for client validation and displayed totals. Signatures align.
Pre-flight: Task 1 lookupProducts dependency is supplied by the direct server route and Agent runtime; test call sites use fakes. No conflict.

- [x] Task 1: RAG validation and Commerce price filtering
- [x] Task 2: Shopping Agent tool, prompt, and stub behavior
- [x] Task 3: Direct RAG intake UI
- [x] Task 4: Shopping Agent gate and entry point

Baseline: `npm run test:unit` failed before changes: 608 tests, 568 passed, 40 failed. Failures are ENOENT reads of pre-existing shot artifacts (`shots/06b/.../audit-after.json`, `shots/pmqa079-network-review/.../preflight.json`, and `shots/06a/pmqa043/commerce_test_prdump.sql`). These artifacts are outside this feature; preserve them and use focused tests plus typecheck for this work, then report full-suite baseline failures.

Task 1: complete (uncommitted; tests: `node --test tests/unit/rag-search.test.ts tests/unit/server-rag-search.test.ts` → 11/11 passed).
Task 1: Ruling: retain the existing RagEvidence response shape — evidence is attached to its parent RagSearchItem, so the exact-budget test asserts the evidence text instead of a nested product_id field.
Task 1: Ruling: `searchRag` now constructs the upstream query from validated `use_case` + unchanged `original_question` instead of trusting the Agent-supplied `query`; a red/green regression test showed the prior service could forward a partial query and omit required conditions. The plan step was amended to match this enforcement.

- [x] Task 1: RAG validation and Commerce price filtering

Task 2: complete (uncommitted; tests: `node --test tests/unit/agent-rag.test.ts` → 5/5 passed, including Commerce-backed RAG comparison cards).
- [x] Task 2: Shopping Agent tool, prompt, and stub behavior

Task 3: complete (uncommitted; tests: `node --test tests/unit/rag-search-ui.test.ts` → 9/9 passed). RAG form snapshots submitted criteria, invalidates previous results when criteria change, and displays Commerce variant prices plus the authoritative shipping fee. Plan file list amended to include `src/web/styles.css`.
- [x] Task 3: Direct RAG intake UI

Task 4: complete (uncommitted; tests: `node --test tests/unit/agent-gate.test.ts tests/unit/server-rag-search.test.ts` → 3 tests passed; `npm run check` passed). Shopping Brain is enabled; CS remains unavailable through both the UI gate and API route. Plan amended to track the API boundary check.
- [x] Task 4: Shopping Agent gate and entry point

Review findings resolved: RAG comparison cards now use nested Commerce product summaries, prices, availability, and review IDs; effective combined query length is checked before Agent service invocation and RAG fetch; UI copy states the result is from at most 20 ranked candidates; returned RAG product metadata has pricing fields stripped before it reaches the Agent.

Final verification: focused feature suite `node --test tests/unit/rag-search-ui.test.ts tests/unit/agent-rag.test.ts tests/unit/agent-gate.test.ts tests/unit/rag-search.test.ts tests/unit/server-rag-search.test.ts` → 29/29 passed; `npm run check`, `npm run build`, and `git diff --check` passed.
Final full unit suite: 621 tests, 581 passed, 40 failed. The 40 failures are the same baseline ENOENT failures for the missing `shots/06b/.../audit-after.json`, `shots/pmqa079-network-review/.../preflight.json`, and `shots/06a/pmqa043/commerce_test_prdump.sql` artifacts. Full run log: `/tmp/rag-required-intake-final-unit.log`.

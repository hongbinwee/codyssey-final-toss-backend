# Required Intake Before Shopping RAG Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Require a one-item, shipping-inclusive KRW budget and use case before either Shopping Agent or direct RAG search can query upstream, then return only RAG-ranked candidates whose current Commerce variant price fits.

**Architecture:** Keep RAG responsible for relevance and evidence, and use current Commerce catalog data as the source for variant prices and the 3,000 KRW shipping fee. Add server-side intake validation and price filtering shared by the Agent tool and direct search endpoint; mirror the intake requirement in the Shopping Brain prompt and direct search form. Enable only the Shopping Agent entry point and retain the local stub's explicit, non-RAG behavior.

**Tech Stack:** TypeScript, Node built-in test runner, React, existing Commerce catalog and RAG clients.

**Spec:** `docs/superpowers/specs/2026-10-17-rag-required-intake-design.md`

## Global Constraints

- Budget is a positive integer in KRW for one item, including the current flat shipping fee of 3,000 KRW.
- A non-empty use case and valid budget are both required before any upstream RAG request.
- Preserve the user's original question; send the use case and stated product conditions as the RAG query.
- Filter RAG IDs against current Commerce variants with `unit_price_won + shipping_fee_won <= budget_won`; never trust RAG metadata prices.
- Missing Commerce products and products without an affordable active variant are excluded; preserve RAG order and evidence for remaining products.
- Do not change credentials, the RAG index, supported categories, CS tools, or product write controls.
- Preserve the existing dirty `commerce-storefront` worktree and make no commits during this WIP checkpoint.

## Review Focus

- A variant exactly at the budget after shipping remains eligible, while one won over budget is excluded. **Test:** Task 1 `test_filters_rag_ranked_items_by_current_commerce_price_and_shipping`.
- Missing, blank, vague/non-integer, zero, and below-shipping budgets make zero upstream calls. **Test:** Task 1 `test_rejects_incomplete_or_unspendable_intake_without_fetching` and Task 2 `test_search_rag_tool_rejects_missing_slots_before_service_call`.
- A RAG product absent from Commerce or with no eligible variant is excluded even if its RAG metadata contains a low price. **Test:** Task 1 `test_excludes_products_without_affordable_commerce_variants`.
- RAG receives the use case plus stated conditions while `original_question` remains unchanged. **Test:** Task 1 `test_forwards_intake_query_without_budget_as_a_price_filter` and Task 3 `test_request_keeps_original_question_and_builds_query_from_use_case`.
- With the local stub selected, no RAG tool is called or claimed and every user-facing stub response remains labeled. **Test:** Task 2 `test_stub_never_requests_rag_and_labels_empty_results`.

---

### Task 1: Enforce intake and Commerce price filtering in the RAG service

**Files:**
- Create: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/shipping.ts`
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/catalog.ts`
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/contracts.ts`
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/rag-search.ts`
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/server.ts`
- Test: `codyssey-final-toss-backend/.worktrees/commerce-storefront/tests/unit/rag-search.test.ts`
- Test: `codyssey-final-toss-backend/.worktrees/commerce-storefront/tests/unit/server-rag-search.test.ts`

**Interfaces:**
- Consumes: existing `getProductSummariesByIds(productIds)` and `FLAT_SHIPPING_FEE_WON` catalog behavior.
- Produces: shared `FLAT_SHIPPING_FEE_WON = 3000`; `RagSearchRequest` with required `original_question`, `use_case`, `query`, `budget_won`, and `top_k`, plus optional `category`; `RagSearchResult.budget_won` and `shipping_fee_won`; `RagSearchItem.commerce_product: ProductSummary`; `RagSearchDeps.lookupProducts(productIds: readonly string[]): Promise<ProductSummary[]>`.

- [x] **Step 1: Add failing service tests** named `test_rejects_incomplete_or_unspendable_intake_without_fetching`, `test_filters_rag_ranked_items_by_current_commerce_price_and_shipping`, `test_excludes_products_without_affordable_commerce_variants`, `test_forwards_intake_query_without_budget_as_a_price_filter`, `test_search_query_uses_the_confirmed_use_case_and_original_question`, and `test_rag_result_removes_untrusted_price_metadata`. Cover missing/blank `use_case`, absent or non-integer/zero `budget_won`, budget below 3,000 KRW, exact budget boundary, one-won-over boundary, oversized combined query, missing catalog ID, and RAG metadata price disagreeing with Commerce. Assert invalid requests call `fetchRag` zero times; assert valid results preserve rank/evidence and attach only Commerce variants with unit price plus 3,000 KRW at or below budget. Update existing request, dependency, and result fixtures for the required intake and Commerce fields.
- [x] **Step 2: Run the focused tests and confirm they fail** with missing request fields/Commerce filtering behavior. Run from the nested worktree: `node --test tests/unit/rag-search.test.ts`.
- [x] **Step 3: Implement the shared shipping constant and RAG contract.** Keep the existing `catalog.ts` export compatible by re-exporting the shared constant. Validate `original_question` (max 4,000 chars), `use_case` (max 1,000 chars), and `query` (max 1,000 chars) as nonblank, `top_k` as an integer from 1 to 20, `budget_won` as a positive safe integer, and reject `budget_won < FLAT_SHIPPING_FEE_WON` before endpoint resolution or fetch.
- [x] **Step 4: Hydrate and filter ranked IDs in `searchRag`.** Add `lookupProducts` to `RagSearchDeps`, look up only the returned unique RAG product IDs, preserve upstream order, drop missing products and products with no active variant satisfying `unit_price_won + FLAT_SHIPPING_FEE_WON <= budget_won`, and put the Commerce summary with only eligible variants on `commerce_product`, recomputing its availability from those variants. Include the confirmed `budget_won` and current `shipping_fee_won` in every `RagSearchResult`, including upstream no-results responses. Keep RAG evidence and ranking unchanged. Do not forward `budget_won` as an upstream price filter; build the upstream `query` from the validated use case and unchanged `original_question`, so the required slots remain in the query even if an Agent tool call supplies a partial `query`. Remove price-related fields from untrusted RAG product metadata before returning results. Preserve current retryable timeout and invalid-upstream-response behavior.
- [x] **Step 5: Add failing HTTP coverage** showing an authenticated request missing either slot returns HTTP 400 and makes zero RAG calls, while a complete request reaches the upstream path. Run: `node --test tests/unit/server-rag-search.test.ts`.
- [x] **Step 6: Wire the server's direct RAG route to `getProductSummariesByIds`, then run both focused test files** and confirm invalid intake is rejected before network access and eligible results use Commerce prices.

### Task 2: Add the Shopping Agent RAG tool and required clarification prompt

**Files:**
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/agent.ts`
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/llm.ts`
- Test: `codyssey-final-toss-backend/.worktrees/commerce-storefront/tests/unit/agent-rag.test.ts`

**Interfaces:**
- Consumes: Task 1 `RagSearchRequest`, `RagSearchResult`, `searchRag`, and `getProductSummariesByIds`.
- Produces: read-only `search_rag` available only to the `shopping` brain, with required `original_question`, `use_case`, `query`, `budget_won`, and `top_k`, optional `category`; exported `AgentDeps.searchRag(input: unknown): Promise<ToolResult<unknown>>` injection; private `defaultAgentDeps(): AgentDeps`; `executeTool(name: string, rawArgs: unknown, ctx: RequestContext, clientActionId: string, brain: Brain = "shopping", deps: AgentDeps = defaultAgentDeps()): Promise<ToolResult<unknown>>` and `runAgentTurn(req: AgentTurnRequest, ctx: RequestContext, provider: Provider, deps: AgentDeps = defaultAgentDeps()): Promise<AgentTurnResult>` pass that dependency for DB-free unit coverage.

- [x] **Step 1: Add failing Agent tests** named `test_shopping_prompt_requests_only_missing_intake`, `test_search_rag_tool_rejects_missing_slots_before_service_call`, `test_complete_search_rag_tool_call_forwards_all_arguments`, `test_rag_compare_card_uses_commerce_product_prices`, and `test_stub_never_requests_rag_and_labels_empty_results`. Inspect the Shopping system message and tool schema, verify `search_rag` is absent for CS, verify missing required slots fail before the injected RAG service is invoked, and verify a complete tool call passes the original question, use case, query, category, top-k, and budget intact. Verify RAG comparison cards use the nested Commerce product summary.
- [x] **Step 2: Run `node --test tests/unit/agent-rag.test.ts`** and confirm the tests fail because the tool, prompt rules, and injected service are absent.
- [x] **Step 3: Add the read-only Shopping-only `search_rag` tool** and a default runtime dependency that calls Task 1 `searchRag` with `process.env.RAG_API_BASE_URL`, global `fetch`, and `getProductSummariesByIds`. Pass an injectable `AgentDeps` through `runAgentTurn` to `executeTool`; leave other tools and CS registration unchanged.
- [x] **Step 4: Extend `SHOPPING_SYSTEM`** to require explicit one-item total budget including shipping and a use case, treat vague amounts as missing, ask only for missing slots (both together when both are missing), retain any already supplied slot in the conversation, not call RAG until complete, and never raise the budget or broaden constraints after an empty result.
- [x] **Step 5: Keep Shopping stub final responses explicitly labeled and RAG-free.** Preserve `stubProvider`'s existing `search_products` behavior and all CS stub behavior; add the `(로컬 stub — LLM 미설정)` label to the Shopping empty-result response too, and verify the Shopping stub's first response requests `search_products`, never `search_rag`.
- [x] **Step 6: Run the focused Agent tests** and confirm prompt/tool visibility, zero service calls for rejected tool arguments, correct complete request forwarding, and labeled stub behavior.

### Task 3: Require budget and use case in the direct RAG search screen

**Files:**
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/web/rag-search.ts`
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/web/screens/Search.tsx`
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/web/styles.css`
- Test: `codyssey-final-toss-backend/.worktrees/commerce-storefront/tests/unit/rag-search-ui.test.ts`

**Interfaces:**
- Consumes: Task 1 required request fields, `commerce_product`, `RagSearchResult.shipping_fee_won`, and shared shipping constant.
- Produces: `buildRagSearchRequest(originalQuestion, useCase, budgetInput, category?)` returning `RagSearchRequest | null`; `submitRagSearch(input: RagSearchRequest | null, post)` returning `null` without invoking `post` for invalid intake.

- [x] **Step 1: Add failing UI-helper tests** named `test_request_keeps_original_question_and_builds_query_from_use_case`, `test_invalid_intake_never_posts`, and `test_rag_display_uses_commerce_prices_and_shipping_total`. Cover required query/use case/budget, comma-formatted integer KRW, zero/decimal/text/below-shipping budget rejection, original question preservation, use-case-plus-conditions query construction, Commerce-only displayed prices, and zero `post` calls when the request builder returns `null`.
- [x] **Step 2: Run `node --test tests/unit/rag-search-ui.test.ts`** and confirm the new intake tests fail.
- [x] **Step 3: Implement request parsing and the no-submit guard.** Parse only digit strings after removing grouping commas; reject non-safe integers, missing values, totals below 3,000 KRW, and a combined query longer than 1,000 characters. Build `query` by joining trimmed use case and original question while preserving the latter separately.
- [x] **Step 4: Add budget and use-case inputs to RAG mode in `Search.tsx`.** Keep the current keyword mode unchanged; render the intake panel whenever RAG mode is selected (including before the first query is submitted), label the fields “사용 용도” and “상품 1개 배송비 포함 총 예산”, disable the RAG submit control and return early from the submit handler when the request builder returns `null`, and show a clear inline reason when the amount is below shipping. Render product title and eligible variant unit prices from `commerce_product` rather than RAG metadata. For each displayed eligible variant, show its Commerce unit price and the total after adding the result's `shipping_fee_won`.
- [x] **Step 5: Change the empty RAG result copy** to state that no product matched the current use case and shipping-inclusive budget among the maximum 20 ranked RAG candidates, without suggesting that the user raise the budget or broaden requirements. Label the result scope as a maximum of 20 candidates rather than the entire catalog.
- [x] **Step 6: Run the focused UI helper tests** and confirm valid requests carry both slots and invalid requests invoke no API callback.

### Task 4: Activate only the Shopping Agent entry point

**Files:**
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/web/agent-gate.ts`
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/web/app.tsx`
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/server.ts` (enforce Shopping-only at the API boundary)
- Test: `codyssey-final-toss-backend/.worktrees/commerce-storefront/tests/unit/agent-gate.test.ts`
- Test: `codyssey-final-toss-backend/.worktrees/commerce-storefront/tests/unit/server-rag-search.test.ts`

**Interfaces:**
- Consumes: existing `AgentTurnPayload` and `sendAgentTurn` interface.
- Produces: enabled Shopping turn callback; CS requests remain blocked by the UI gate and server API; AI nav and menu entries open the Shopping Agent without the “준비중” state.

- [x] **Step 1: Update gate tests first** to assert a Shopping payload invokes the post callback once and a CS payload invokes it zero times with `AGENT_UNAVAILABLE`.
- [x] **Step 2: Run `node --test tests/unit/agent-gate.test.ts`** and confirm failure against the current globally closed gate.
- [x] **Step 3: Enable the Shopping brain in `agent-gate.ts`** while retaining fail-closed behavior for `brain: "cs"`.
- [x] **Step 4: Enable the AI nav and menu entries in `app.tsx`** to open `setAgentOpen("shopping")`; remove the disabled and “준비중” indicators for those entries.
- [x] **Step 5: Run the focused gate test** and then run `npm run check` from the nested worktree to catch cross-task type mismatches. Do not commit.
- [x] **Step 6: Verify the server rejects CS Brain requests** with HTTP 403 before invoking the Agent runtime; run the existing focused server route test.

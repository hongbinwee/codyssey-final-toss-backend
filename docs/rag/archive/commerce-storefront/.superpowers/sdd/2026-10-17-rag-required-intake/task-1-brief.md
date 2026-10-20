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

- [ ] **Step 1: Add failing service tests** named `test_rejects_incomplete_or_unspendable_intake_without_fetching`, `test_filters_rag_ranked_items_by_current_commerce_price_and_shipping`, `test_excludes_products_without_affordable_commerce_variants`, and `test_forwards_intake_query_without_budget_as_a_price_filter`. Cover missing/blank `use_case`, absent or non-integer/zero `budget_won`, budget below 3,000 KRW, exact budget boundary, one-won-over boundary, missing catalog ID, and RAG metadata price disagreeing with Commerce. Assert invalid requests call `fetchRag` zero times; assert valid results preserve rank/evidence and attach only Commerce variants with unit price plus 3,000 KRW at or below budget. Update existing request, dependency, and result fixtures for the required intake and Commerce fields.
- [ ] **Step 2: Run the focused tests and confirm they fail** with missing request fields/Commerce filtering behavior. Run from the nested worktree: `node --test tests/unit/rag-search.test.ts`.
- [ ] **Step 3: Implement the shared shipping constant and RAG contract.** Keep the existing `catalog.ts` export compatible by re-exporting the shared constant. Validate `original_question` (max 4,000 chars), `use_case` (max 1,000 chars), and `query` (max 1,000 chars) as nonblank, `top_k` as an integer from 1 to 20, `budget_won` as a positive safe integer, and reject `budget_won < FLAT_SHIPPING_FEE_WON` before endpoint resolution or fetch.
- [ ] **Step 4: Hydrate and filter ranked IDs in `searchRag`.** Add `lookupProducts` to `RagSearchDeps`, look up only the returned unique RAG product IDs, preserve upstream order, drop missing products and products with no active variant satisfying `unit_price_won + FLAT_SHIPPING_FEE_WON <= budget_won`, and put the Commerce summary with only eligible variants on `commerce_product`, recomputing its availability from those variants. Include the confirmed `budget_won` and current `shipping_fee_won` in every `RagSearchResult`, including upstream no-results responses. Keep RAG evidence and ranking unchanged. Do not forward `budget_won` as an upstream price filter; forward the supplied combined `query` and unchanged `original_question`. Preserve current retryable timeout and invalid-upstream-response behavior.
- [ ] **Step 5: Add failing HTTP coverage** showing an authenticated request missing either slot returns HTTP 400 and makes zero RAG calls, while a complete request reaches the upstream path. Run: `node --test tests/unit/server-rag-search.test.ts`.
- [ ] **Step 6: Wire the server's direct RAG route to `getProductSummariesByIds`, then run both focused test files** and confirm invalid intake is rejected before network access and eligible results use Commerce prices.


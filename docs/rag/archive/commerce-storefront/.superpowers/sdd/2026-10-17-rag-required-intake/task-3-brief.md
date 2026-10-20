### Task 3: Require budget and use case in the direct RAG search screen

**Files:**
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/web/rag-search.ts`
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/web/screens/Search.tsx`
- Test: `codyssey-final-toss-backend/.worktrees/commerce-storefront/tests/unit/rag-search-ui.test.ts`

**Interfaces:**
- Consumes: Task 1 required request fields, `commerce_product`, `RagSearchResult.shipping_fee_won`, and shared shipping constant.
- Produces: `buildRagSearchRequest(originalQuestion, useCase, budgetInput, category?)` returning `RagSearchRequest | null`; `submitRagSearch(input: RagSearchRequest | null, post)` returning `null` without invoking `post` for invalid intake.

- [ ] **Step 1: Add failing UI-helper tests** named `test_request_keeps_original_question_and_builds_query_from_use_case`, `test_invalid_intake_never_posts`, and `test_rag_display_uses_commerce_prices_and_shipping_total`. Cover required query/use case/budget, comma-formatted integer KRW, zero/decimal/text/below-shipping budget rejection, original question preservation, use-case-plus-conditions query construction, Commerce-only displayed prices, and zero `post` calls when the request builder returns `null`.
- [ ] **Step 2: Run `node --test tests/unit/rag-search-ui.test.ts`** and confirm the new intake tests fail.
- [ ] **Step 3: Implement request parsing and the no-submit guard.** Parse only digit strings after removing grouping commas; reject non-safe integers, missing values, totals below 3,000 KRW, and a combined query longer than 1,000 characters. Build `query` by joining trimmed use case and original question while preserving the latter separately.
- [ ] **Step 4: Add budget and use-case inputs to RAG mode in `Search.tsx`.** Keep the current keyword mode unchanged; render the intake panel whenever RAG mode is selected (including before the first query is submitted), label the fields “사용 용도” and “상품 1개 배송비 포함 총 예산”, disable the RAG submit control and return early from the submit handler when the request builder returns `null`, and show a clear inline reason when the amount is below shipping. Render product title and eligible variant unit prices from `commerce_product` rather than RAG metadata. For each displayed eligible variant, show its Commerce unit price and the total after adding the result's `shipping_fee_won`.
- [ ] **Step 5: Change the empty RAG result copy** to state that no product matched the current use case and shipping-inclusive budget without suggesting that the user raise the budget or broaden requirements.
- [ ] **Step 6: Run the focused UI helper tests** and confirm valid requests carry both slots and invalid requests invoke no API callback.


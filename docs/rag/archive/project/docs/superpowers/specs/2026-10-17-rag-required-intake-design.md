# Required Intake Before Shopping RAG Search

**Status:** Design approved; implementation plan in review
**Date:** 2026-10-17

## Goal

Require an explicit purchase budget and use case before the Shopping Agent or the direct RAG search screen can run an RAG query. The chatbot asks for whichever required information is missing, then searches with the confirmed use case and returns only candidates whose current Commerce price fits the confirmed budget.

## Current state

- `SHOPPING_SYSTEM` does not require a budget or a use case before product search.
- Shopping Agent tools do not include RAG search.
- The Agent UI is fail-closed, and its entry point is marked as coming soon.
- The RAG search screen calls `/api/rag/search` directly with only a query; it can bypass a chatbot prompt.
- The RAG service ranks evidence but is not the source of current Commerce price. Commerce catalog variants and the configured flat shipping fee are authoritative for the budget check.

## User flow

The required intake has two slots:

1. **Budget:** a positive integer in KRW for buying one item, including the current flat shipping fee of 3,000 KRW.
2. **Use case:** a non-empty description of what the item will be used for.

When a user asks for a recommendation:

- If both slots are absent, ask for the budget and use case in one concise follow-up.
- If only one slot is absent, ask only for that slot and retain the supplied value in the conversation.
- Treat vague amounts such as “cheap” as missing; ask for a numeric KRW amount. Do not invent or assume a budget or use case.
- Do not call the RAG upstream service while either slot is missing or invalid.
- Once both are valid, query RAG using the use case and other stated product conditions. Preserve the user's original question separately.
- Filter returned product IDs against current Commerce catalog variants using `unit_price_won + shipping_fee_won <= budget_won`. Show prices from Commerce data, not RAG metadata.
- If no returned candidate fits the budget, report no qualifying result. Do not raise the budget or broaden the constraints silently.
- If the budget is below the flat shipping fee, explain that no one-item purchase can fit and do not call RAG.

The current demo supports the `earphones` category. This work does not expand the supported catalog or index.

## Components and boundaries

### Shopping Agent

- Extend the Shopping Brain system prompt with the two required slots and the clarification behavior above.
- Add a read-only `search_rag` tool for the Shopping Brain. It accepts the original question, use case/query, category, result count, and explicit budget.
- Validate the tool arguments in the server-side tool executor. Missing or blank values, and non-positive or non-integer budgets, must fail before any RAG network request.
- Enable the existing Shopping Agent UI entry point and turn gate. CS behavior and tools remain unchanged.
- Keep the existing provider selection; this change does not add credentials or make live-provider calls during implementation. Live conversational behavior still requires the configured live provider. The local stub must retain its explicit “로컬 stub — LLM 미설정” label, must not call RAG, and must not claim that RAG ran.

### Direct RAG search

- Add required budget and use-case inputs to the RAG search mode.
- Extend the browser request type and server validation to require both inputs before forwarding a query.
- The UI must not submit while either input is missing or invalid. The server must independently reject such requests before calling `fetchRag`.
- Reuse the same Commerce catalog price check as the Agent flow so the direct path cannot bypass the budget.

### Price and evidence sources

- RAG remains responsible for relevance ranking and source evidence.
- Commerce remains authoritative for product identity, current variant prices, and shipping fee.
- The backend applies the price constraint to RAG-returned product IDs using current Commerce catalog data. The upstream RAG request is not treated as a hard price filter.
- Keep RAG evidence attached to each returned product so the Agent can ground its explanation.

## Error behavior

- Missing or invalid intake: clarify in the chat; return a validation error on direct API calls, without contacting upstream RAG.
- No candidate satisfies the budget: return an empty result with a truthful explanation; never relax the amount.
- RAG timeout or invalid upstream response: preserve the current retryable error behavior and do not fabricate candidates or evidence.
- Missing Commerce catalog data for a RAG product: exclude that product from budget-qualified recommendations rather than trusting RAG metadata prices.

## Acceptance criteria

1. A chat request without either required slot produces a focused follow-up and makes zero RAG network calls.
2. A request with only budget asks for use case; a request with only use case or a vague budget asks for a numeric budget; each makes zero RAG calls.
3. A complete request calls RAG using the use case and stated conditions, then includes only products whose current variant price plus shipping is within budget.
4. No result outside the budget is returned even if RAG ranks it highly.
5. The direct RAG UI cannot submit without both fields, and the server endpoint independently rejects incomplete requests before network access.
6. The existing Shopping Agent entry point is available for the configured provider. If provider selection falls back to the local stub, its response remains explicitly labeled and it does not call RAG or claim an RAG-backed answer. CS tools, product write controls, and RAG indexing remain unchanged.
7. Tests cover missing fields, partial fields, invalid amounts, zero upstream calls on rejected requests, exact budget boundaries, and both entry points.

## Non-goals

- Changing RAG indexing, embeddings, ranking, or supported categories.
- Persisting intake slots as long-term user preferences.
- Changing the CS Brain or enabling its currently disabled order inquiry paths.
- Provisioning or changing any LLM or RAG credentials.
- Relaxing the requested budget when fewer than three candidates match.

## Risks and limits

- The upstream RAG API returns at most 20 candidates. Filtering those candidates by current Commerce prices can return fewer qualifying results even when additional in-budget products exist lower in the full ranking. The application must not represent this as an exhaustive catalog search.
- The local Agent uses a stub when no live LLM provider is configured. The stub can support only its explicitly implemented behavior; actual natural-language clarification and query formation require a configured live provider.
- The flat shipping fee is currently a project constant. If shipping becomes product-specific, the budget check must use the product's authoritative shipping rule instead.

## Implementation constraints

- Existing uncommitted changes in the `commerce-storefront` worktree are user work and must be preserved; only files needed for this flow may be edited.
- No credentials, protected databases, seed data, or RAG index contents are changed.
- The existing project instruction prohibits commits during the current WIP checkpoint, so the design and implementation remain uncommitted unless that instruction changes.

### Task 2: Add the Shopping Agent RAG tool and required clarification prompt

**Files:**
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/agent.ts`
- Modify: `codyssey-final-toss-backend/.worktrees/commerce-storefront/src/llm.ts`
- Test: `codyssey-final-toss-backend/.worktrees/commerce-storefront/tests/unit/agent-rag.test.ts`

**Interfaces:**
- Consumes: Task 1 `RagSearchRequest`, `RagSearchResult`, `searchRag`, and `getProductSummariesByIds`.
- Produces: read-only `search_rag` available only to the `shopping` brain, with required `original_question`, `use_case`, `query`, `budget_won`, and `top_k`, optional `category`; exported `AgentDeps.searchRag(input: unknown): Promise<ToolResult<unknown>>` injection; private `defaultAgentDeps(): AgentDeps`; `executeTool(name: string, rawArgs: unknown, ctx: RequestContext, clientActionId: string, brain: Brain = "shopping", deps: AgentDeps = defaultAgentDeps()): Promise<ToolResult<unknown>>` and `runAgentTurn(req: AgentTurnRequest, ctx: RequestContext, provider: Provider, deps: AgentDeps = defaultAgentDeps()): Promise<AgentTurnResult>` pass that dependency for DB-free unit coverage.

- [ ] **Step 1: Add failing Agent tests** named `test_shopping_prompt_requests_only_missing_intake`, `test_search_rag_tool_rejects_missing_slots_before_service_call`, `test_complete_search_rag_tool_call_forwards_all_arguments`, and `test_stub_never_requests_rag_and_labels_empty_results`. Inspect the Shopping system message and tool schema, verify `search_rag` is absent for CS, verify missing required slots fail before the injected RAG service is invoked, and verify a complete tool call passes the original question, use case, query, category, top-k, and budget intact.
- [ ] **Step 2: Run `node --test tests/unit/agent-rag.test.ts`** and confirm the tests fail because the tool, prompt rules, and injected service are absent.
- [ ] **Step 3: Add the read-only Shopping-only `search_rag` tool** and a default runtime dependency that calls Task 1 `searchRag` with `process.env.RAG_API_BASE_URL`, global `fetch`, and `getProductSummariesByIds`. Pass an injectable `AgentDeps` through `runAgentTurn` to `executeTool`; leave other tools and CS registration unchanged.
- [ ] **Step 4: Extend `SHOPPING_SYSTEM`** to require explicit one-item total budget including shipping and a use case, treat vague amounts as missing, ask only for missing slots (both together when both are missing), retain any already supplied slot in the conversation, not call RAG until complete, and never raise the budget or broaden constraints after an empty result.
- [ ] **Step 5: Keep Shopping stub final responses explicitly labeled and RAG-free.** Preserve `stubProvider`'s existing `search_products` behavior and all CS stub behavior; add the `(로컬 stub — LLM 미설정)` label to the Shopping empty-result response too, and verify the Shopping stub's first response requests `search_products`, never `search_rag`.
- [ ] **Step 6: Run the focused Agent tests** and confirm prompt/tool visibility, zero service calls for rejected tool arguments, correct complete request forwarding, and labeled stub behavior.


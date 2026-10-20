# Commerce + RAG Full-Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the Commerce demo storefront to a separate RAG index built from the pinned digital fixtures, then verify search → product detail → variant selection → cart in a browser.

**Architecture:** The Python RAG service reads the Commerce fixture JSON as a versioned read-only source and indexes only `digital`. An authenticated Commerce server route proxies search, hydrates exact RAG product IDs from the Commerce DB, and returns catalog-owned summaries with RAG evidence; the existing detail and cart paths remain authoritative for purchase data.

**Tech Stack:** Python 3.12, FastAPI, PostgreSQL with `vector`/`pg_search`, FastEmbed, TypeScript, Node.js 24, PostgreSQL 17, React, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-15-commerce-rag-full-flow-design.md`

## Global Constraints

- Preserve the current RAG database, active index, API process, Commerce databases, and existing containers; do not write, reset, stop, or delete them.
- Use a new Commerce demo database and a new RAG staging database, each with a new volume and an unused loopback-only port.
- Index only Commerce category `digital`: 7 products, 12 variants, and 25 reviews; preserve stable `p-d-*` product IDs.
- Keep variant price and stock out of semantic evidence; Commerce DB is the source of truth for displayed price, stock, options, reviews, and images.
- Proxy browser requests through authenticated `POST /api/rag/search`; do not expose RAG URLs or credentials to the browser.
- Preserve RAG rank and evidence order; never substitute a similar product for an unresolved exact ID.
- RAG mode supports semantic query and exact `digital` category only; do not claim hard price/spec filtering.
- Keep normal keyword search available. Do not add checkout, payment, order placement, production deployment, or publishing to this flow.
- The Commerce fixture snapshot is `hongbinwee/codyssey_final-mission-main` at `781e78597843859299be2bb7278e06219595e9b7`; fixture products/reviews are synthetic.

## Review Focus

- A changed or malformed fixture must produce a different stable dataset version or fail before an index run is activated. Test in Task 1 with changed fixture bytes, duplicate IDs, and invalid review-to-product links.
- A demo review must not lose its original `r-d-*` provenance when the RAG response uses the SHA-256 source key. Test in Task 1 by asserting the hash and the original ID, `source_kind`, and `source_ref` in indexed evidence metadata.
- Missing or inactive Commerce product IDs must never become purchasable cards. Test in Task 3 for exact ordered hydration and omission, and in Task 4 for partial and total catalog/index mismatch.
- Invalid category/limit, unavailable index, and timeout must return an error/retry state without falling back to keyword search. Test in Task 4 and Task 5.
- A late response for an old query must not display mismatched products or evidence, and synthetic review evidence must be labeled. Test in Task 5 and the browser flow in Task 6.

---

## File and Repository Boundaries

The RAG implementation and this plan live in the RAG worktree on branch `codex/commerce-rag-integration`. The Commerce implementation will use a separate worktree based on the pinned upstream snapshot; it must not edit `/tmp/codyssey_final_mission_upstream` in place.

**RAG repository**

- `src/toss_ads/rag/commerce_source.py` — strict fixture loader and normalization into the existing RAG source contract.
- `src/toss_ads/rag/source.py` — shared source protocol used by the indexer.
- `src/toss_ads/rag/chunker.py` — retain Commerce review provenance fields in review chunk metadata.
- `src/toss_ads/rag/config.py`, `src/toss_ads/rag/__main__.py`, `src/toss_ads/rag/api.py` — allow fixture indexing and RAG serving without an Amazon source URL while preserving the existing Amazon index command.
- `tests/test_commerce_fixture_source.py`, `tests/test_rag_commerce_index_cli.py`, `tests/test_rag_api.py` — adapter, provenance, validation, CLI, and serving-config coverage.
- `deploy/commerce-rag-demo.compose.yaml`, `deploy/commerce-rag-demo.env.example`, `docs/commerce-rag-demo.md` — isolated local database setup and repeatable indexing/search instructions.
- `.gitignore` — keep generated local passwords and demo identity files out of Git.

**Commerce repository**

- `src/contracts.ts` — typed RAG request, evidence, and search result contracts.
- `src/catalog.ts` — exact-ID active product hydration using current Commerce rows.
- `src/rag-search.ts` — request validation, RAG proxy, response validation, hydration join, and error mapping.
- `src/server.ts` — authenticated `POST /api/rag/search` route.
- `src/web/rag-search.ts`, `src/web/screens/Search.tsx`, `src/web/styles.css` — RAG mode, request state, ranked cards, and source-labeled snippets.
- `tests/unit/catalog-rag.test.ts`, `tests/unit/rag-search.test.ts`, `tests/unit/rag-search-ui.test.ts` — isolated service and UI-state tests.
- `src/rag-demo-safety.ts`, `tests/unit/rag-demo-safety.test.ts`, `playwright.rag-demo.config.ts`, `tests/rag-demo/server.ts`, `tests/rag-demo/commerce-rag-flow.spec.ts`, `package.json` — dedicated browser flow with a fail-closed isolated database preflight.
- `.gitignore` — keep local RAG demo credentials and identity files out of Git.
- `README.md` — link to the local demo setup without changing the normal Commerce setup path.

## Task 1: Normalize the pinned Commerce fixtures as a RAG source

**Files (RAG repository):**
- Create: `src/toss_ads/rag/commerce_source.py`
- Modify: `src/toss_ads/rag/source.py`
- Modify: `src/toss_ads/rag/chunker.py`
- Test: `tests/test_commerce_fixture_source.py`

**Interfaces:**
- Produces `CommerceFixtureSource.from_repository(root: Path) -> CommerceFixtureSource`, `list_categories() -> CategorySnapshot`, `iter_products(category: str, dataset_version: str) -> Iterator[dict[str, Any]]`, and `iter_reviews(category: str, dataset_version: str) -> Iterator[dict[str, Any]]`.
- `RagSource(Protocol)` in `source.py` defines those three read-only methods; both `AmazonReviewsClient` and `CommerceFixtureSource` implement it.
- Dataset version is `commerce-demo-v1:<sha256>` over canonical fixture contents, `COMMERCE_MAPPING_VERSION`, and `CHUNKER_VERSION`.

- [ ] **Step 1: Write failing fixture adapter tests**

Add tests named `test_digital_snapshot_has_expected_counts_and_stable_version`, `test_changed_fixture_changes_dataset_version`, `test_product_records_keep_exact_ids_and_exclude_variant_price_and_stock`, `test_review_records_hash_id_and_keep_demo_provenance`, and `test_invalid_or_duplicate_fixture_linkage_fails_closed`.

Assert category counts are exactly 7 products and 25 reviews for `digital`; 12 digital variants are folded into their parent product evidence; product ID `p-d-key-87` is unchanged; product evidence includes specs, option values, and effective specs (including the K87 switch terms); it contains no variant price/stock fields; review `source_id` is lowercase SHA-256 of its original `r-d-*` ID and source metadata retains `commerce_review_id`, `source_kind="SYNTHETIC"`, and `source_ref`.

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_commerce_fixture_source.py' -v`

Expected: FAIL because the fixture source and Commerce provenance mapping do not exist yet.

- [ ] **Step 3: Implement strict fixture normalization**

Read only `db/seeds/demo-catalog.json` and `db/seeds/demo-reviews.json`. Reject malformed top-level shape, duplicate product/variant/review IDs, a variant whose parent product is missing, and a review whose product is missing. Derive counts from validated fixture rows. Emit only `digital` products/reviews; combine each product's `specs`, variant `option_values`, and effective `specs + spec_overrides` under `details`, with no price, stock, or purchasable variant ID. Map review `id` to `review_key=sha256(id)`, `product_id` to `parent_asin`, `body` to `text`, and `written_at` to `timestamp`; set `source_metadata` to `commerce_review_id`, `source_kind`, and `source_ref`. Extend the review metadata allow-list only for those explicit Commerce provenance keys.

- [ ] **Step 4: Run the focused tests and confirm they pass**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_commerce_fixture_source.py' -v`

Expected: all adapter, determinism, category-scope, and provenance tests PASS.

- [ ] **Step 5: Commit the RAG adapter**

```bash
git add src/toss_ads/rag/commerce_source.py src/toss_ads/rag/source.py src/toss_ads/rag/chunker.py tests/test_commerce_fixture_source.py
git commit -m "feat: add Commerce demo fixture RAG source"
```

## Task 2: Add a fixture indexing command and isolated staging databases

**Files (RAG repository):**
- Modify: `src/toss_ads/rag/config.py`
- Modify: `src/toss_ads/rag/indexer.py`
- Modify: `src/toss_ads/rag/__main__.py`
- Modify: `src/toss_ads/rag/api.py`
- Modify: `tests/test_rag_api.py`
- Create: `tests/test_rag_commerce_index_cli.py`
- Modify: `.gitignore`
- Create: `deploy/commerce-rag-demo.compose.yaml`
- Create: `deploy/commerce-rag-demo.env.example`
- Create: `docs/commerce-rag-demo.md`

**Interfaces:**
- `Settings.from_env(require_amazon_source: bool = True) -> Settings` keeps the existing Amazon URL requirement by default. Fixture indexing calls it with `False`; FastAPI serving calls it with `False`; default Amazon `index` behavior is unchanged.
- `index_dataset(source: RagSource, store: RagStore, embedder: FastEmbedEmbeddings, settings: Settings, *, resume_run_id: str | None = None, categories: tuple[str, ...] | None = None) -> IndexSummary` accepts the shared source protocol.
- `create_index_source(args: argparse.Namespace, settings: Settings) -> RagSource` in `__main__.py` selects the fixture adapter only when `args.commerce_fixtures` is set.
- `index --commerce-fixtures <commerce-repo-root> --category digital` selects the fixture source and the existing embedding/store/index path; omitting this option retains the Amazon source.

- [ ] **Step 1: Write failing CLI/config tests**

Add tests named `test_fixture_index_does_not_require_amazon_url`, `test_fixture_cli_selects_digital_source`, `test_amazon_index_still_requires_and_uses_amazon_source`, and `test_serve_settings_do_not_require_amazon_source`.

Assert fixture mode accepts a valid `RAG_DATABASE_URL` with no `AMAZON_REVIEWS_API_BASE_URL`, rejects any fixture category except `digital` before opening a run, and uses the same embedding/chunking/store contract; default Amazon mode continues rejecting a missing Amazon URL.

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_rag_commerce_index_cli.py' -v` and `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_rag_api.py' -v`

Expected: FAIL because settings and CLI source selection are Amazon-only.

- [ ] **Step 3: Implement the source selector and config behavior**

Add an explicit `--commerce-fixtures` option to the `index` subcommand. In fixture mode, reject non-`digital` categories before creating an index run. Keep `serve` free of any requirement to configure an Amazon URL by changing FastAPI's default environment load, not by passing a fake source URL. Preserve existing positional `Settings(...)` construction and default Amazon indexing behavior.

- [ ] **Step 4: Add an isolated Compose project and operator instructions**

- Define new services/volumes for Commerce PostgreSQL 17 (`commerce` database) and the existing locally built RAG PostgreSQL image (`toss_rag` database); use distinct loopback ports `15436` and `15437`, a unique Compose project name, and `pull_policy: never` for the RAG image. Before first start, verify the project/container/volume names do not exist and ports `15436`, `15437`, `13001`, and `18002` are unbound; if any target exists, stop and choose a fresh project/port configuration. Use ignored local secret files and never fixed container/volume names. Ignore `.secrets/` and `.commerce-rag-demo.local/` in Git. Document bootstrap, Commerce migrations/base seed/demo seed, RAG index bootstrap, the Commerce app/RAG API ports `13001`/`18002`, and local `DATABASE_URL`/`RAG_API_BASE_URL` configuration. Record the new Commerce Compose service's system identifier in `.commerce-rag-demo.local/identity.env` for the browser preflight. The instructions must never invoke `down -v` or reference `commerce_demo_verify`.

- [ ] **Step 5: Run RAG CLI/config and existing source-scope tests**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_rag_commerce_index_cli.py' -v`, `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_rag_indexer_scope.py' -v`, and `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_rag_api.py' -v`

Expected: fixture CLI tests and prior category-scope tests PASS; no live database is used.

- [ ] **Step 6: Commit the staging setup**

```bash
git add .gitignore src/toss_ads/rag/config.py src/toss_ads/rag/indexer.py src/toss_ads/rag/__main__.py src/toss_ads/rag/api.py tests/test_rag_api.py tests/test_rag_commerce_index_cli.py deploy/commerce-rag-demo.compose.yaml deploy/commerce-rag-demo.env.example docs/commerce-rag-demo.md
git commit -m "feat: add isolated Commerce RAG demo index setup"
```

## Task 3: Hydrate ranked IDs from exact Commerce catalog rows

**Files (Commerce worktree):**
- Modify: `src/catalog.ts`
- Create: `tests/unit/catalog-rag.test.ts`

**Interfaces:**
- Produces `getProductSummariesByIds(productIds: readonly string[], db: Pick<typeof sql, "unsafe"> = sql): Promise<ProductSummary[]>`.
- Deduplicates repeated IDs by first occurrence, rejects more than 20 distinct IDs, and returns active product summaries in input order with active variants, current Commerce price/stock, rating summary, image, and availability.

- [ ] **Step 1: Write failing hydrator tests**

Add tests named `test_hydration_preserves_requested_rank_order_and_commerce_state`, `test_hydration_omits_missing_and_inactive_ids_without_substitution`, and `test_empty_and_duplicate_id_inputs_are_bounded`.

Use a fake `unsafe` DB to assert exact-ID predicates, input rank order despite database row order, current Commerce prices/stock, and omission of inactive/missing IDs. Assert no broad semantic/title lookup is called.

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `npm ci && node --test tests/unit/catalog-rag.test.ts`

Expected: FAIL because exact-ID hydration is not implemented.

- [ ] **Step 3: Implement `getProductSummariesByIds`**

Reuse the existing `toVariant`, `productAvailability`, and summary construction rules in `src/catalog.ts`. Query only requested active product IDs and active variants; query ratings for those IDs. Reassemble rows in the exact caller order and skip IDs without an active exact catalog row.

- [ ] **Step 4: Run catalog hydration and existing catalog tests**

Run: `node --test tests/unit/catalog-rag.test.ts tests/unit/catalog.test.ts`

Expected: both test files PASS.

- [ ] **Step 5: Commit Commerce catalog work**

```bash
git add src/catalog.ts tests/unit/catalog-rag.test.ts
git commit -m "feat: hydrate RAG hits by exact Commerce product ID"
```

## Task 4: Add the authenticated RAG search proxy

**Files (Commerce worktree):**
- Modify: `src/contracts.ts`
- Create: `src/rag-search.ts`
- Modify: `src/server.ts`
- Create: `tests/unit/rag-search.test.ts`
- Modify: `tests/unit/server-rag-search.test.ts`

**Interfaces:**
- `RagSearchRequest = { original_question: string; query: string; category?: "digital"; top_k: number }`.
- `RagSearchResult = { dataset_version: string; items: { product: ProductSummary; evidence: RagEvidence[]; rrf_score: number }[]; unverified_conditions: string[]; catalog_mismatch_count: number }`.
- `RagEvidence` retains `source_type`, hashed `source_id`, `source_field`, `evidence_text`, `source_metadata`, and `rrf_rank`.
- `RagSearchDeps = { baseUrl: string | undefined; fetchRag: typeof fetch; hydrate: typeof getProductSummariesByIds }`.
- `searchRag(input: RagSearchRequest, deps: RagSearchDeps) -> Promise<ToolResult<RagSearchResult>>` accepts injected dependencies for deterministic tests.

- [ ] **Step 1: Write failing proxy and route tests**

Add tests named `test_rejects_invalid_query_category_and_top_k`, `test_preserves_rag_rank_and_evidence_with_exact_catalog_rows`, `test_partial_and_total_catalog_mismatch_never_substitute`, `test_timeout_or_upstream_error_returns_retryable_failure`, `test_no_results_remains_no_results`, and `test_route_requires_a_valid_commerce_session`.

Assert `top_k` is 1–20, category is absent or exactly `digital`, no price/spec filters are forwarded, RAG item order and evidence order survive hydration, partial mismatch count is returned, total mismatch becomes `CATALOG_INDEX_MISMATCH`, timeout/index errors become error envelopes, and an unauthenticated browser cannot invoke the RAG dependency.

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `node --test tests/unit/rag-search.test.ts tests/unit/server-rag-search.test.ts`

Expected: FAIL because the RAG contract, proxy, and endpoint do not exist.

- [ ] **Step 3: Implement typed request validation and proxy**

Add strict body validation, server-only `RAG_API_BASE_URL`, bounded request timeout, and validation of the upstream RAG response before mapping. Convert RAG status/errors to the Commerce API envelope. Hydrate returned IDs once, join by exact `product_id`, preserve RAG rank/evidence order, report partial mismatch, and fail if no item can be hydrated. Do not silently call `/api/products` on any failure.

- [ ] **Step 4: Wire `POST /api/rag/search` behind the existing session gate**

In `src/server.ts`, add the route only after `reqCtx(req)` succeeds. Return errors through the existing JSON envelope; keep `GET /api/products` unchanged. Ensure the RAG base URL and database credentials never enter response data or logs.

- [ ] **Step 5: Run proxy, route, and existing product API tests**

Run: `node --test tests/unit/rag-search.test.ts tests/unit/server-rag-search.test.ts tests/unit/catalog.test.ts`

Expected: all selected tests PASS, including unauthenticated 401 and exact catalog mismatch behavior.

- [ ] **Step 6: Commit Commerce proxy work**

```bash
git add src/contracts.ts src/rag-search.ts src/server.ts tests/unit/rag-search.test.ts tests/unit/server-rag-search.test.ts
git commit -m "feat: add authenticated Commerce RAG search proxy"
```

## Task 5: Add RAG mode and source-grounded evidence to Commerce search

**Files (Commerce worktree):**
- Create: `src/web/rag-search.ts`
- Modify: `src/web/screens/Search.tsx`
- Modify: `src/web/styles.css`
- Create: `tests/unit/rag-search-ui.test.ts`

**Interfaces:**
- `buildRagSearchRequest(query: string, category?: "digital"): RagSearchRequest` sends the same query as `original_question` and `query`, with `top_k: 20`.
- `orderedRagItems(result: RagSearchResult): RagSearchResult["items"]` returns items in RAG rank order without local sorting.
- `ragEvidenceLabel(evidence: RagEvidence): string` returns `상품 설명`, `리뷰`, or `리뷰 · 데모 데이터` from the source type and Commerce `source_kind`.
- `submitRagSearch(input: RagSearchRequest, post: RagPost): Promise<ApiResult<RagSearchResult>>` calls only `POST /api/rag/search`; it does not call or fall back to `GET /api/products`.
- RAG results stay in server-provided order; the component associates each result/evidence collection with the submitted query generation.

- [ ] **Step 1: Write failing RAG UI helper tests**

Add tests named `test_request_sends_query_and_exact_digital_category`, `test_rag_items_keep_server_order`, `test_error_retries_rag_without_keyword_fallback`, `test_old_query_response_is_not_renderable`, and `test_review_evidence_exposes_synthetic_provenance`.

Assert request limit 20, optional exact category only, `orderedRagItems` preserves the provided IDs even when Commerce prices/ratings differ, an API error calls only the RAG endpoint, stale response ownership is rejected, and `source_type="review"` with `source_kind="SYNTHETIC"` produces `리뷰 · 데모 데이터`.

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `node --test tests/unit/rag-search-ui.test.ts`

Expected: FAIL because the RAG UI request/state helpers do not exist.

- [ ] **Step 3: Implement RAG search request/state helpers**

Add typed request construction and a query-generation guard; map `ok`, `no_results`, and error states without changing the normal search contract.

- [ ] **Step 4: Add a RAG mode control and render results/evidence**

Add accessible `키워드 검색` and `RAG 검색` mode controls. Keep current autocomplete, filtering, sorting, and pagination for keyword mode. In RAG mode send one request per submit, offer only the exact `digital` category, hide price/spec sort/filter controls, and never fallback to keyword search. Render Commerce `ProductSummary` cards with a `데모 데이터` label and up to three returned evidence snippets, source type, and synthetic review label. Route card clicks through the existing `onOpenProduct(product_id)` path.

- [ ] **Step 5: Run UI helper tests, typecheck, and build**

Run: `node --test tests/unit/rag-search-ui.test.ts tests/unit/search-loader.test.ts && npm run check && npm run build`

Expected: selected unit tests, TypeScript check, and bundle build PASS; normal keyword search tests remain green.

- [ ] **Step 6: Commit Commerce search UI work**

```bash
git add src/web/rag-search.ts src/web/screens/Search.tsx src/web/styles.css tests/unit/rag-search-ui.test.ts
git commit -m "feat: add RAG mode to Commerce search"
```

## Task 6: Verify the isolated browser purchase path and document handoff

**Files (Commerce worktree):**
- Create: `playwright.rag-demo.config.ts`
- Create: `tests/rag-demo/commerce-rag-flow.spec.ts`
- Create: `tests/rag-demo/server.ts`
- Create: `src/rag-demo-safety.ts`
- Create: `tests/unit/rag-demo-safety.test.ts`
- Modify: `.gitignore`
- Modify: `package.json`
- Modify: `README.md`
- Modify: `docs/commerce-rag-demo.md` (RAG repository)

**Interfaces:**
- `assertRagDemoTarget(env, observedIdentity) -> { ok: true } | { ok: false; reason: string }` accepts only Commerce at `127.0.0.1:15436/commerce`, RAG at `127.0.0.1:18002`, the explicit demo marker, and the Commerce database system identifier recorded from the new Compose service.
- `npm run test:rag-demo` runs only the new Commerce RAG demo Playwright config/spec; its server wrapper verifies the live DB identity before listening.
- The flow uses the local access code, searches `저소음 적축 K87 키보드 후기` in RAG mode (the review-intent word requests review evidence), opens exact product `p-d-key-87`, selects an available `v-d-key-87-*` variant, adds it to cart, and asserts the same product/variant IDs and Commerce price in `GET /api/cart`.

- [ ] **Step 1: Write failing isolated-target guard tests**

Add tests named `test_accepts_only_the_recorded_loopback_demo_instance`, `test_rejects_wrong_host_port_or_database`, `test_rejects_missing_marker_or_rag_url`, and `test_rejects_database_system_identifier_mismatch`. The browser flow must use a distinct new Compose volume and must not call the repository's guarded general-purpose `verify`, integration, or legacy E2E wrappers.

- [ ] **Step 2: Run the focused guard tests and confirm they fail**

Run: `node --test tests/unit/rag-demo-safety.test.ts`

Expected: FAIL because the demo target guard is not implemented.

- [ ] **Step 3: Implement the isolated server wrapper and browser flow**

Implement `assertRagDemoTarget` and the server wrapper. Before `start()` listens, verify the exact loopback Commerce URL, `current_database() = 'commerce'`, and system identifier loaded from `.commerce-rag-demo.local/identity.env`; reject before serving on any mismatch. Configure the RAG URL as loopback port `18002`. Add a dedicated package script invoking only `playwright.rag-demo.config.ts`. Assert the RAG result is `p-d-key-87` and includes both product and synthetic review evidence; details show Commerce-owned image/options/current price; variant selection succeeds; and the cart contains the selected `p-d-key-87` / `v-d-key-87-*` pair. This runner covers only the new isolated flow and does not claim the general E2E suite is ready or passing. Stop at cart verification; do not enter checkout.

- [ ] **Step 4: Run repository checks and the isolated end-to-end flow**

Run Commerce checks: `npm run check && npm run build && node --test tests/unit/catalog-rag.test.ts tests/unit/rag-search.test.ts tests/unit/server-rag-search.test.ts tests/unit/rag-search-ui.test.ts tests/unit/rag-demo-safety.test.ts`.

Then, only after verifying the new Compose project/volume names and loopback ports are unused, start the isolated services, migrate/seed only the new Commerce DB (`npm run db:migrate -- --phase=6`, `npm run db:seed -- --phase=4`, `npm run db:seed:demo`), bootstrap/index the new RAG DB, start the local APIs, and run `npm run test:rag-demo`.

Expected: unit/type/build checks PASS; the browser reaches cart with exact `p-d-key-87` and the selected `v-d-key-87-*`; the RAG result contains product and review evidence; staging RAG health reports only `digital`, 7 products, and 25 reviews. Record before/after current RAG `/healthz` dataset version/categories and confirm they are identical. Do not print credentials.

- [ ] **Step 5: Document local start/stop and verification commands**

Document loopback URLs, local secret-file setup, unique Compose project and volume names, seed order, index command, app startup, the tested query, and how to stop only the newly created containers without deleting volumes. Keep `commerce_demo_verify` and all protected DBs out of commands and examples.

- [ ] **Step 6: Commit the browser-flow handoff**

```bash
git add .gitignore src/rag-demo-safety.ts tests/unit/rag-demo-safety.test.ts playwright.rag-demo.config.ts tests/rag-demo/server.ts tests/rag-demo/commerce-rag-flow.spec.ts package.json README.md
git commit -m "test: verify Commerce RAG cart flow in isolation"
```

From the RAG worktree, commit the final shared runbook update separately:

```bash
git add docs/commerce-rag-demo.md
git commit -m "docs: document isolated Commerce RAG demo flow"
```

## Self-Review

- **Spec coverage:** Fixture mapping/version/counts and provenance are in Task 1; separate index/config/services are in Task 2; exact catalog hydration is in Task 3; authenticated proxy and mismatch/error handling are in Task 4; RAG UI/evidence/no-fallback are in Task 5; isolated browser path and before/after current-index check are in Task 6.
- **Step scan:** Each task has named tests, focused commands, explicit signatures, and a commit. No feature step depends on unspecified price/spec filtering or generated review summaries.
- **Type consistency:** Task 3 returns `ProductSummary[]`; Task 4 joins those rows into the typed `RagSearchResult`; Task 5 consumes that result and sends the Task 4 request; Task 6 exercises the same IDs through existing Commerce detail/cart APIs.
- **Review focus:** All five failure classes are pinned by the tests in Tasks 1, 3, 4, 5, and 6.
- **Proportion:** The plan is scoped to one coupled cross-repository feature and does not prescribe unrelated RAG, Commerce, checkout, or production work.

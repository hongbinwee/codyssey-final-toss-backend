# Commerce Frontend + RAG Full-Flow Integration Design

**Status:** Design approved in conversation; written-spec review pending. No feature code or database has been changed.

## Goal

Use the Commerce app from `hongbinwee/codyssey_final-mission-main` as a browser UI for the existing RAG implementation, and verify a complete local shopping path: natural-language search, RAG evidence, product detail, variant selection, and cart add. Keep the existing RAG files and active index intact.

## Existing system boundaries

- The Python RAG backend exposes `POST /v1/rag/search` and reads one active index run per `RAG_DATABASE_URL`. Its current local active run contains `Appliances` and `earphones`.
- The Commerce TypeScript app has its own catalog database and search route (`GET /api/products`). Its product detail, reviews, variants, images, and cart use Commerce product IDs.
- The current RAG earphone result IDs (for example, `earphone-test-024`) do not match Commerce demo IDs (for example, `p-d-ear-lite`). Using the current active index for the full shopping path would not provide a safe product-to-cart identity mapping.
- The complete Commerce demo fixture contains 25 products, 55 variants, and 80 reviews. Its `p-d-*`, `v-d-*`, and `r-d-*` IDs are stable fixture IDs. The records and product images are synthetic. The RAG test index is limited to the `digital` category to stay within the user's previously selected appliance/electronics scope.

## Chosen architecture

Use the existing RAG code with a **separate Commerce-demo index and database**, and run the Commerce app against a **separate, newly created local demo database and volume**. The browser will use a new RAG mode in the existing Commerce search screen. The Commerce server will proxy RAG requests and hydrate results from the Commerce catalog by exact product ID.

The current RAG database, active index, API process, Commerce databases, and existing containers are not targets for writes, resets, shutdown, or deletion. The staging services use their own database volumes and unused loopback ports. The Commerce app's database is named `commerce` only inside its newly created isolated PostgreSQL instance so the repository's demo-seed guard can validate it. Do not use the existing `commerce_demo_verify` database or any existing volume.

### Commerce fixture index

Add an additive source adapter/index command to the Python RAG backend. It reads a pinned snapshot of the Commerce repository's `db/seeds/demo-catalog.json` and `db/seeds/demo-reviews.json`; it does not query or mutate the Commerce database. A stable dataset version is derived from the fixture contents and mapping/chunker version.

Mapping rules:

| Commerce field | RAG field/use |
| --- | --- |
| product `id` | `product_id` / `parent_asin`; keep the exact `p-d-*` value |
| product `name`, `brand`, `category`, `description` | `title`, `brand`, the exact RAG category and `main_category`, and `description` |
| product `specs`, variant option values, and effective variant specs | Product `details` evidence so semantic search can find terms such as `저소음 적축` and `그레이` |
| variant price and stock | Excluded from semantic evidence; Commerce DB remains authoritative for current price and inventory |
| review `id` | Stable SHA-256 review source key required by the RAG response contract; preserve the original `r-d-*` ID and `source_kind` / `source_ref` in safe source metadata |
| review `product_id`, `body`, `rating`, `written_at` | RAG product linkage and review evidence fields |

Index only the `digital` fixture category. That subset contains 7 products, 12 variants, and 25 reviews. Do not index `beauty`, `fashion`, `living`, or `food`. The new Commerce demo DB may contain the complete 25/55/80 fixture so the existing store UI can operate, while RAG mode exposes only its supported `digital` category. Variant data is searchable as product evidence but variants are not independent purchasable products. The Commerce DB supplies all displayed price, stock, variant, review-list, and image data. Images remain normal static web assets and are not image-embedded by RAG.

The staging RAG process uses the same `/v1/rag/search` contract and embedding/chunking implementation, with a separate `RAG_DATABASE_URL` and local port. It has one active Commerce-demo run. This does not activate or replace a run in the current RAG database.

### Request and result path

1. The user selects RAG mode in the Commerce search screen and submits a Korean query, optional exact `digital` category, and a result limit no greater than the RAG contract's maximum of 20.
2. The browser calls a new authenticated Commerce endpoint, `POST /api/rag/search`; it does not call the RAG host directly.
3. The Commerce server validates the request, forwards it to the staging RAG API using a server-only `RAG_API_BASE_URL`, and converts transport or RAG errors into the app's existing API envelope.
4. For each RAG `product_id`, the Commerce server looks up an active product with that exact ID and builds the existing `ProductSummary` from Commerce rows. It preserves RAG rank and evidence order. It never substitutes a similar or unrelated product. Missing or inactive catalog IDs are excluded and reported as a catalog/index mismatch; if none can be hydrated, the UI shows an actionable error state.
5. The UI displays the hydrated product card and the RAG evidence snippets, including whether the source is product text or a review and whether it is synthetic. The card opens the existing product detail route.
6. The existing detail/review APIs supply the current demo image, specifications, reviews, option prices, and stock. Existing variant selection and cart APIs perform the cart operation against the isolated Commerce demo database.

### Search behavior and limits

- Add a RAG mode to the existing search view; retain normal keyword search as a separate mode.
- RAG mode supports semantic query and exact `digital` category filtering. It does not claim hard enforcement of natural-language price or specification requirements: the current RAG request contract treats those conditions as unverified. Product detail and Commerce DB remain the source of truth for option availability, price, and stock.
- Preserve RAG result ordering. Do not sort RAG results by rating or price after retrieval.
- Show an explicit “데모 데이터” provenance label for these synthetic products and review evidence.
- The existing full review list remains available from the Commerce product detail/review flow. RAG evidence is shown as retrieved snippets, not as a generated factual summary.

## Isolation and safety

- Create a uniquely named local Compose project and new volumes for the Commerce demo database and the RAG staging database. Bind them only to unused loopback ports. Do not reuse, stop, reset, seed, migrate, or delete the existing PostgreSQL service on port 5432 or the existing RAG API on port 8002.
- Run the Commerce app on an unused loopback port. Keep credentials in ignored local environment/secret files and never print them or commit them.
- Do not run the Commerce demo seed against any existing database. Use only the new Commerce database/volume.
- Browser-to-RAG traffic is proxied through the authenticated Commerce server; no RAG database URL or secret is exposed to the browser.
- End-to-end cart writes are limited to the new local demo database. The requested flow stops at cart verification; checkout, payment, order creation, production deployment, and push are outside scope.

## Error behavior

- A RAG timeout, unavailable index, invalid category, or failed search produces an error/retry state in RAG mode. It does not silently fall back to normal keyword search.
- A product ID missing or inactive in the Commerce catalog is never shown as purchasable. Report the mismatch; show hydrated results only when exact matches remain.
- Commerce price, inventory, and variant state are read from the Commerce database at display/action time, not trusted from RAG metadata.

## Scope exclusions

- Modifying or reindexing the current active `Appliances + earphones` RAG dataset.
- Replacing the Commerce app's normal keyword search.
- Importing real external Commerce data or setting up ongoing synchronization.
- Image captioning, OCR, or image embeddings.
- Deterministic price/spec filtering inside RAG, checkout, payment, order placement, deployment, or publishing.

## Acceptance criteria

1. A new isolated RAG index reports 7 products, 25 reviews, and only the `digital` category. It excludes the other four categories. Every indexed review links to an indexed product; product IDs remain `p-d-*` and review provenance remains inspectable.
2. A query for the low-noise red-switch K87 keyboard in `digital` returns `p-d-key-87` with product/review evidence. The result can be hydrated from the isolated Commerce catalog without ID substitutions.
3. In the browser, a user can enter RAG mode, submit the query, see the matching product image and current Commerce price/options, open the product detail, select a variant, and verify that variant in the cart.
4. RAG review evidence is displayed with its source type and synthetic-data label. Existing detail/review pages and normal search continue to work.
5. A before/after read of the current RAG `/healthz` reports the same active dataset version and categories. No writes target the current active RAG database or any existing Commerce database.
6. Type/unit checks and the relevant UI/API tests pass. The end-to-end cart check uses only the newly created Commerce demo database and local app instance.

## Source snapshot

- Commerce source: `hongbinwee/codyssey_final-mission-main`, `main` snapshot `781e78597843859299be2bb7278e06219595e9b7`.
- RAG source: workspace branch `codex/rag-contracts-validation` at the start of this design task; implementation is intended for a separate `codex/commerce-rag-integration` worktree.

# RAG recommendation quality implementation

User approved the in-chat design with “이렇게 만들어줘”. Implement in the existing RAG flow.

## Constraints
- Backend repository only; feature/rag-recommendation-quality, based on origin/main.
- origin/main currently contains only README. Bring the running service baseline into this branch, preserve the unrelated dirty checkout.
- PostgreSQL 5432 only. Preserve source files, source rows, original chunks, profiles and IDs.
- Shopping Brain owns category routing; optional structured product_type is a backward compatible addition.
- Implement locally; publishing/merging is separate from implementation. No new listening ports.
- Do not add or run automated tests without an explicit request. Use compilation and static inspection; reuse evaluation only if authorized.

## Tasks
- [x] Request/config: profile and product_type, strict stock flag, configurable profile/schema allowlists and independent Commerce reader.
- [x] Type registry: extensible aliases, main-item matching, unknown type and ambiguous intent fail safely.
- [x] Retrieval: diverse per-product candidates, product ranks, lexical reranking, review-only channel contribution, no forced irrelevant results.
- [x] Commerce hydration: read-only live variant lookup, same-variant budget/stock enforcement before top_k, snapshot/live labels.
- [x] Evidence: real review preference, synthetic labels, no tiny fragments/administrative metadata; chunker v3 keeps source offsets and token budgets.
- [x] API and integration docs: configured profiles rather than beauty-only pin; preserve legacy catalog endpoint pin.
- [x] Compile and inspect code, document deployment state and limitations.

## Intended acceptance
Backpack, fan and shirt requests must not return other product types. Price/stock conditions must be checked on the same variant. Review-only matches must survive fusion. Unsupported items may return no_results/low_relevance. Chunk provenance must remain valid. Quantitative quality claims require a new evaluation and human-reviewed held-out labels.

## Implementation record
- Main contains only README; seeded this branch with the running RAG baseline, not unrelated dirty work.
- Source schema/public mapping is configured on the server; Commerce query uses a read-only transaction.
- Type filtering and same-variant price/stock eligibility precede candidate search to avoid missing eligible items beyond top_k.
- Chunker v3 is implemented but existing chunks are preserved and not re-embedded.
- Validation: Python compileall, import build using existing container dependencies, generated Pydantic request schema, and git whitespace inspection.
- No automated tests, retrieval evaluation, deployment, commits, pushes or merges performed.
- Final review: author static review, no delegated agent. Quality gains remain unmeasured.

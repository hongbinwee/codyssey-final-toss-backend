# v4 모의 시연용 데이터 QA

- Products: 180; Skincare 100 / Makeup 80; Brands: 102
- Simulated variants: 180; synthetic reviews: 4737; text duplicates: 0
- Five-section descriptions: 180; char range: 606–700; ≥500 chars: 180
- Manufacturer product-level fact verified: 4; NOT VERIFIED: 176. **Never present as 180 officially verified.**
- Observed review mean (source subset): 4.7904; synthetic review mean: 4.7862. 5-star selection bias may dominate.
- Actual original review text in ZIP: 0; observed review aspect aggregates only; source review count distinct from synthetic count.
- No live DB import, no actual RAG/Commerce E2E.
- Synthetic reviews are hypothetical, intentionally not verified consumer experiences.
- Demo historical price and inventory are NOT real shop offer or SKU.
- Long unverified descriptions deliberately state unknown ingredients, options, manufacturer instructions rather than filling with imaginary details. This limits their marketing usefulness.

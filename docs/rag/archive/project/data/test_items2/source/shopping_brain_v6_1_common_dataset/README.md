# Shopping Brain V6.1 — Review Language Refinement (CANDIDATE)

Version: v6.1-review-refined. Scope: review naturalness/variety/rating alignment.
Products: 1,500; variants: 1,917; reviews: 46,100.
Original review IDs, ratings, dates, provenance, product/variant IDs are preserved.
Source-collected (REAL) review texts are preserved exactly.
Some generated (SYNTHETIC) review texts were revised using deterministic, product-family/rating-aware rules.
`source_kind` and `source_ref` remain visible to internal pipelines, and must not be relabeled or represented as verified buyers.
Quality claims in these illustrative reviews are NOT proof of actual purchases or product performance.

## Important limits
This is a candidate for internal development, NOT a fully verified final dataset.
No independent human/LLM semantic review of all 46,100 rows, marketplace source-fact refresh, image accessibility, rights clearance or live model evaluation was performed.
Product catalog/taxonomy, variant legitimacy and some review-to-variant mappings inherited from V6 may require correction.
The category/aspect keyword coverage fields are heuristics, NOT independent statements of authenticity.

## Release integrity
products.json, variants.json, reviews.json share the same IDs; no synthetic items were reclassified as REAL.
See the separate QA package (not part of this canonical four-file ZIP) for detailed diffs and validators.

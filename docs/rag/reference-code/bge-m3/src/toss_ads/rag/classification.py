"""Deterministic category/type mismatch checks for source products."""

from __future__ import annotations

import re
from typing import Any

from .types import QuarantinedProduct


CATEGORY_POLICY_VERSION = "source-category-type-v1"


def _normalize(value: str) -> str:
    words = re.sub(r"[^a-z0-9]+", " ", value.casefold()).split()
    return " ".join(word for word in words if word != "and")


_DOMAIN_ALIASES = {
    "beauty": "beauty",
    "skin care": "beauty",
    "skincare": "beauty",
    "make up": "beauty",
    "makeup": "beauty",
    "electronics": "electronics",
    "books": "books",
}

_CATEGORY_DOMAINS = {"beauty": "beauty"}


def _domain(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return _DOMAIN_ALIASES.get(_normalize(value))


def _book_detail_signals(details: Any) -> list[str]:
    if not isinstance(details, dict):
        return []
    signals: list[str] = []
    for key, value in details.items():
        if not isinstance(key, str) or value is None or not str(value).strip():
            continue
        normalized_key = _normalize(key)
        if normalized_key in {"isbn 10", "isbn10", "isbn 13", "isbn13"}:
            isbn = re.sub(r"[^0-9xX]", "", str(value))
            if (len(isbn) == 10 and re.fullmatch(r"[0-9]{9}[0-9xX]", isbn)) or (
                len(isbn) == 13 and isbn.isdigit()
            ):
                signals.append(f"details:{key}")
        elif normalized_key in {"paperback", "hardcover", "mass market paperback"}:
            signals.append(f"details:{key}")
        elif _normalize(str(value)) in {"paperback", "hardcover", "mass market paperback"}:
            signals.append(f"details:{key}:book_format")
    return signals


def classify_product(
    category: str, dataset_version: str, product: dict[str, Any]
) -> QuarantinedProduct | None:
    """Return an audit record for high-confidence cross-domain mismatches."""
    expected_domain = _CATEGORY_DOMAINS.get(category)
    if expected_domain is None:
        return None

    categories = product.get("categories")
    category_labels = tuple(
        value[:300]
        for value in categories[:30]
        if isinstance(value, str) and value.strip()
    ) if isinstance(categories, list) else ()
    main_category = product.get("main_category")
    main_category = main_category[:300] if isinstance(main_category, str) else None

    signals: list[str] = []
    mismatch = False
    observed_main_domain = _domain(main_category)
    if observed_main_domain is not None and observed_main_domain != expected_domain:
        mismatch = True
        signals.append(f"main_category:{main_category}")

    top_category = category_labels[0] if category_labels else None
    observed_category_domain = _domain(top_category)
    if observed_category_domain is not None and observed_category_domain != expected_domain:
        mismatch = True
        signals.append(f"categories[0]:{top_category}")

    if expected_domain != "books":
        isbn_signals = _book_detail_signals(product.get("details"))
        if isbn_signals:
            mismatch = True
            signals.extend(isbn_signals)

    if not mismatch:
        return None

    title = product.get("title")
    return QuarantinedProduct(
        dataset_version=dataset_version,
        category=category,
        product_id=str(product.get("product_id", "")),
        reason_code="product_type_mismatch",
        policy_version=CATEGORY_POLICY_VERSION,
        product_title=title[:1000] if isinstance(title, str) else None,
        main_category=main_category,
        categories=category_labels,
        type_signals=tuple(signals),
    )

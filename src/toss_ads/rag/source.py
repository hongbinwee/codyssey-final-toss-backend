"""Bounded, read-only and version-consistent access to the source API."""

from __future__ import annotations

import json
import math
import random
import re
import time
from collections import Counter
from collections.abc import Iterator, MutableMapping
from typing import Any
from urllib.parse import quote, urlsplit

import httpx

from .types import CategorySnapshot
from .privacy import redact_explicit_pii


class SourceError(RuntimeError):
    """Safe source API failure code; never includes response text."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _reject_json_constant(_value: str) -> None:
    raise ValueError("non_finite_number")


_PRIVATE_IDENTITY_KEYS = {
    "user_id",
    "user_email",
    "email_address",
    "phone_number",
    "user_name",
    "reviewer_id",
    "reviewer_name",
    "customer_name",
    "customer_email",
    "customer_phone",
    "author_id",
}


def without_user_ids(
    value: Any, counts: MutableMapping[str, int] | None = None
) -> Any:
    """Remove explicit identity fields and redact explicit PII in source strings."""
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            normalized_key = str(key).casefold().replace("-", "_")
            if normalized_key in _PRIVATE_IDENTITY_KEYS:
                if counts is not None:
                    counts["private_fields_removed"] = counts.get("private_fields_removed", 0) + 1
                continue
            clean[key] = without_user_ids(item, counts)
        return clean
    if isinstance(value, list):
        return [without_user_ids(item, counts) for item in value]
    if isinstance(value, str):
        return redact_explicit_pii(value, counts)
    return value


class AmazonReviewsClient:
    TRANSIENT_STATUSES = {429, 502, 503, 504}

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 20.0,
        retries: int = 2,
        max_response_bytes: int = 10 * 1024 * 1024,
    ):
        try:
            parsed = urlsplit(base_url)
            valid = (
                parsed.scheme in {"http", "https"}
                and bool(parsed.hostname)
                and parsed.username is None
                and parsed.password is None
                and not parsed.query
                and not parsed.fragment
                and math.isfinite(timeout)
                and timeout > 0
                and type(retries) is int
                and 0 <= retries <= 5
                and type(max_response_bytes) is int
                and max_response_bytes > 0
            )
            parsed.port
        except (TypeError, ValueError):
            valid = False
        if not valid:
            raise SourceError("source_invalid_input")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.max_response_bytes = max_response_bytes
        self.privacy_redaction_counts: Counter[str] = Counter()
        self.client = httpx.Client(
            timeout=httpx.Timeout(timeout),
            follow_redirects=False,
            headers={"Accept": "application/json"},
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "AmazonReviewsClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _get(self, path: str, query: dict[str, Any] | None = None) -> Any:
        url = self.base_url + path
        for attempt in range(self.retries + 1):
            retry_delay = 0.0
            try:
                with self.client.stream("GET", url, params=query) as response:
                    if response.status_code in self.TRANSIENT_STATUSES:
                        if attempt == self.retries:
                            raise SourceError("source_http_error")
                        retry_after = response.headers.get("Retry-After", "")
                        try:
                            retry_delay = min(4.0, max(0.0, float(retry_after)))
                        except ValueError:
                            retry_delay = min(0.25 * (2**attempt), 2.0)
                        retry_delay += random.uniform(0.0, 0.1)
                    elif response.status_code != 200:
                        raise SourceError("source_http_error")
                    else:
                        content_length = response.headers.get("Content-Length")
                        if content_length is not None:
                            try:
                                if int(content_length) > self.max_response_bytes:
                                    raise SourceError("source_response_too_large")
                            except ValueError:
                                raise SourceError("source_invalid_response") from None
                        body = bytearray()
                        for part in response.iter_bytes():
                            body.extend(part)
                            if len(body) > self.max_response_bytes:
                                raise SourceError("source_response_too_large")
                        try:
                            return json.loads(body, parse_constant=_reject_json_constant)
                        except (ValueError, UnicodeError):
                            raise SourceError("source_invalid_response") from None
            except SourceError:
                raise
            except (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError):
                if attempt == self.retries:
                    raise SourceError("source_http_error") from None
                retry_delay = min(0.25 * (2**attempt), 2.0) + random.uniform(0.0, 0.1)
            if retry_delay:
                time.sleep(retry_delay)
        raise SourceError("source_http_error")

    def _page(
        self,
        path: str,
        query: dict[str, Any] | None = None,
        *,
        expected_version: str | None = None,
        expected_total: int | None = None,
    ) -> dict[str, Any]:
        result = self._get(path, query)
        if not isinstance(result, dict):
            raise SourceError("source_invalid_response")
        version = result.get("dataset_version")
        if not isinstance(version, str) or not version.strip():
            raise SourceError("source_invalid_response")
        if expected_version is not None and version != expected_version:
            raise SourceError("source_version_changed")
        if not isinstance(result.get("items"), list) or any(
            not isinstance(item, dict) for item in result["items"]
        ):
            raise SourceError("source_invalid_response")
        if any(type(result.get(key)) is not int or result[key] < 0 for key in ("total", "offset", "limit")):
            raise SourceError("source_invalid_response")
        if expected_total is not None and result["total"] != expected_total:
            raise SourceError("source_invalid_response")
        if query is None:
            valid = result["offset"] == 0 and result["limit"] == result["total"]
        else:
            valid = (
                result["offset"] == query["offset"]
                and result["limit"] == query["limit"]
                and 1 <= result["limit"] <= 200
            )
        expected_items = min(result["limit"], max(0, result["total"] - result["offset"]))
        if (
            not valid
            or result["offset"] > result["total"]
            or len(result["items"]) != expected_items
        ):
            raise SourceError("source_invalid_response")
        return without_user_ids(result, self.privacy_redaction_counts)

    def list_categories(self) -> CategorySnapshot:
        page = self._page("/v1/categories")
        seen: set[str] = set()
        for category in page["items"]:
            name = category.get("category")
            if (
                not isinstance(name, str)
                or not name.strip()
                or name in seen
                or type(category.get("product_count")) is not int
                or category["product_count"] < 0
                or type(category.get("review_count")) is not int
                or category["review_count"] < 0
            ):
                raise SourceError("source_invalid_response")
            seen.add(name)
        return CategorySnapshot(page["dataset_version"], tuple(page["items"]))

    def _iter_pages(
        self,
        path: str,
        *,
        dataset_version: str,
        extra_query: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        offset = 0
        total: int | None = None
        while total is None or offset < total:
            query = {**(extra_query or {}), "limit": 200, "offset": offset}
            page = self._page(
                path,
                query,
                expected_version=dataset_version,
                expected_total=total,
            )
            total = page["total"]
            yield from page["items"]
            offset += len(page["items"])
            if not page["items"] and offset < total:
                raise SourceError("source_invalid_response")

    def iter_products(self, category: str, dataset_version: str) -> Iterator[dict[str, Any]]:
        if not isinstance(category, str) or not category.strip():
            raise SourceError("source_invalid_input")
        path = "/v1/categories/" + quote(category, safe="") + "/products"
        seen: set[str] = set()
        for product in self._iter_pages(path, dataset_version=dataset_version):
            product_id = product.get("parent_asin")
            if not isinstance(product_id, str) or not product_id.strip() or product_id in seen:
                raise SourceError("source_invalid_response")
            seen.add(product_id)
            yield product

    def iter_reviews(self, category: str, dataset_version: str) -> Iterator[dict[str, Any]]:
        if not isinstance(category, str) or not category.strip():
            raise SourceError("source_invalid_input")
        path = "/v1/categories/" + quote(category, safe="") + "/reviews"
        seen: set[str] = set()
        for review in self._iter_pages(path, dataset_version=dataset_version):
            review_key = review.get("review_key")
            parent_asin = review.get("parent_asin")
            if (
                not isinstance(review_key, str)
                or not re.fullmatch(r"[0-9a-f]{64}", review_key)
                or review_key in seen
                or not isinstance(parent_asin, str)
                or not parent_asin.strip()
            ):
                raise SourceError("source_invalid_response")
            seen.add(review_key)
            yield review

"""Generic source evidence sanitization helpers."""

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

"""Deterministic source-grounded chunking with token budgets and JSON Pointer provenance."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterator
from typing import Any

from .types import EvidenceChunk

CHUNKER_VERSION = "source-evidence-token-v2"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_MAX_TOKENS = 96
_BOUNDARY = re.compile(r"[.!?。！？][\"'”’)]*\s+|\n+")
_REVIEW_METADATA = ("rating", "timestamp", "helpful_vote", "verified_purchase")


def _escape_pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _string_leaves(
    value: object, pointer: str, *, canonical_scalars: bool = False
) -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        if value.strip():
            yield pointer, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _string_leaves(
                item, f"{pointer}/{index}", canonical_scalars=canonical_scalars
            )
    elif isinstance(value, dict):
        for key in sorted(value):
            yield from _string_leaves(
                value[key],
                f"{pointer}/{_escape_pointer_token(str(key))}",
                canonical_scalars=canonical_scalars,
            )
    elif canonical_scalars and isinstance(value, (bool, int, float)):
        yield pointer, json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )


def iter_product_fields(product: dict[str, object]) -> Iterator[tuple[str, str]]:
    for key in ("title", "features", "description", "details"):
        if key in product:
            yield from _string_leaves(
                product[key], f"/{key}", canonical_scalars=(key == "details")
            )


def iter_review_fields(review: dict[str, object]) -> Iterator[tuple[str, str]]:
    text = review.get("text")
    if isinstance(text, str) and text.strip():
        yield "/text", text
    else:
        title = review.get("title")
        if isinstance(title, str) and title.strip():
            yield "/title", title


def resolve_source_field(record: dict[str, object], pointer: str) -> str:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("source_field_must_be_json_pointer")
    value: object = record
    for escaped in pointer[1:].split("/"):
        if re.search(r"~(?![01])", escaped):
            raise ValueError("invalid_source_field_escape")
        token = escaped.replace("~1", "/").replace("~0", "~")
        try:
            if isinstance(value, list):
                if not re.fullmatch(r"0|[1-9][0-9]*", token):
                    raise ValueError("invalid_list_index")
                value = value[int(token)]
            elif isinstance(value, dict):
                value = value[token]
            else:
                raise ValueError("source_field_does_not_resolve")
        except (KeyError, IndexError, TypeError):
            raise ValueError("source_field_does_not_resolve") from None
    if isinstance(value, str):
        return value
    if value is None:
        raise ValueError("source_field_does_not_resolve_to_string")
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _identifier(record: dict[str, object], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key}_must_be_nonempty")
    return value


def _fallback_token_count(text: str) -> int:
    # UTF-8 bytes are a conservative upper bound for this model's token count.
    return len(text.encode("utf-8")) + 2


def _prefix_for_embedding(
    context: str, label: str, max_tokens: int, token_count: Callable[[str], int]
) -> str:
    prefix = "\n".join(part for part in (context, label) if part)
    if not prefix or token_count(prefix) <= max(1, max_tokens // 4):
        return prefix
    budget = max(1, max_tokens // 4)
    low, high = 0, len(prefix)
    while low < high:
        middle = (low + high + 1) // 2
        if token_count(prefix[:middle]) <= budget:
            low = middle
        else:
            high = middle - 1
    return prefix[:low].rstrip()


def _spans(
    text: str,
    prefix: str,
    max_tokens: int,
    token_count: Callable[[str], int],
) -> Iterator[tuple[int, int]]:
    separator = "\n" if prefix else ""

    def fits(start: int, end: int) -> bool:
        return token_count(f"{prefix}{separator}{text[start:end]}") <= max_tokens

    start = 0
    while start < len(text):
        if fits(start, len(text)):
            yield start, len(text)
            return
        low, high = start + 1, len(text)
        best = start
        while low <= high:
            middle = (low + high) // 2
            if fits(start, middle):
                best = middle
                low = middle + 1
            else:
                high = middle - 1
        if best == start:
            raise ValueError("embedding_prefix_exceeds_token_budget")

        # Prefer a sentence boundary, then whitespace, when it uses most of the
        # available window. The offsets still cover every original character.
        sentence_ends = [
            match.end()
            for match in _BOUNDARY.finditer(text, start, best)
            if match.end() - start >= max(1, (best - start) // 2)
        ]
        if sentence_ends:
            best = sentence_ends[-1]
        else:
            space_ends = [
                match.end()
                for match in re.finditer(r"\s+", text[start:best])
                if match.end() >= max(1, (best - start) // 2)
            ]
            if space_ends:
                best = start + space_ends[-1]
        yield start, best
        start = best


def _build(
    record: dict[str, object],
    category: str,
    dataset_version: str,
    source_type: str,
    fields: Iterator[tuple[str, str]],
    context: str,
    max_tokens: int,
    count_tokens: Callable[[str], int] | None,
) -> list[EvidenceChunk]:
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 1:
        raise ValueError("max_tokens_must_be_positive")
    if not isinstance(category, str) or not category.strip():
        raise ValueError("category_must_be_nonempty")
    if not isinstance(dataset_version, str) or not dataset_version.strip():
        raise ValueError("dataset_version_must_be_nonempty")
    token_count = count_tokens or _fallback_token_count
    product_id = _identifier(record, "product_id")
    source_id = _identifier(record, "review_key") if source_type == "review" else product_id
    chunker_version = f"{CHUNKER_VERSION}:max_tokens={max_tokens}"
    metadata = (
        {key: record[key] for key in _REVIEW_METADATA if key in record and key != "user_id"}
        if source_type == "review"
        else {}
    )
    chunks: list[EvidenceChunk] = []
    for field, original in fields:
        label = "/".join(
            token.replace("~1", "/").replace("~0", "~")
            for token in field[1:].split("/")
        )
        prefix = _prefix_for_embedding(context, label, max_tokens, token_count)
        for start, end in _spans(original, prefix, max_tokens, token_count):
            identity = [
                dataset_version,
                category,
                product_id,
                source_type,
                source_id,
                field,
                start,
                end,
                chunker_version,
                EMBEDDING_MODEL,
            ]
            chunk_id = hashlib.sha256(
                json.dumps(identity, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            evidence = original[start:end]
            embedding_text = "\n".join(part for part in (prefix, evidence) if part)
            if token_count(embedding_text) > max_tokens:
                raise ValueError("embedding_chunk_exceeds_token_budget")
            chunks.append(
                EvidenceChunk(
                    chunk_id=chunk_id,
                    dataset_version=dataset_version,
                    category=category,
                    product_id=product_id,
                    source_type=source_type,
                    source_id=source_id,
                    source_field=field,
                    start_offset=start,
                    end_offset=end,
                    evidence_text=evidence,
                    embedding_text=embedding_text,
                    source_metadata=dict(metadata),
                    embedding_model=EMBEDDING_MODEL,
                    chunker_version=chunker_version,
                )
            )
    return chunks


def build_product_chunks(
    product: dict[str, object],
    category: str,
    dataset_version: str,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    count_tokens: Callable[[str], int] | None = None,
) -> list[EvidenceChunk]:
    title = product.get("title")
    return _build(
        product,
        category,
        dataset_version,
        "product",
        iter_product_fields(product),
        title if isinstance(title, str) else "",
        max_tokens,
        count_tokens,
    )


def build_review_chunks(
    review: dict[str, object],
    product_title: str,
    category: str,
    dataset_version: str,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    count_tokens: Callable[[str], int] | None = None,
) -> list[EvidenceChunk]:
    review_title = review.get("title")
    context = "\n".join(
        value
        for value in (product_title, review_title)
        if isinstance(value, str) and value
    )
    return _build(
        review,
        category,
        dataset_version,
        "review",
        iter_review_fields(review),
        context,
        max_tokens,
        count_tokens,
    )

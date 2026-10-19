"""Product identity and lexical relevance; no catalogue IDs or LLM inference."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


def normalized(value: str) -> str:
    return re.sub(r"[^\w가-힣]+", "", unicodedata.normalize("NFKC", value).casefold())


def primary_title(payload: dict[str, Any]) -> str:
    # A serum with a free cream is still a serum. Preserve the original title
    # in responses; only identity matching uses this view.
    title = str(payload.get("title", ""))
    title = re.sub(r"^(?:\[[^\]]+\]\s*)+", "", title)
    return re.split(r"\(\s*\+|\+|증정|사은품", title, maxsplit=1)[0]


@dataclass(frozen=True)
class TypeIntent:
    product_type: str | None
    origin: str
    ambiguous: bool = False


class ProductTypeRegistry:
    def __init__(self, path: str | None = None):
        raw = json.loads(Path(path or Path(__file__).with_name("product_types.json")).read_text())
        self.version = raw["version"]
        self.types: dict[str, tuple[str, ...]] = {}
        self.parents: dict[str, tuple[str, ...]] = {}
        self.categories: dict[str, frozenset[str]] = {}
        for entry in raw["types"]:
            key = entry["id"]
            if not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,127}", key) or key in self.types:
                raise ValueError("invalid_product_type_registry")
            aliases = entry["aliases"]
            if not aliases or any(not isinstance(x, str) or not normalized(x) for x in aliases):
                raise ValueError("invalid_product_type_registry")
            self.types[key] = tuple(dict.fromkeys(normalized(x) for x in aliases))
            parents = entry.get("parents", [])
            categories = entry.get("categories", [])
            if (not isinstance(parents, list) or not isinstance(categories, list)
                or any(not isinstance(x, str) or not x for x in [*parents, *categories])):
                raise ValueError("invalid_product_type_registry")
            self.parents[key] = tuple(parents)
            self.categories[key] = frozenset(categories)
        if any(p not in self.types for parents in self.parents.values() for p in parents):
            raise ValueError("unknown_product_type_parent")
        self.ancestors: dict[str, frozenset[str]] = {}

        def ancestors(key: str, visited: frozenset[str]) -> frozenset[str]:
            if key in visited:
                raise ValueError("cyclic_product_type_registry")
            if key not in self.ancestors:
                found = set(self.parents[key])
                for parent in self.parents[key]:
                    found.update(ancestors(parent, visited | {key}))
                self.ancestors[key] = frozenset(found)
            return self.ancestors[key]

        for key in self.types:
            ancestors(key, frozenset())
        for key in self.types:
            if any(self.categories[k] for k in {key, *self.ancestors[key]}) and not self.category_scope(key):
                raise ValueError("conflicting_product_type_categories")

    def family(self, key: str) -> frozenset[str]:
        return frozenset({key, *(child for child in self.types if key in self.ancestors[child])})

    def category_scope(self, key: str) -> frozenset[str]:
        scopes = [self.categories[k] for k in {key, *self.ancestors.get(key, ())} if self.categories.get(k)]
        return frozenset.intersection(*scopes) if scopes else frozenset()

    def _most_specific(self, matches: set[str]) -> set[str]:
        return {key for key in matches if not any(key in self.ancestors[other] for other in matches)}

    def _resolve_matches(self, matches: set[str], origin: str) -> TypeIntent:
        matches = self._most_specific(matches)
        if len(matches) <= 1:
            return TypeIntent(next(iter(matches)) if matches else None, origin if matches else "unspecified")
        # Several forms of one family (e.g. powder/drink) are searchable as
        # that family; unrelated product requests still need clarification.
        common = set.intersection(*(set(self.ancestors[key]) for key in matches))
        common = self._most_specific(common)
        return TypeIntent(next(iter(common)), origin) if len(common) == 1 else TypeIntent(None, origin, True)

    def matches(self, text: str) -> set[str]:
        text = normalized(text)
        hits = [(alias, key) for key, aliases in self.types.items() for alias in aliases if alias in text]
        # Prefer compound aliases to their substrings, e.g. pet shampoo.
        return self._most_specific({key for alias, key in hits if not any(
            alias != other and alias in other for other, _ in hits
        )})

    def intent(self, query: str, explicit: str | None) -> TypeIntent:
        if explicit is not None:
            key = explicit.strip()
            if key in self.types:
                return TypeIntent(key, "brain")
            matches = self.matches(key)
            if matches:
                return self._resolve_matches(matches, "brain")
            # An unknown type is an exact, normalized catalogue identity.
            # Never silently ignore a new type supplied by Shopping Brain.
            return TypeIntent(key, "brain", len(matches) > 1)
        matches = self.matches(query)
        if "water_filter" not in matches and re.search(r"정수기|정수|브리타", query) and "필터" in query:
            matches.add("water_filter")
        if "shampoo" in matches and re.search(r"강아지|반려견|애견|반려동물", query):
            matches.discard("shampoo")
            matches.add("pet_shampoo")
        # Conflicting requested types require clarification, not an arbitrary
        # choice of one type and silently dropping the others.
        return self._resolve_matches(matches, "query")

    def request_intent(self, query: str, explicit: str | None, original_question: str) -> TypeIntent:
        """A rewritten query or caller-supplied type must not change the item requested."""
        inferred = self.intent(query, None)
        original = self.intent(original_question, None)
        chosen = self.intent(query, explicit) if explicit else inferred
        if not chosen.product_type and not chosen.ambiguous:
            chosen = TypeIntent(original.product_type, "original_question", original.ambiguous)
        for other in (inferred, original):
            if chosen.ambiguous or other.ambiguous:
                return TypeIntent(None, "conflict", True)
            if chosen.product_type is None or other.product_type is None:
                continue
            if not self.family(chosen.product_type).intersection(self.family(other.product_type)):
                return TypeIntent(None, "conflict", True)
            if other.product_type in self.family(chosen.product_type):
                chosen = TypeIntent(other.product_type, chosen.origin)
        return chosen

    def product_matches(self, payload: dict[str, Any], product_type: str) -> bool:
        features = payload.get("features")
        features = features if isinstance(features, dict) else {}
        family = self.family(product_type)
        scopes = self.category_scope(product_type)
        category = payload.get("category") or payload.get("main_category")
        if scopes and category not in scopes:
            return False
        canonical = features.get("canonical_product_type")
        if isinstance(canonical, str) and canonical.strip():
            identity = self.intent(canonical, canonical)
            return normalized(canonical) == normalized(product_type) or identity.product_type in family
        title = primary_title(payload)
        title_types = self.matches(title)
        if product_type == "pet_shampoo":
            return "shampoo" in title_types and bool(re.search(
                r"강아지|반려|애견|펫", title + str(features.get("comparison_family", ""))
            )) or "pet_shampoo" in title_types
        if product_type == "shampoo" and self.product_matches(payload, "pet_shampoo"):
            return False
        if product_type == "water_filter":
            return "필터" in title and bool(re.search(r"정수|브리타", title))
        if title_types.intersection(family):
            return True
        if product_type in self.types:
            # Conflicting main-item titles override overly broad source labels.
            if title_types:
                return False
            labels = " ".join(str(features.get(k, "")) for k in (
                "product_type", "canonical_product_type", "comparison_family", "sub_category"
            ))
            return bool(family.intersection(self.matches(labels)))
        values = [features.get("canonical_product_type"), features.get("product_type"), payload.get("product_type")]
        return normalized(product_type) in {normalized(x) for x in values if isinstance(x, str)}


@lru_cache(maxsize=8)
def type_registry(path: str | None = None) -> ProductTypeRegistry:
    return ProductTypeRegistry(path)


_GENERIC = {
    "추천", "추천해줘", "추천해주세요", "찾고", "있어", "찾아줘", "상품", "제품", "구매", "사고",
    "싶어", "쓸", "사용할", "사용", "바를", "바르는", "사용하는", "먹는", "마시는", "할", "때", "위한",
    "좀", "좋은", "있는", "가능한", "후기", "리뷰", "근거", "알려줘", "보여줘", "please", "recommend", "find",
}


def query_terms(query: str) -> list[str]:
    terms = re.findall(r"[가-힣A-Za-z0-9]+", unicodedata.normalize("NFKC", query).casefold())
    return list(dict.fromkeys(x for x in terms if len(x) >= 2 and x not in _GENERIC and not x.isdigit()))


def lexical_relevance(query: str, payload: dict[str, Any]) -> tuple[int, float]:
    title = normalized(primary_title(payload))
    if normalized(query) == normalized(str(payload.get("title", ""))):
        return 2, 1.0
    terms = query_terms(query)
    if not terms:
        return 0, 0.0
    features = payload.get("features")
    features = features if isinstance(features, dict) else {}
    identity = normalized(" ".join([primary_title(payload), str(payload.get("brand", "")), *[
        str(features.get(k, "")) for k in ("product_type", "canonical_product_type", "comparison_family")
    ]]))
    title_hits = sum(normalized(x) in title for x in terms)
    identity_hits = sum(normalized(x) in identity for x in terms)
    return int(title_hits > 0), (2 * title_hits + identity_hits) / (3 * len(terms))

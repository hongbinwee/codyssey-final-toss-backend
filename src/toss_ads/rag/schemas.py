"""Pydantic request shapes for the Agent-to-RAG API."""

from __future__ import annotations

import math
import re
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, field_validator, model_validator


class PriceFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    price_min: float | None = None
    price_max: float | None = None
    currency: StrictStr | None = None
    in_stock: StrictBool | None = None

    @field_validator("price_min", "price_max", mode="before")
    @classmethod
    def finite_nonnegative_amount(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("price_must_be_numeric")
        if not math.isfinite(float(value)) or value < 0:
            raise ValueError("invalid_price")
        return float(value)

    @field_validator("currency")
    @classmethod
    def valid_currency_code(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[A-Z]{3}", value):
            raise ValueError("invalid_currency")
        return value


class RagSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: StrictStr | None = Field(default=None, max_length=128)
    original_question: StrictStr = Field(min_length=1, max_length=4000)
    query: StrictStr = Field(min_length=1, max_length=1000)
    category: StrictStr | None = Field(default=None, min_length=1, max_length=128)
    profile: StrictStr | None = Field(default=None, min_length=1, max_length=128)
    product_type: StrictStr | None = Field(default=None, min_length=1, max_length=128)
    filters: PriceFilters = Field(default_factory=PriceFilters)
    required_conditions: list[StrictStr] = Field(default_factory=list, max_length=20)
    preferences: list[StrictStr] = Field(default_factory=list, max_length=20)
    product_ids: list[StrictStr] | None = Field(default=None, min_length=1, max_length=3)
    source_type: Literal["review"] | None = None
    top_k: StrictInt = Field(default=10, ge=1, le=20)

    @field_validator("request_id", "original_question", "query", "category", "profile", "product_type")
    @classmethod
    def nonblank_string(cls, value: StrictStr | None) -> StrictStr | None:
        if value is not None and not value.strip():
            raise ValueError("blank_string")
        return value

    @field_validator("required_conditions", "preferences")
    @classmethod
    def bounded_nonblank_conditions(cls, values: list[StrictStr]) -> list[StrictStr]:
        if any(not value.strip() or len(value) > 500 for value in values):
            raise ValueError("invalid_condition")
        return values

    @field_validator("product_ids")
    @classmethod
    def valid_product_ids(cls, values: list[StrictStr] | None) -> list[StrictStr] | None:
        if values is None:
            return None
        if any(
            not value.strip()
            or value != value.strip()
            or len(value) > 256
            or any(ord(char) < 32 or ord(char) == 127 for char in value)
            for value in values
        ):
            raise ValueError("invalid_product_id")
        if len(set(values)) != len(values):
            raise ValueError("duplicate_product_id")
        return values

    @model_validator(mode="after")
    def valid_price_range(self) -> "RagSearchRequest":
        low, high = self.filters.price_min, self.filters.price_max
        if low is not None and high is not None and low > high:
            raise ValueError("invalid_price_range")
        if (low is not None or high is not None) and self.filters.currency is None:
            raise ValueError("currency_required")
        if self.source_type == "review":
            if self.product_ids is None:
                raise ValueError("product_ids_required_for_review_search")
        return self


class ProductScopedReviewRequest(BaseModel):
    """Follow-up review search scoped to products already recommended upstream."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    request_id: StrictStr | None = Field(default=None, max_length=128)
    profile: StrictStr | None = Field(default=None, min_length=1, max_length=128)
    dataset_version: StrictStr | None = Field(default=None, min_length=1, max_length=256)
    category: StrictStr | None = Field(default=None, min_length=1, max_length=128)
    product_ids: list[StrictStr] = Field(
        min_length=1,
        max_length=50,
        validation_alias=AliasChoices("productIds", "product_ids"),
    )
    aspect: StrictStr = Field(min_length=1, max_length=64)
    query: StrictStr = Field(min_length=1, max_length=1000)
    limit_per_product: StrictInt = Field(default=3, ge=1, le=10)

    @field_validator("request_id", "profile", "dataset_version", "category", "aspect", "query")
    @classmethod
    def nonblank_review_filter(cls, value: StrictStr | None) -> StrictStr | None:
        if value is not None and not value.strip():
            raise ValueError("blank_string")
        return value

    @field_validator("aspect")
    @classmethod
    def normalized_aspect(cls, value: str) -> str:
        return value.strip().casefold()

    @field_validator("product_ids")
    @classmethod
    def valid_product_ids(cls, values: list[StrictStr]) -> list[StrictStr]:
        if any(not value.strip() or len(value) > 256 for value in values):
            raise ValueError("invalid_product_id")
        if len(set(values)) != len(values):
            raise ValueError("duplicate_product_id")
        return values


class ProductScopedReviewAggregateRequest(BaseModel):
    """Full-population aspect counts; this is separate from top-ranked evidence."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    request_id: StrictStr | None = Field(default=None, max_length=128)
    profile: StrictStr | None = Field(default=None, min_length=1, max_length=128)
    dataset_version: StrictStr | None = Field(default=None, min_length=1, max_length=256)
    category: StrictStr | None = Field(default=None, min_length=1, max_length=128)
    product_ids: list[StrictStr] = Field(
        min_length=1,
        max_length=50,
        validation_alias=AliasChoices("productIds", "product_ids"),
    )
    aspect: StrictStr = Field(min_length=1, max_length=64)

    @field_validator("request_id", "profile", "dataset_version", "category", "aspect")
    @classmethod
    def nonblank_aggregate_filter(cls, value: StrictStr | None) -> StrictStr | None:
        if value is not None and not value.strip():
            raise ValueError("blank_string")
        return value

    @field_validator("aspect")
    @classmethod
    def normalized_aggregate_aspect(cls, value: str) -> str:
        return value.strip().casefold()

    @field_validator("product_ids")
    @classmethod
    def valid_aggregate_product_ids(cls, values: list[StrictStr]) -> list[StrictStr]:
        if any(not value.strip() or len(value) > 256 for value in values):
            raise ValueError("invalid_product_id")
        if len(set(values)) != len(values):
            raise ValueError("duplicate_product_id")
        return values

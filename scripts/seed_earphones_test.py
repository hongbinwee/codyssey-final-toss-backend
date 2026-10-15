"""Generate an isolated synthetic earphone dataset for the Toss schema.

The script only renders SQL. It never connects to a database by itself, which
makes it safe to review before applying the generated SQL to the test schema.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_SCHEMA = "test_earphones"
DEFAULT_SEED = 20261015
BASE_WRITTEN_AT = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)

BRANDS = [
    "Auralink",
    "SoundNest",
    "PulseArc",
    "NovaTone",
    "EchoBloom",
    "KinetiSound",
    "LumaBeat",
    "WaveCraft",
    "MellowPods",
    "Sonicraft",
]

COLORS = ["black", "white", "navy", "sage", "lavender"]
WATER_RESISTANCE = ["IPX4", "IPX5", "IPX7"]
CODECS = ["SBC/AAC", "SBC/AAC/aptX", "SBC/AAC/LDAC"]

RATING_PROFILES = [
    # Every profile starts with one of each rating. The remaining ratings make
    # product averages meaningfully different while retaining diversity.
    [1, 2, 3, 4, 5, 5, 5, 5, 5, 5, 4, 4, 4, 4, 3, 3, 5, 4, 5, 5],
    [1, 2, 3, 4, 5, 4, 4, 4, 4, 4, 5, 5, 3, 3, 3, 4, 5, 2, 4, 3],
    [1, 2, 3, 4, 5, 3, 3, 3, 4, 4, 4, 2, 2, 5, 4, 3, 2, 4, 3, 5],
    [1, 2, 3, 4, 5, 2, 2, 2, 3, 3, 3, 4, 4, 5, 3, 2, 3, 4, 1, 2],
    [1, 2, 3, 4, 5, 1, 1, 1, 2, 2, 2, 3, 3, 4, 2, 1, 2, 3, 2, 1],
]

REVIEW_SENTENCES = {
    5: [
        "착용감이 편하고 음질이 기대보다 좋습니다.",
        "통화 품질과 배터리 모두 만족스럽습니다.",
        "출퇴근용으로 사용하기에 아주 편리합니다.",
    ],
    4: [
        "전반적으로 만족스럽고 가격 대비 괜찮습니다.",
        "음질은 좋고 연결도 안정적이지만 조금 아쉬운 부분이 있습니다.",
        "디자인과 사용성이 좋아서 자주 사용하고 있습니다.",
    ],
    3: [
        "무난하게 사용할 수 있지만 특별한 장점은 잘 모르겠습니다.",
        "기본 기능은 괜찮고 기대한 수준의 제품입니다.",
        "음질은 보통이며 상황에 따라 만족도가 달라질 것 같습니다.",
    ],
    2: [
        "기능은 작동하지만 착용감과 연결성이 아쉽습니다.",
        "가격을 생각하면 이해되지만 개선할 부분이 보입니다.",
        "배터리와 통화 품질에서 아쉬움이 있었습니다.",
    ],
    1: [
        "연결이 자주 끊겨서 사용하기 불편했습니다.",
        "기대와 달리 착용감과 음질이 만족스럽지 않았습니다.",
        "초기에는 작동했지만 안정적으로 사용하기 어려웠습니다.",
    ],
}


def generate_products(count: int = 50, seed: int = DEFAULT_SEED) -> list[dict[str, Any]]:
    """Return deterministic synthetic earphone products."""
    if count < 1:
        raise ValueError("count must be at least 1")

    rng = random.Random(seed)
    products: list[dict[str, Any]] = []
    for index in range(1, count + 1):
        brand = BRANDS[(index - 1) % len(BRANDS)]
        series = (index - 1) // len(BRANDS) + 1
        product_id = f"earphone-test-{index:03d}"
        product_name = f"{brand} Air {series}-{index:02d}"
        products.append(
            {
                "id": product_id,
                "name": product_name,
                "brand": brand,
                "category": "earphones",
                "description": (
                    f"{product_name}는 일상적인 음악 감상과 통화를 위한 "
                    "합성 테스트용 무선 이어폰입니다."
                ),
                "image_urls": [],
                "specs_json": {
                    "type": "true_wireless",
                    "connection": "Bluetooth 5.3",
                    "anc": index % 3 != 0,
                    "battery_hours": 5 + (index % 6),
                    "driver_mm": 10 + (index % 4),
                    "water_resistance": WATER_RESISTANCE[index % len(WATER_RESISTANCE)],
                    "codec": CODECS[index % len(CODECS)],
                    "color": COLORS[index % len(COLORS)],
                    "synthetic_seed": seed,
                },
                "active": True,
                "version": 1,
                "_price": 39_900 + ((index * 7_300) % 180_000),
                "_stock": 20 + ((index * 13) % 81),
                "_rng_marker": rng.randrange(1000, 9999),
            }
        )
    return products


def generate_variants(products: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create one default variant per synthetic product."""
    variants: list[dict[str, Any]] = []
    for product in products:
        index = int(product["id"].rsplit("-", 1)[1])
        variants.append(
            {
                "id": f"{product['id']}-v1",
                "product_id": product["id"],
                "option_values_json": {
                    "color": product["specs_json"]["color"],
                    "bundle": "standard",
                },
                "spec_overrides_json": {},
                "unit_price_won": product["_price"],
                "stock_qty": product["_stock"],
                "active": True,
                "version": 1,
                "_index": index,
            }
        )
    return variants


def generate_reviews(
    products: Iterable[dict[str, Any]],
    reviews_per_product: int = 20,
    seed: int = DEFAULT_SEED,
) -> list[dict[str, Any]]:
    """Return deterministic reviews with all ratings represented per product."""
    if reviews_per_product < 5:
        raise ValueError("reviews_per_product must be at least 5 to include ratings 1 through 5")

    reviews: list[dict[str, Any]] = []
    for product_index, product in enumerate(products, start=1):
        product_id = product["id"]
        product_number = int(product_id.rsplit("-", 1)[1])
        profile = RATING_PROFILES[(product_number - 1) % len(RATING_PROFILES)]
        ratings = (profile * ((reviews_per_product + len(profile) - 1) // len(profile)))[:reviews_per_product]
        random.Random(seed + product_index * 7919).shuffle(ratings)

        for review_number, rating in enumerate(ratings, start=1):
            sentence = REVIEW_SENTENCES[rating][(product_number + review_number) % len(REVIEW_SENTENCES[rating])]
            written_at = BASE_WRITTEN_AT - timedelta(days=(product_number * 3 + review_number))
            reviews.append(
                {
                    "id": f"{product_id}-review-{review_number:02d}",
                    "product_id": product_id,
                    "variant_id": f"{product_id}-v1",
                    "rating": rating,
                    "body": f"{product['name']} 리뷰: {sentence}",
                    "source_kind": "SYNTHETIC",
                    "source_ref": "earphones-test-v1",
                    "written_at": written_at.isoformat(),
                }
            )
    return reviews


def _sql_text(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _sql_json(value: Any) -> str:
    return f"{_sql_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')))}::jsonb"


def _sql_bool(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def _values(rows: Iterable[Iterable[str]]) -> str:
    return ",\n".join("(" + ", ".join(row) + ")" for row in rows)


def _product_rows(products: Iterable[dict[str, Any]]) -> Iterable[list[str]]:
    for product in products:
        yield [
            _sql_text(product["id"]),
            _sql_text(product["name"]),
            _sql_text(product["brand"]),
            _sql_text(product["category"]),
            _sql_text(product["description"]),
            _sql_json(product["image_urls"]),
            _sql_json(product["specs_json"]),
            _sql_bool(product["active"]),
            str(product["version"]),
        ]


def _variant_rows(variants: Iterable[dict[str, Any]]) -> Iterable[list[str]]:
    for variant in variants:
        yield [
            _sql_text(variant["id"]),
            _sql_text(variant["product_id"]),
            _sql_json(variant["option_values_json"]),
            _sql_json(variant["spec_overrides_json"]),
            str(variant["unit_price_won"]),
            str(variant["stock_qty"]),
            _sql_bool(variant["active"]),
            str(variant["version"]),
        ]


def _review_rows(reviews: Iterable[dict[str, Any]]) -> Iterable[list[str]]:
    for review in reviews:
        yield [
            _sql_text(review["id"]),
            _sql_text(review["product_id"]),
            _sql_text(review["variant_id"]),
            str(review["rating"]),
            _sql_text(review["body"]),
            _sql_text(review["source_kind"]),
            _sql_text(review["source_ref"]),
            f"{_sql_text(review['written_at'])}::timestamptz",
        ]


def render_seed_sql(
    schema: str = DEFAULT_SCHEMA,
    product_count: int = 50,
    reviews_per_product: int = 20,
    seed: int = DEFAULT_SEED,
) -> str:
    """Render an idempotent SQL transaction for the isolated test schema."""
    if not schema.isidentifier():
        raise ValueError("schema must be a simple SQL identifier")

    products = generate_products(count=product_count, seed=seed)
    variants = generate_variants(products)
    reviews = generate_reviews(products, reviews_per_product=reviews_per_product, seed=seed)

    sql: list[str] = [
        "-- Synthetic earphone fixture; only the isolated test schema is replaced.",
        "BEGIN;",
        f"DROP SCHEMA IF EXISTS {schema} CASCADE;",
        f"CREATE SCHEMA {schema};",
        "",
        f"CREATE TABLE {schema}.products (LIKE public.products INCLUDING ALL);",
        f"CREATE TABLE {schema}.product_variants (LIKE public.product_variants INCLUDING ALL);",
        f"CREATE TABLE {schema}.reviews (LIKE public.reviews INCLUDING ALL);",
        "",
        f"ALTER TABLE {schema}.product_variants",
        f"  ADD CONSTRAINT product_variants_product_id_fkey FOREIGN KEY (product_id) REFERENCES {schema}.products(id);",
        f"ALTER TABLE {schema}.reviews",
        f"  ADD CONSTRAINT reviews_product_id_fkey FOREIGN KEY (product_id) REFERENCES {schema}.products(id);",
        f"ALTER TABLE {schema}.reviews",
        f"  ADD CONSTRAINT reviews_product_id_variant_id_fkey FOREIGN KEY (product_id, variant_id) REFERENCES {schema}.product_variants(product_id, id);",
        "",
        f"INSERT INTO {schema}.products (id, name, brand, category, description, image_urls, specs_json, active, version) VALUES",
        _values(_product_rows(products)) + ";",
        "",
        f"INSERT INTO {schema}.product_variants (id, product_id, option_values_json, spec_overrides_json, unit_price_won, stock_qty, active, version) VALUES",
        _values(_variant_rows(variants)) + ";",
        "",
        f"INSERT INTO {schema}.reviews (id, product_id, variant_id, rating, body, source_kind, source_ref, written_at) VALUES",
        _values(_review_rows(reviews)) + ";",
        "",
        "COMMIT;",
    ]
    return "\n".join(sql) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", default=DEFAULT_SCHEMA)
    parser.add_argument("--products", type=int, default=50)
    parser.add_argument("--reviews-per-product", type=int, default=20)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    sql = render_seed_sql(
        schema=args.schema,
        product_count=args.products,
        reviews_per_product=args.reviews_per_product,
        seed=args.seed,
    )
    if args.output:
        args.output.write_text(sql, encoding="utf-8")
    else:
        print(sql, end="")


if __name__ == "__main__":
    main()

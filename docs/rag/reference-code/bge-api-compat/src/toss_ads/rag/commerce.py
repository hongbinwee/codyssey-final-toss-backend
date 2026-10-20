"""Read-only Commerce hydration. Identifiers come from server configuration."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

from psycopg import sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import Settings
from .schemas import PriceFilters


class CommerceUnavailable(RuntimeError):
    pass


class CommerceStore:
    def __init__(self, settings: Settings):
        if not settings.commerce_database_url:
            raise CommerceUnavailable("commerce_not_configured")
        parsed = urlsplit(settings.commerce_database_url)
        if parsed.port not in (None, 5432) or parsed.path != "/toss":
            raise ValueError("invalid_configuration:COMMERCE_DATABASE_URL")
        self.schemas = dict(settings.commerce_schema_map)
        self.pool = ConnectionPool(
            conninfo=settings.commerce_database_url, min_size=1, max_size=4,
            kwargs={"row_factory": dict_row}, open=True,
        )
        try:
            self.pool.wait(timeout=10)
        except Exception:
            self.pool.close()
            raise

    def close(self) -> None:
        self.pool.close()

    def lookup(
        self, products: list[dict[str, Any]], filters: PriceFilters, require_stock: bool
    ) -> dict[tuple[str, str], dict[str, Any]]:
        """Check price and stock on the SAME variant before choosing one per item."""
        if filters.currency not in (None, "KRW"):
            raise CommerceUnavailable("unsupported_currency")
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for product in products:
            dataset = product["payload"].get("source_dataset")
            schema = self.schemas.get(dataset)
            if not schema:
                raise CommerceUnavailable("commerce_source_unmapped")
            groups[schema].append(product)
        result: dict[tuple[str, str], dict[str, Any]] = {}
        # One snapshot for all source schemas. The account should also have
        # SELECT-only grants; transaction_read_only is a second boundary.
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                conn.execute("SET LOCAL statement_timeout = '5s'")
                for schema, candidates in groups.items():
                    rows = conn.execute(sql.SQL("""
                        SELECT p.id AS product_id, p.category, v.id AS variant_id,
                               v.unit_price_won, v.stock_qty
                        FROM {}.products p
                        JOIN {}.product_variants v ON v.product_id = p.id
                        WHERE p.id = ANY(%s::text[])
                          AND (%s::numeric IS NULL OR v.unit_price_won >= %s)
                          AND (%s::numeric IS NULL OR v.unit_price_won <= %s)
                          AND (NOT %s OR v.stock_qty > 0)
                        ORDER BY p.id, v.unit_price_won, v.id
                    """).format(sql.Identifier(schema), sql.Identifier(schema)), (
                        [p["product_id"] for p in candidates],
                        filters.price_min, filters.price_min, filters.price_max, filters.price_max,
                        require_stock,
                    )).fetchall()
                    requested = {(p["category"], p["product_id"]): p for p in candidates}
                    for row in rows:
                        key = (row["category"], row["product_id"])
                        if key not in requested or key in result:
                            continue
                        payload = requested[key]["payload"]
                        price = payload.get("price")
                        price = price if isinstance(price, dict) else {}
                        result[key] = {
                            "variant_id": row["variant_id"],
                            "unit_price_won": row["unit_price_won"],
                            "currency": "KRW", "stock_qty": row["stock_qty"],
                            "checked_at": datetime.now(timezone.utc).isoformat(),
                            "validation_status": "verified_database_row",
                            "source_database": "toss", "source_schema": schema,
                            "price_basis": "selected_commerce_variant",
                            "is_simulated": price.get("is_simulated"),
                            "purchase_mode": "demo" if schema != "public" else "commerce",
                            "is_live_market_price": False,
                            "dataset_release_status": payload.get("dataset_release_status"),
                            "source_price_evidence_status": price.get("evidence_status"),
                        }
        return result

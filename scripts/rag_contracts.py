"""Validate RAG v0.1 JSON, original evidence, and optional live search results."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
from typing import Any
from urllib.parse import quote

import httpx
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts/amazon-reviews-rag/v0.1"


class ContractError(ValueError):
    """A public contract or source provenance invariant was violated."""


def read_json(path: Path) -> Any:
    def reject_constant(value: str):
        raise ContractError("non_finite_number")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)


def _safe_json(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError("non_finite_number")
    if isinstance(value, dict):
        if "user_id" in value:
            raise ContractError("user_id_not_allowed")
        for item in value.values():
            _safe_json(item)
    elif isinstance(value, list):
        for item in value:
            _safe_json(item)


def normalize_source(value: Any) -> Any:
    """Copy original source content while removing user IDs at every depth."""
    if isinstance(value, dict):
        return {key: normalize_source(item) for key, item in value.items() if key != "user_id"}
    if isinstance(value, list):
        return [normalize_source(item) for item in value]
    return value


def validate(kind: str, payload: dict) -> None:
    if kind not in {"request", "response", "source"}:
        raise ContractError("unknown_contract")
    schema = read_json(CONTRACTS / f"{kind}.schema.json")
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(payload))
    if errors:
        # Do not print payload fragments, original questions or reviewer data.
        path = "/".join(str(part) for part in errors[0].absolute_path)
        raise ContractError(f"schema_violation:{path or '$'}")
    _safe_json(payload)
    if kind == "request":
        price = payload.get("filters", {})
        low, high = price.get("price_min"), price.get("price_max")
        if low is not None and high is not None and low > high:
            raise ContractError("invalid_price_range")
        if (low is not None or high is not None) and not price.get("currency"):
            raise ContractError("currency_required")
    elif kind == "source":
        review = payload["review"]
        if review is not None and review["parent_asin"] != payload["product"]["parent_asin"]:
            raise ContractError("review_product_mismatch")
    else:
        status, items, error = payload["status"], payload["items"], payload["error_code"]
        if status == "ok":
            if not items or error is not None or not payload["dataset_version"]:
                raise ContractError("invalid_ok_response")
        elif items or (status == "error") != (error is not None):
            raise ContractError("invalid_empty_or_error_response")
        if status != "error" and not payload["dataset_version"]:
            raise ContractError("dataset_version_required")
        seen: set[tuple[str, str]] = set()
        for rank, item in enumerate(items, 1):
            identity = (item["category"], item["product_id"])
            if identity in seen:
                raise ContractError("duplicate_product")
            seen.add(identity)
            for evidence in item["evidence"]:
                if evidence["product_id"] != item["product_id"]:
                    raise ContractError("evidence_product_mismatch")
                if evidence["source_version"] != payload["dataset_version"]:
                    raise ContractError("source_version_mismatch")
                if evidence["end_offset"] - evidence["start_offset"] != len(evidence["evidence_text"]):
                    raise ContractError("evidence_offset_length_mismatch")
                if evidence["rrf_rank"] != rank:
                    raise ContractError("rrf_rank_mismatch")
                if evidence["bm25_rank"] is None and evidence["vector_rank"] is None:
                    raise ContractError("search_rank_required")
                if evidence["source_type"] == "product" and evidence["source_id"] != item["product_id"]:
                    raise ContractError("product_source_id_mismatch")


def load_cases(split: str = "all") -> list[dict]:
    cases = read_json(ROOT / "evals/amazon_reviews_rag_cases.json")["cases"]
    return [case for case in cases if split == "all" or case["split"] == split]


def load_sources() -> dict:
    return read_json(ROOT / "evals/fixtures/amazon_reviews_rag_sources.json")


def source_field(payload: dict, path: str) -> str:
    """Resolve title, features[0], or details[\"Brand\"] without evaluating code."""
    match = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+|"(?:[^"\\]|\\.)*")\])?', path)
    if match is None:
        raise ContractError("invalid_source_field")
    value = payload.get(match.group(1))
    selector = match.group(2)
    try:
        if selector is not None:
            value = value[json.loads(selector)]
    except (IndexError, KeyError, TypeError, json.JSONDecodeError):
        raise ContractError("source_field_missing") from None
    if value is None:
        raise ContractError("source_field_missing")
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _source_record(label: dict, sources: dict) -> dict:
    for entry in sources["records"]:
        if (entry["category"], entry["product"]["parent_asin"]) != (label["category"], label["product_id"]):
            continue
        if label["source_type"] == "product":
            if label["source_id"] == label["product_id"]:
                return entry["product"]
            break
        for review in entry["reviews"]:
            if review["review_key"] == label["source_id"]:
                if review["parent_asin"] != label["product_id"]:
                    raise ContractError("review_product_mismatch")
                return review
    raise ContractError("source_not_found")


def verify_case_sources(case: dict, sources: dict) -> int:
    _safe_json(sources)
    if case["dataset_version"] != sources["dataset_version"]:
        raise ContractError("dataset_version_mismatch")
    for label in case["relevant"]:
        text = source_field(_source_record(label, sources), label["source_field"])
        start, end = label["start_offset"], label["end_offset"]
        if not (0 <= start < end <= len(text)) or text[start:end] != label["evidence_text"]:
            raise ContractError("gold_evidence_mismatch")
    return len(case["relevant"])


def verify_evidence(item: dict, evidence: dict, sources: dict) -> None:
    if evidence["source_version"] != sources["dataset_version"]:
        raise ContractError("source_version_mismatch")
    label = dict(evidence, category=item["category"], product_id=item["product_id"])
    original = _source_record(label, sources)
    product_label = dict(label, source_type="product", source_id=item["product_id"])
    product = _source_record(product_label, sources)
    for returned, source in [(item["product_metadata"], product), (evidence["source_metadata"], original)]:
        for key, value in returned.items():
            if key not in source or json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False) != json.dumps(source[key], sort_keys=True, ensure_ascii=False, allow_nan=False):
                raise ContractError("returned_metadata_mismatch")
    text = source_field(original, evidence["source_field"])
    start, end = evidence["start_offset"], evidence["end_offset"]
    if not (0 <= start < end <= len(text)) or text[start:end] != evidence["evidence_text"]:
        raise ContractError("returned_evidence_mismatch")


def evaluate_response(case: dict, response: Any, sources: dict) -> dict:
    result = {"case_id": case["case_id"], "status": response.get("status") if isinstance(response, dict) else None,
              "contract_valid": False, "status_match": False, "product_hit": False,
              "source_hit": False, "evidence_checked": 0, "invalid_evidence": 0, "passed": False}
    try:
        validate("response", response)
        verify_case_sources(case, sources)
        if response["dataset_version"] != case["dataset_version"]:
            raise ContractError("response_version_mismatch")
    except ContractError as error:
        result["error_code"] = str(error)
        return result
    result["contract_valid"] = True
    result["status_match"] = response["status"] == case["expected_status"]
    for item in response["items"]:
        matching = [label for label in case["relevant"]
                    if (label["category"], label["product_id"]) == (item["category"], item["product_id"])]
        result["product_hit"] |= bool(matching)
        for evidence in item["evidence"]:
            result["evidence_checked"] += 1
            try:
                verify_evidence(item, evidence, sources)
            except ContractError:
                result["invalid_evidence"] += 1
                continue
            for label in matching:
                if (evidence["source_type"], evidence["source_id"], evidence["source_field"]) == (
                        label["source_type"], label["source_id"], label["source_field"]):
                    if evidence["start_offset"] <= label["start_offset"] and evidence["end_offset"] >= label["end_offset"]:
                        result["source_hit"] = True
    relevant_ok = not case["relevant"] or (result["product_hit"] and result["source_hit"])
    result["passed"] = bool(result["status_match"] and relevant_ok and not result["invalid_evidence"])
    return result


def collect_live_sources(base_url: str, cases: list[dict], *, transport=None) -> dict:
    """Read original API pages while requiring a single unchanging snapshot."""
    records = []
    seen_review_keys: set[tuple[str, str]] = set()
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=20, transport=transport) as client:
        def get(path: str) -> dict:
            value = client.get(path)
            value.raise_for_status()
            payload = normalize_source(value.json())
            _safe_json(payload)
            return payload
        version = get("/healthz")["dataset_version"]
        if any(case["dataset_version"] != version for case in cases):
            raise ContractError("dataset_version_mismatch")
        products = sorted({(label["category"], label["product_id"])
                           for case in cases for label in case["relevant"]})
        for category, product_id in products:
            prefix = f"/v1/categories/{quote(category, safe='')}"
            product = get(f"{prefix}/products/{quote(product_id, safe='')}")
            if product.get("parent_asin") != product_id:
                raise ContractError("product_id_mismatch")
            reviews, offset, total = [], 0, None
            while total is None or offset < total:
                page = get(f"{prefix}/reviews?parent_asin={quote(product_id, safe='')}&limit=200&offset={offset}")
                if page.get("dataset_version") != version:
                    raise ContractError("dataset_version_mismatch")
                if type(page.get("total")) is not int or page["total"] < 0:
                    raise ContractError("invalid_source_page")
                if page.get("offset") != offset or page.get("limit") != 200 or not isinstance(page.get("items"), list):
                    raise ContractError("invalid_source_page")
                if total is not None and total != page["total"]:
                    raise ContractError("source_total_changed")
                total = page["total"]
                if len(page["items"]) != min(200, max(0, total - offset)):
                    raise ContractError("incomplete_source_page")
                for review in page["items"]:
                    key = review.get("review_key")
                    if review.get("parent_asin") != product_id or not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key):
                        raise ContractError("review_product_mismatch")
                    if (category, key) in seen_review_keys:
                        raise ContractError("duplicate_review_key")
                    seen_review_keys.add((category, key))
                reviews.extend(page["items"])
                offset += 200
            if len(reviews) != total:
                raise ContractError("incomplete_source_page")
            records.append({"category": category, "product": product, "reviews": reviews})
        if get("/healthz")["dataset_version"] != version:
            raise ContractError("dataset_version_mismatch")
    return {"dataset_version": version, "records": records}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("examples", "sources", "search"), default="examples")
    parser.add_argument("--split", choices=("all", "tuning", "holdout"), default="all")
    parser.add_argument("--api-base-url")
    parser.add_argument("--rag-base-url")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report: dict = {"mode": args.mode, "search_executed": False, "passed": False}
    try:
        if args.mode == "examples":
            mapping = {"request.json": "request", "source.json": "source",
                       "response-ok.json": "response", "response-no-results.json": "response",
                       "response-low-relevance.json": "response", "response-error.json": "response"}
            for name, kind in mapping.items():
                validate(kind, read_json(CONTRACTS / "examples" / name))
            report.update(examples_checked=len(mapping), passed=True)
        else:
            cases = load_cases(args.split)
            if not cases:
                raise ContractError("empty_evaluation_set")
            sources = collect_live_sources(args.api_base_url, cases) if args.api_base_url else load_sources()
            for case in cases:
                verify_case_sources(case, sources)
            report.update(dataset_version=sources["dataset_version"], case_count=len(cases),
                          source_verified_cases=len(cases), live_source_checked=bool(args.api_base_url),
                          annotation_status="source_verified_pending_team_review")
            if args.mode == "sources":
                report["passed"] = True
            else:
                if not args.rag_base_url or not args.api_base_url:
                    raise ContractError("search_requires_rag_and_source_urls")
                results = []
                report["results"] = results
                report["search_attempts"] = 0
                with httpx.Client(base_url=args.rag_base_url.rstrip("/"), timeout=60) as client:
                    for case in cases:
                        request = {"request_id": case["case_id"], "original_question": case["query"],
                                   "query": case["query"], "filters": {}, "required_conditions": [],
                                   "preferences": [], "top_k": 10}
                        validate("request", request)
                        report["search_executed"] = True
                        report["search_attempts"] += 1
                        try:
                            result = client.post("/v1/rag/search", json=request)
                            result.raise_for_status()
                            response = result.json()
                        except (httpx.HTTPError, ValueError):
                            failure = evaluate_response(case, {}, sources)
                            failure["error_code"] = "search_transport_failed"
                            results.append(failure)
                            raise ContractError("search_transport_failed") from None
                        try:
                            validate("response", response)
                        except ContractError:
                            results.append(evaluate_response(case, response, sources))
                            continue
                        # Returned candidates may be outside the ten fixture products.
                        response_cases = [{"dataset_version": case["dataset_version"], "relevant": [
                            {"category": item["category"], "product_id": item["product_id"]}]} for item in response.get("items", [])]
                        actual_sources = collect_live_sources(args.api_base_url, response_cases) if response_cases else sources
                        results.append(evaluate_response(case, response, {"dataset_version": sources["dataset_version"],
                            "records": sources["records"] + actual_sources["records"]}))
                report["passed"] = all(r["passed"] for r in results)
    except (ContractError, httpx.HTTPError, OSError, ValueError, KeyError, TypeError) as error:
        report["error_code"] = str(error) if isinstance(error, ContractError) else "validation_execution_failed"
    if "results" in report:
        results = report["results"]
        report.update(product_hits=sum(r["product_hit"] for r in results),
                      source_hits=sum(r["source_hit"] for r in results),
                      invalid_evidence=sum(r["invalid_evidence"] for r in results))
    encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

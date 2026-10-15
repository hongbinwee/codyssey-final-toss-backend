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
import sys

sys.path.insert(0, str(ROOT / "src"))
from toss_ads.rag.source import without_user_ids

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
    """Apply the same privacy transform used before content reaches the index."""
    return without_user_ids(value)


def validate(kind: str, payload: dict) -> None:
    if kind not in {"request", "response", "source"}:
        raise ContractError("unknown_contract")
    contract_root = CONTRACTS
    if kind == "response" and isinstance(payload, dict) and (
        "supported_categories" in payload or payload.get("error_code") == "unsupported_category"
    ):
        # The current service emits the proposed v0.2 category-support fields;
        # keep the v0.1 contract strict for responses that use the original shape.
        contract_root = CONTRACTS.parent / "v0.2"
    schema = read_json(contract_root / f"{kind}.schema.json")
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


def load_cases(split: str = "all", *, category: str | None = None) -> list[dict]:
    cases = read_json(ROOT / "evals/amazon_reviews_rag_cases.json")["cases"]
    selected = [case for case in cases if split == "all" or case["split"] == split]
    if category is None:
        return selected
    return [
        case
        for case in selected
        if category in {
            item.get("category")
            for item in case.get("relevant", []) + case.get("excluded_products", [])
        }
    ]


def load_sources() -> dict:
    return read_json(ROOT / "evals/fixtures/amazon_reviews_rag_sources.json")


def source_field(payload: dict, path: str) -> str:
    """Resolve a JSON Pointer, with the original bracket notation as a migration aid."""
    if isinstance(path, str) and path.startswith("/"):
        value: Any = payload
        for escaped in path[1:].split("/"):
            if re.search(r"~(?![01])", escaped):
                raise ContractError("invalid_source_field")
            token = escaped.replace("~1", "/").replace("~0", "~")
            try:
                if isinstance(value, list):
                    if not re.fullmatch(r"0|[1-9][0-9]*", token):
                        raise ValueError
                    value = value[int(token)]
                elif isinstance(value, dict):
                    value = value[token]
                else:
                    raise ValueError
            except (IndexError, KeyError, TypeError, ValueError):
                raise ContractError("source_field_missing") from None
        if value is None:
            raise ContractError("source_field_missing")
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
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
    evaluation_role = case.get("evaluation_role", "relevance")
    result = {"case_id": case["case_id"], "evaluation_role": evaluation_role,
              "status": response.get("status") if isinstance(response, dict) else None,
              "contract_valid": False, "status_match": False, "product_hit": False,
              "source_hit": False, "relevance_scored": evaluation_role == "relevance",
              "evidence_checked": 0, "invalid_evidence": 0, "passed": False}
    if evaluation_role == "policy_exclusion":
        result.update(policy_exclusion_pass=False, excluded_products_absent=False,
                      excluded_product_returned=False)
    try:
        if evaluation_role not in {"relevance", "policy_exclusion"}:
            raise ContractError("unknown_evaluation_role")
        excluded_products = case.get("excluded_products", [])
        if evaluation_role == "policy_exclusion" and (not excluded_products or any(
                not isinstance(product, dict) or not isinstance(product.get("category"), str)
                or not isinstance(product.get("product_id"), str)
                for product in excluded_products)):
            raise ContractError("invalid_policy_exclusion")
        validate("response", response)
        if response["status"] == "error":
            result["contract_valid"] = True
            result["error_code"] = response["error_code"]
            return result
        verify_case_sources(case, sources)
        if response["dataset_version"] != case["dataset_version"]:
            raise ContractError("response_version_mismatch")
    except ContractError as error:
        result["error_code"] = str(error)
        return result
    result["contract_valid"] = True
    result["status_match"] = (
        response["status"] == case["expected_status"]
        if evaluation_role == "relevance" else None
    )
    if evaluation_role == "policy_exclusion":
        excluded = {(product["category"], product["product_id"]) for product in excluded_products}
        returned = {(item["category"], item["product_id"]) for item in response["items"]}
        result["excluded_product_returned"] = bool(excluded & returned)
        result["excluded_products_absent"] = not result["excluded_product_returned"]
    for item in response["items"]:
        matching = [label for label in case["relevant"]
                    if (label["category"], label["product_id"]) == (item["category"], item["product_id"])]
        if evaluation_role == "relevance":
            result["product_hit"] |= bool(matching)
        for evidence in item["evidence"]:
            result["evidence_checked"] += 1
            try:
                verify_evidence(item, evidence, sources)
            except ContractError:
                result["invalid_evidence"] += 1
                continue
            if evaluation_role == "policy_exclusion":
                continue
            for label in matching:
                if (evidence["source_type"], evidence["source_id"], evidence["source_field"]) == (
                        label["source_type"], label["source_id"], label["source_field"]):
                    if evidence["start_offset"] <= label["start_offset"] and evidence["end_offset"] >= label["end_offset"]:
                        result["source_hit"] = True
    if evaluation_role == "policy_exclusion":
        result["policy_exclusion_pass"] = bool(
            response["status"] != "error"
            and result["excluded_products_absent"]
            and not result["invalid_evidence"]
        )
        result["passed"] = result["policy_exclusion_pass"]
    else:
        relevant_ok = not case["relevant"] or (result["product_hit"] and result["source_hit"])
        result["passed"] = bool(result["status_match"] and relevant_ok and not result["invalid_evidence"])
    return result


def summarize_results(results: list[dict]) -> dict:
    """Keep policy compliance checks outside relevance hit-rate denominators."""
    relevance = [result for result in results if result.get("evaluation_role", "relevance") == "relevance"]
    policy = [result for result in results if result.get("evaluation_role") == "policy_exclusion"]
    return {
        "relevance_case_count": len(relevance),
        "product_hits": sum(result["product_hit"] for result in relevance),
        "source_hits": sum(result["source_hit"] for result in relevance),
        "relevance_passes": sum(result["passed"] for result in relevance),
        "search_retries": sum(result.get("retry_count", 0) for result in results),
        "retried_search_cases": sum(result.get("retry_count", 0) > 0 for result in results),
        "policy_exclusion_case_count": len(policy),
        "policy_exclusion_passes": sum(result.get("policy_exclusion_pass", False) for result in policy),
        "policy_exclusion_failures": sum(not result.get("policy_exclusion_pass", False) for result in policy),
        "invalid_evidence": sum(result["invalid_evidence"] for result in results),
    }


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
    parser.add_argument("--category", help="limit search evaluation to cases labeled for this indexed category")
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
            all_split_cases = load_cases(args.split)
            cases = load_cases(args.split, category=args.category)
            if not cases:
                raise ContractError("empty_evaluation_set")
            sources = collect_live_sources(args.api_base_url, cases) if args.api_base_url else load_sources()
            for case in cases:
                verify_case_sources(case, sources)
            report.update(dataset_version=sources["dataset_version"], case_count=len(cases),
                          source_verified_cases=len(cases), live_source_checked=bool(args.api_base_url),
                          annotation_status="source_verified_pending_team_review")
            if args.category is not None:
                in_scope_ids = {case["case_id"] for case in cases}
                report["category_scope"] = args.category
                report["out_of_scope_case_count"] = len(all_split_cases) - len(cases)
                report["out_of_scope_case_ids"] = [
                    case["case_id"] for case in all_split_cases
                    if case["case_id"] not in in_scope_ids
                ]
            if args.mode == "sources":
                report["passed"] = True
            else:
                if not args.rag_base_url or not args.api_base_url:
                    raise ContractError("search_requires_rag_and_source_urls")
                results = []
                report["results"] = results
                report["search_attempts"] = 0
                report["retry_policy"] = {
                    "max_retries": 1,
                    "retryable_error_codes": ["database_failed", "timeout"],
                    "transport_failures_retried": False,
                }
                with httpx.Client(base_url=args.rag_base_url.rstrip("/"), timeout=60) as client:
                    for case in cases:
                        request = {"request_id": case["case_id"], "original_question": case["query"],
                                   "query": case["query"], "filters": {}, "required_conditions": [],
                                   "preferences": [], "top_k": 10}
                        validate("request", request)
                        report["search_executed"] = True
                        retry_error_codes: list[str] = []

                        def append_result(outcome: dict) -> None:
                            outcome["retry_count"] = len(retry_error_codes)
                            outcome["retry_error_codes"] = list(retry_error_codes)
                            results.append(outcome)

                        for retry_index in range(2):
                            report["search_attempts"] += 1
                            try:
                                result = client.post("/v1/rag/search", json=request)
                                response = result.json()
                            except httpx.HTTPError:
                                failure = evaluate_response(case, {}, sources)
                                failure["error_code"] = "search_transport_failed"
                                append_result(failure)
                                raise ContractError("search_transport_failed") from None
                            except ValueError:
                                failure = evaluate_response(case, {}, sources)
                                failure["error_code"] = "search_response_invalid"
                                append_result(failure)
                                raise ContractError("search_response_invalid") from None
                            try:
                                validate("response", response)
                            except ContractError:
                                append_result(evaluate_response(case, response, sources))
                                break
                            if response["status"] == "error":
                                if (
                                    response["error_code"] in {"database_failed", "timeout"}
                                    and retry_index == 0
                                ):
                                    retry_error_codes.append(response["error_code"])
                                    continue
                                append_result(evaluate_response(case, response, sources))
                                break
                            if result.status_code >= 400:
                                failure = evaluate_response(case, response, sources)
                                failure["passed"] = False
                                failure["error_code"] = "http_status_response_mismatch"
                                append_result(failure)
                                break
                            # Returned candidates may be outside the ten fixture products.
                            response_cases = [{"dataset_version": case["dataset_version"], "relevant": [
                                {"category": item["category"], "product_id": item["product_id"]}]} for item in response.get("items", [])]
                            actual_sources = collect_live_sources(args.api_base_url, response_cases) if response_cases else sources
                            append_result(evaluate_response(case, response, {"dataset_version": sources["dataset_version"],
                                "records": sources["records"] + actual_sources["records"]}))
                            break
                report["passed"] = all(r["passed"] for r in results)
    except (ContractError, httpx.HTTPError, OSError, ValueError, KeyError, TypeError) as error:
        report["error_code"] = str(error) if isinstance(error, ContractError) else "validation_execution_failed"
    if "results" in report:
        report.update(summarize_results(report["results"]))
    encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Consumer-visible contract and evidence integrity checks."""
from __future__ import annotations

import copy
import contextlib
import importlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import httpx


ROOT = Path(__file__).resolve().parents[1]


class RagContractTests(unittest.TestCase):
    def validator(self):
        try:
            return importlib.import_module("scripts.rag_contracts")
        except ModuleNotFoundError:
            self.fail("RAG contract validator is not implemented")

    def example(self, name):
        return json.loads((ROOT / "contracts/amazon-reviews-rag/v0.1/examples" / name).read_text())

    def test_complete_examples_conform_to_the_shared_contract(self):
        validator = self.validator()
        for name, kind in [("request.json", "request"), ("source.json", "source"),
                           ("response-ok.json", "response"), ("response-no-results.json", "response"),
                           ("response-low-relevance.json", "response"), ("response-error.json", "response")]:
            with self.subTest(name=name):
                validator.validate(kind, self.example(name))

    def test_request_rejects_blank_query_boolean_top_k_and_bad_price_range(self):
        validator = self.validator()
        for change in [{"query": "   "}, {"top_k": True}, {"top_k": 0},
                       {"filters": {"price_min": 2, "price_max": 1, "currency": "USD"}},
                       {"filters": {"price_max": 100}}, {"filters": {"currency": "한글자"}}]:
            payload = self.example("request.json")
            payload.update(change)
            with self.subTest(change=change), self.assertRaises(validator.ContractError):
                validator.validate("request", payload)

    def test_response_rejects_wrong_product_version_and_offset(self):
        validator = self.validator()
        for field, value in [("product_id", "other-product"), ("source_version", "stale-version"),
                             ("end_offset", 1), ("source_id", "not-a-review-key")]:
            payload = self.example("response-ok.json")
            payload["items"][0]["evidence"][0][field] = value
            with self.subTest(field=field), self.assertRaises(validator.ContractError):
                validator.validate("response", payload)

    def test_response_rejects_error_with_items_or_ok_without_evidence(self):
        validator = self.validator()
        for status, error_code in [("error", "database_failed"), ("no_results", None), ("low_relevance", None)]:
            payload = self.example("response-ok.json")
            payload.update(status=status, error_code=error_code)
            with self.subTest(status=status), self.assertRaises(validator.ContractError):
                validator.validate("response", payload)
        payload = self.example("response-ok.json")
        payload["items"][0]["evidence"] = []
        with self.assertRaises(validator.ContractError):
            validator.validate("response", payload)

    def test_source_rejects_review_attached_to_a_different_product(self):
        validator = self.validator()
        payload = self.example("source.json")
        payload["review"]["parent_asin"] = "other-product"
        with self.assertRaises(validator.ContractError):
            validator.validate("source", payload)

    def test_identifiers_are_not_leaked_in_nested_payloads(self):
        validator = self.validator()
        payload = self.example("response-ok.json")
        payload["items"][0]["product_metadata"]["nested"] = {"user_id": "private"}
        with self.assertRaises(validator.ContractError):
            validator.validate("response", payload)

    def test_source_normalization_removes_nested_video_user_ids_without_changing_text(self):
        validator = self.validator()
        original = {"title": "  Exact original text  ", "videos": [{"user_id": "private", "url": "https://example.test/video"}]}
        clean = validator.normalize_source(original)
        self.assertEqual(clean, {"title": "  Exact original text  ", "videos": [{"url": "https://example.test/video"}]})
        self.assertEqual(original["videos"][0]["user_id"], "private")

    def test_unknown_response_fields_and_nonfinite_score_are_rejected(self):
        validator = self.validator()
        payload = self.example("response-ok.json")
        payload["confidence"] = 0.9
        with self.assertRaises(validator.ContractError):
            validator.validate("response", payload)
        payload = self.example("response-ok.json")
        payload["items"][0]["rrf_score"] = float("nan")
        with self.assertRaises(validator.ContractError):
            validator.validate("response", payload)

    def test_fixture_labels_are_grounded_and_holdout_products_are_disjoint(self):
        validator = self.validator()
        cases = validator.load_cases()
        sources = validator.load_sources()
        self.assertEqual(len(cases), 20)
        splits = {"tuning": set(), "holdout": set()}
        for case in cases:
            validator.verify_case_sources(case, sources)
            self.assertEqual(case["annotation_status"], "source_verified_pending_team_review")
            splits[case["split"]].add((case["relevant"][0]["category"], case["relevant"][0]["product_id"]))
        self.assertTrue(splits["tuning"])
        self.assertTrue(splits["holdout"])
        self.assertFalse(splits["tuning"] & splits["holdout"])

    def test_public_source_fixture_excludes_profiles_and_user_media(self):
        validator = self.validator()
        forbidden = {"user_id", "author", "images", "videos"}

        def check(value):
            if isinstance(value, dict):
                self.assertTrue(forbidden.isdisjoint(value))
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)

        check(validator.load_sources())

    def test_a_changed_source_sentence_fails_provenance_validation(self):
        validator = self.validator()
        case = copy.deepcopy(validator.load_cases()[0])
        case["relevant"][0]["evidence_text"] = "invented evidence"
        with self.assertRaises(validator.ContractError):
            validator.verify_case_sources(case, validator.load_sources())

    def test_evaluation_counts_exact_source_hits_and_fails_on_wrong_evidence(self):
        validator = self.validator()
        case = validator.load_cases()[0]
        response = self.example("response-ok.json")
        result = validator.evaluate_response(case, response, validator.load_sources())
        self.assertTrue(result["product_hit"])
        self.assertTrue(result["source_hit"])
        self.assertTrue(result["passed"])
        response["items"][0]["evidence"][0]["evidence_text"] = "X" * 171
        result = validator.evaluate_response(case, response, validator.load_sources())
        self.assertFalse(result["passed"])
        self.assertEqual(result["invalid_evidence"], 1)

    def test_evaluation_reports_a_missed_source_as_a_failure(self):
        validator = self.validator()
        response = self.example("response-no-results.json")
        case = validator.load_cases()[0]
        result = validator.evaluate_response(case, response, validator.load_sources())
        self.assertFalse(result["passed"])
        self.assertFalse(result["product_hit"])
        self.assertFalse(result["source_hit"])

    def test_response_rejects_duplicate_products_and_misnumbered_final_rank(self):
        validator = self.validator()
        response = self.example("response-ok.json")
        response["items"].append(copy.deepcopy(response["items"][0]))
        with self.assertRaises(validator.ContractError):
            validator.validate("response", response)
        response = self.example("response-ok.json")
        response["items"][0]["evidence"][0]["rrf_rank"] = 2
        with self.assertRaises(validator.ContractError):
            validator.validate("response", response)

    def test_live_source_collection_checks_page_version_completeness_and_review_links(self):
        validator = self.validator()
        fixture = validator.load_sources()
        case = validator.load_cases()[0]
        product, reviews = fixture["records"][0]["product"], fixture["records"][0]["reviews"]
        version = fixture["dataset_version"]

        def transport(variation):
            def handle(request):
                if request.url.path == "/healthz":
                    payload = {"status": "ok", "dataset_version": version}
                elif "/products/" in request.url.path:
                    payload = copy.deepcopy(product)
                    payload["videos"] = [{"user_id": "private", "title": "original"}]
                else:
                    payload = {"dataset_version": version, "items": copy.deepcopy(reviews),
                               "offset": 0, "limit": 200, "total": len(reviews)}
                    if variation == "changed_version":
                        payload["dataset_version"] = "changed-version"
                    elif variation == "incomplete_page":
                        payload["total"] += 1
                    elif variation == "foreign_review":
                        payload["items"][0]["parent_asin"] = "other-product"
                return httpx.Response(200, json=payload)
            return httpx.MockTransport(handle)

        sources = validator.collect_live_sources("https://source.test", [case], transport=transport("valid"))
        self.assertEqual(validator.verify_case_sources(case, sources), 1)
        self.assertEqual(sources["records"][0]["product"]["videos"], [{"title": "original"}])
        for failure in ("changed_version", "incomplete_page", "foreign_review"):
            with self.subTest(failure=failure), self.assertRaises(validator.ContractError):
                validator.collect_live_sources("https://source.test", [case], transport=transport(failure))

    def test_source_field_resolution_handles_quoted_keys_without_executing_paths(self):
        validator = self.validator()
        payload = {"details": {"Item [model]": "EL-USB-RT", "Count": 4}}
        self.assertEqual(validator.source_field(payload, 'details["Item [model]"]'), "EL-USB-RT")
        self.assertEqual(validator.source_field(payload, 'details["Count"]'), "4")
        with self.assertRaises(validator.ContractError):
            validator.source_field(payload, '__import__("os").system("anything")')

    def test_changed_product_price_review_rating_and_invented_metadata_fail(self):
        validator = self.validator()
        for target, key, value in [("product", "price", 0.01), ("review", "rating", 5),
                                   ("product", "title", "Another product"),
                                   ("review", "invented_attribute", "fiction")]:
            response = self.example("response-ok.json")
            if target == "product":
                response["items"][0]["product_metadata"][key] = value
            else:
                response["items"][0]["evidence"][0]["source_metadata"][key] = value
            result = validator.evaluate_response(validator.load_cases()[0], response, validator.load_sources())
            with self.subTest(target=target, key=key):
                self.assertFalse(result["passed"])
                self.assertEqual(result["invalid_evidence"], 1)

    def test_overlapping_review_pages_cannot_hide_a_missing_review(self):
        validator = self.validator()
        sources = validator.load_sources()
        record = sources["records"][0]
        version = sources["dataset_version"]
        reviews = [dict(record["reviews"][0], review_key=f"{i:064x}") for i in range(200)]
        reviews[0] = record["reviews"][0]
        def handle(request):
            if request.url.path == "/healthz":
                data = {"status": "ok", "dataset_version": version}
            elif "/products/" in request.url.path:
                data = record["product"]
            else:
                offset = int(request.url.params["offset"])
                data = {"dataset_version": version, "items": reviews if offset == 0 else [reviews[0]],
                        "total": 201, "offset": offset, "limit": 200}
            return httpx.Response(200, json=data)
        with self.assertRaises(validator.ContractError):
            validator.collect_live_sources("https://source.test", [validator.load_cases()[0]],
                                           transport=httpx.MockTransport(handle))

    def run_search_cli(self, *, fail_at=None, malformed=False, transport_fail_at=None,
                       transient_fail_at=None):
        validator = self.validator()
        fixture = validator.load_sources()
        records = {row["product"]["parent_asin"]: row for row in fixture["records"]}
        response = self.example("response-ok.json")
        attempted = 0
        def handle(request):
            nonlocal attempted
            if request.url.host == "rag.test":
                attempted += 1
                if attempted == transport_fail_at:
                    raise httpx.ConnectError("offline")
                if attempted == fail_at:
                    error = self.example("response-error.json")
                    error["request_id"] = json.loads(request.content)["request_id"]
                    return httpx.Response(503, json=error)
                if attempted == transient_fail_at:
                    error = self.example("response-error.json")
                    error["request_id"] = json.loads(request.content)["request_id"]
                    error["error_code"] = "database_failed"
                    return httpx.Response(503, json=error)
                result = copy.deepcopy(response)
                result["request_id"] = json.loads(request.content)["request_id"]
                return httpx.Response(200, json=[] if malformed else result)
            if request.url.path == "/healthz":
                data = {"status": "ok", "dataset_version": fixture["dataset_version"]}
            elif "/products/" in request.url.path:
                data = records[request.url.path.rsplit("/", 1)[-1]]["product"]
            else:
                reviews = records[request.url.params["parent_asin"]]["reviews"]
                data = {"dataset_version": fixture["dataset_version"], "items": reviews,
                        "total": len(reviews), "offset": 0, "limit": 200}
            return httpx.Response(200, json=data)
        real_client = httpx.Client
        def client_factory(*args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handle)
            return real_client(*args, **kwargs)
        output = io.StringIO()
        with patch.object(validator.httpx, "Client", client_factory), contextlib.redirect_stdout(output):
            code = validator.main(["--mode", "search", "--split", "holdout",
                                   "--api-base-url", "https://source.test", "--rag-base-url", "https://rag.test"])
        return code, json.loads(output.getvalue())

    def test_http_ok_with_genuine_but_irrelevant_source_fails_search_quality(self):
        code, report = self.run_search_cli()
        self.assertEqual(code, 1)
        self.assertTrue(report["search_executed"])
        self.assertEqual(report["product_hits"], 0)
        self.assertEqual(report["source_hits"], 0)
        self.assertEqual(report["invalid_evidence"], 0)
        self.assertEqual(len(report["results"]), 8)

    def test_search_execution_errors_keep_the_error_code_and_do_not_skip_later_cases(self):
        for fail_at in (1, 2):
            code, report = self.run_search_cli(fail_at=fail_at)
            with self.subTest(fail_at=fail_at):
                self.assertEqual(code, 1)
                self.assertTrue(report["search_executed"])
                self.assertEqual(report["search_attempts"], 8)
                self.assertEqual(len(report["results"]), 8)
                error = report["results"][fail_at - 1]
                self.assertTrue(error["contract_valid"])
                self.assertEqual(error["status"], "error")
                self.assertEqual(error["error_code"], "index_not_ready")

    def test_transport_failure_is_distinct_and_completed_cases_are_preserved(self):
        code, report = self.run_search_cli(transport_fail_at=2)
        self.assertEqual(code, 1)
        self.assertEqual(report["search_attempts"], 2)
        self.assertEqual(len(report["results"]), 2)
        self.assertEqual(report["results"][-1]["error_code"], "search_transport_failed")

    def test_transient_database_error_is_retried_and_recorded(self):
        code, report = self.run_search_cli(transient_fail_at=2)
        self.assertEqual(code, 1)
        self.assertEqual(report["search_attempts"], 9)
        self.assertEqual(len(report["results"]), 8)
        self.assertEqual(report["results"][1]["retry_count"], 1)
        self.assertEqual(report["results"][1]["retry_error_codes"], ["database_failed"])
        self.assertEqual(report["search_retries"], 1)

    def test_malformed_search_json_root_is_reported_without_traceback(self):
        code, report = self.run_search_cli(malformed=True)
        self.assertEqual(code, 1)
        self.assertFalse(report["passed"])
        self.assertFalse(report["results"][0]["contract_valid"])


if __name__ == "__main__":
    unittest.main()

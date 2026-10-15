"""Evaluation behavior for relevance labels and category policy exclusions."""
from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RagEvaluationRoleTests(unittest.TestCase):
    def validator(self):
        try:
            return importlib.import_module("scripts.rag_contracts")
        except ModuleNotFoundError:
            self.fail("RAG contract validator is not implemented")

    def policy_case(self):
        validator = self.validator()
        case = copy.deepcopy(next(c for c in validator.load_cases() if c["case_id"] == "RAG-017"))
        label = case["relevant"][0]
        case["evaluation_role"] = "policy_exclusion"
        case["excluded_products"] = [{"category": label["category"], "product_id": label["product_id"]}]
        return case

    def test_load_cases_can_limit_search_evaluation_to_indexed_category(self):
        validator = self.validator()

        tuning = validator.load_cases("tuning", category="Appliances")
        holdout = validator.load_cases("holdout", category="Appliances")

        self.assertEqual([case["case_id"] for case in tuning], [
            "RAG-001", "RAG-002", "RAG-003", "RAG-004"
        ])
        self.assertEqual([case["case_id"] for case in holdout], [
            "RAG-005", "RAG-006", "RAG-007", "RAG-008"
        ])

    def no_results(self, case):
        return {
            "request_id": case["case_id"],
            "status": "no_results",
            "dataset_version": case["dataset_version"],
            "applied_filters": {},
            "unverified_conditions": [],
            "items": [],
            "error_code": None,
        }

    def excluded_product_response(self, case):
        label = case["relevant"][0]
        return {
            "request_id": case["case_id"],
            "status": "ok",
            "dataset_version": case["dataset_version"],
            "applied_filters": {},
            "unverified_conditions": [],
            "items": [{
                "product_id": label["product_id"],
                "category": label["category"],
                "product_metadata": {},
                "rrf_score": 0.01,
                "evidence": [{
                    "product_id": label["product_id"],
                    "chunk_id": "a" * 64,
                    "source_type": label["source_type"],
                    "source_id": label["source_id"],
                    "source_field": label["source_field"],
                    "source_version": case["dataset_version"],
                    "evidence_text": label["evidence_text"],
                    "source_metadata": {},
                    "start_offset": label["start_offset"],
                    "end_offset": label["end_offset"],
                    "bm25_rank": 1,
                    "vector_rank": 1,
                    "rrf_rank": 1,
                }],
            }],
            "error_code": None,
        }

    def test_policy_exclusion_passes_when_excluded_product_is_absent(self):
        validator = self.validator()
        case = self.policy_case()

        result = validator.evaluate_response(case, self.no_results(case), validator.load_sources())

        self.assertTrue(result["passed"])
        self.assertTrue(result["policy_exclusion_pass"])
        self.assertFalse(result["relevance_scored"])
        self.assertEqual(result["invalid_evidence"], 0)

    def test_live_search_v02_response_matches_the_service_contract(self):
        validator = self.validator()
        for path in sorted((ROOT / "contracts/amazon-reviews-rag/v0.2/examples").glob("response*.json")):
            with self.subTest(example=path.name):
                response = json.loads(path.read_text())
                validator.validate("response", response)

    def test_policy_exclusion_fails_if_excluded_product_is_returned(self):
        validator = self.validator()
        case = self.policy_case()

        result = validator.evaluate_response(case, self.excluded_product_response(case), validator.load_sources())

        self.assertFalse(result["passed"])
        self.assertFalse(result["policy_exclusion_pass"])
        self.assertTrue(result["excluded_product_returned"])
        self.assertEqual(result["invalid_evidence"], 0)

    def test_policy_exclusion_fails_when_returned_evidence_is_not_from_source(self):
        validator = self.validator()
        case = self.policy_case()
        response = self.excluded_product_response(case)
        original_text = response["items"][0]["evidence"][0]["evidence_text"]
        response["items"][0]["evidence"][0]["evidence_text"] = "X" * len(original_text)

        result = validator.evaluate_response(case, response, validator.load_sources())

        self.assertFalse(result["passed"])
        self.assertEqual(result["invalid_evidence"], 1)

    def test_policy_cases_do_not_inflate_relevance_hit_metrics(self):
        validator = self.validator()
        sources = validator.load_sources()
        relevance_case = validator.load_cases()[0]
        relevance_response = json.loads(
            (ROOT / "contracts/amazon-reviews-rag/v0.1/examples/response-ok.json").read_text()
        )
        relevance_result = validator.evaluate_response(relevance_case, relevance_response, sources)
        policy_case = self.policy_case()
        policy_result = validator.evaluate_response(policy_case, self.no_results(policy_case), sources)

        summary = validator.summarize_results([relevance_result, policy_result])

        self.assertEqual(summary["relevance_case_count"], 1)
        self.assertEqual(summary["product_hits"], 1)
        self.assertEqual(summary["source_hits"], 1)
        self.assertEqual(summary["policy_exclusion_case_count"], 1)
        self.assertEqual(summary["policy_exclusion_passes"], 1)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

import psycopg
from fastapi.testclient import TestClient

from toss_ads.rag.api import create_app
from toss_ads.rag.config import Settings


class FailedStore:
    def active_run(self):
        raise psycopg.OperationalError("private connection detail")


class RagApiErrorTests(unittest.TestCase):
    def test_database_errors_return_safe_code_and_log_only_error_class(self):
        app = create_app(
            Settings("http://source", "postgresql://db"),
            store=FailedStore(),
            embedder=object(),
        )
        request = {
            "request_id": "api-error-test",
            "original_question": "question",
            "query": "question",
        }

        with self.assertLogs("toss_ads.rag", level="WARNING") as captured:
            with TestClient(app) as client:
                response = client.post("/v1/rag/search", json=request)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error_code"], "database_failed")
        self.assertIn("OperationalError", captured.output[0])
        self.assertNotIn("private connection detail", captured.output[0])


if __name__ == "__main__":
    unittest.main()

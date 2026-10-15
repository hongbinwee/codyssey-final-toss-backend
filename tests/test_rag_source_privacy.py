"""Privacy filtering for the read-only source API and indexed evidence."""
from __future__ import annotations

from collections import Counter
import unittest

from toss_ads.rag.source import without_user_ids


class RagSourcePrivacyTests(unittest.TestCase):
    def test_explicit_contacts_are_masked_in_place_and_private_keys_removed(self):
        text = "Call me at (212) 555-1212 or email alex@example.test; SSN 123-45-6789."
        source = {
            "user_id": "private-user",
            "user_email": "alex@example.test",
            "review": {"text": text},
        }
        counts = Counter()

        clean = without_user_ids(source, counts)

        self.assertNotIn("user_id", clean)
        self.assertNotIn("user_email", clean)
        self.assertEqual(len(clean["review"]["text"]), len(text))
        self.assertNotIn("(212) 555-1212", clean["review"]["text"])
        self.assertNotIn("alex@example.test", clean["review"]["text"])
        self.assertNotIn("123-45-6789", clean["review"]["text"])
        self.assertEqual(counts["phone"], 1)
        self.assertEqual(counts["email"], 1)
        self.assertEqual(counts["ssn"], 1)
        self.assertEqual(counts["private_fields_removed"], 2)

    def test_hashes_and_unlabeled_model_numbers_are_not_masked(self):
        source = {
            "review_key": "9f621255551212abcdef0123456789abcdef0123456789abcdef0123456789",
            "details": {"item model number": "800-555-1212"},
            "text": "This phone accessory lists model number 800-555-1212.",
            "nearby_context": "Call me at 212-555-1212. The model number is 800-555-1212.",
        }
        counts = Counter()

        clean = without_user_ids(source, counts)

        self.assertEqual(clean["review_key"], source["review_key"])
        self.assertEqual(clean["details"], source["details"])
        self.assertEqual(clean["text"], source["text"])
        self.assertNotIn("212-555-1212", clean["nearby_context"])
        self.assertIn("800-555-1212", clean["nearby_context"])
        self.assertEqual(counts["phone"], 1)


if __name__ == "__main__":
    unittest.main()

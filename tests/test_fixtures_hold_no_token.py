"""Recorded fixtures are committed, so they must never hold a TMDB token."""

import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.tmdb_key import tmdb_read_key  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# TMDB read tokens are JWTs: base64url header "eyJ...", then ".", then the payload.
TOKEN_LIKE = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.|Bearer|Authorization", re.IGNORECASE)


def leaks(text, key):
    """What in a fixture's text looks like a token, if anything."""
    if key and key in text:
        return "the TMDB read token"
    match = TOKEN_LIKE.search(text)
    return match.group(0)[:12] + "..." if match else None


class FixturesHoldNoTokenTest(unittest.TestCase):
    def test_no_fixture_holds_a_token(self):
        key = tmdb_read_key()
        files = sorted(path for path in FIXTURES.rglob("*") if path.is_file())

        self.assertTrue(files, "no fixtures found")
        for path in files:
            with self.subTest(fixture=str(path.relative_to(FIXTURES))):
                self.assertIsNone(leaks(path.read_text(), key))

    def test_a_token_in_a_fixture_is_caught(self):
        self.assertEqual(leaks('{"name": "abc-secret-xyz"}', "abc-secret-xyz"), "the TMDB read token")
        self.assertIsNotNone(leaks('{"auth": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig"}', None))
        self.assertIsNone(leaks('{"name": "DreamWorks Dragons"}', None))


if __name__ == "__main__":
    unittest.main()

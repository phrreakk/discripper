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


def token_found_in(text, key):
    """Describe the token found in a fixture's text, without repeating it; None if there's none."""
    if key and key in text:
        return "the TMDB read token"
    if TOKEN_LIKE.search(text):
        return "something token-like (a JWT, Bearer or Authorization)"
    return None


class FixturesHoldNoTokenTest(unittest.TestCase):
    def test_no_fixture_holds_a_token(self):
        key = tmdb_read_key()
        files = sorted(path for path in FIXTURES.rglob("*") if path.is_file())

        self.assertTrue(files, "no fixtures found")
        for path in files:
            with self.subTest(fixture=str(path.relative_to(FIXTURES))):
                self.assertIsNone(token_found_in(path.read_text(), key))

    def test_the_read_token_itself_is_caught(self):
        self.assertEqual(token_found_in('{"name": "abc-secret-xyz"}', "abc-secret-xyz"), "the TMDB read token")

    def test_a_jwt_shaped_string_is_caught_without_a_token_to_compare(self):
        self.assertIsNotNone(token_found_in('{"auth": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig"}', None))

    def test_ordinary_metadata_passes(self):
        self.assertIsNone(token_found_in('{"name": "DreamWorks Dragons"}', None))


if __name__ == "__main__":
    unittest.main()

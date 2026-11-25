import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import discripper  # noqa: E402


class TmdbKeyTest(unittest.TestCase):
    def setUp(self):
        self.env = Path(self.enterContext(tempfile.TemporaryDirectory())) / ".env"

    def missing(self):
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as exit:
            discripper.tmdbKey(self.env)
        self.assertEqual(exit.exception.code, 1)
        return out.getvalue()

    def test_the_key_comes_from_the_env_file(self):
        self.env.write_text("TMDB_API_KEY=abc123\n", encoding="utf-8")

        self.assertEqual(discripper.tmdbKey(self.env), "abc123")

    def test_a_missing_env_file_exits_with_how_to_fix_it(self):
        printed = self.missing()

        self.assertIn("TMDB_API_KEY", printed)
        self.assertIn(str(self.env), printed)

    def test_a_misnamed_or_blank_key_exits_too(self):
        for text in ["TMDB_KEY=abc123\n", "TMDB_API_KEY=\n"]:
            with self.subTest(text=text):
                self.env.write_text(text, encoding="utf-8")

                self.assertIn("TMDB_API_KEY", self.missing())


if __name__ == "__main__":
    unittest.main()

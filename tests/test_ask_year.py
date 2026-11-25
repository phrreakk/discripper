import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import discripper  # noqa: E402


def ask(typed, kind="movie"):
    """Run askYear with typed answers; return (year, stdout)."""
    out = io.StringIO()
    with mock.patch("builtins.input", side_effect=typed), redirect_stdout(out):
        year = discripper.askYear(kind)
    return year, out.getvalue()


class AskYearTest(unittest.TestCase):
    def test_non_numeric_year_asks_again(self):
        year, out = ask(["2010s", "2010"])
        self.assertEqual(year, "2010")
        self.assertIn("You need a valid year", out)

    def test_blank_answer_skips_the_year(self):
        year, out = ask([""])
        self.assertEqual(year, "")
        self.assertNotIn("You need a valid year", out)

    def test_year_outside_1900_to_this_year_asks_again(self):
        with mock.patch.object(discripper, "datetime") as fake_datetime:
            fake_datetime.today.return_value.year = 2026
            year, out = ask(["1899", "2027", "1900"])
        self.assertEqual(year, "1900")
        self.assertEqual(out.count("You need a valid year"), 2)


if __name__ == "__main__":
    unittest.main()

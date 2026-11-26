import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import discripper  # noqa: E402
from media_lookup import LookupFailed, Media, MediaLookup, Season  # noqa: E402
from tests.test_media_lookup import FakeTmdb  # noqa: E402

DRAGON = {"id": 10191, "original_title": "How to Train Your Dragon",
          "release_date": "2010-03-18", "popularity": 50.0}
FAN_CUT = {"id": 999001, "original_title": "How to Train Your Dragon: Fan Cut", "popularity": 1.25}
DRAGONS_SHOW = {"id": 44305, "original_name": "DreamWorks Dragons",
                "first_air_date": "2012-08-07", "popularity": 40.0}
SEASONS = [{"id": 55501, "name": "Season 1", "season_number": 1, "air_date": "2013-01-01"},
           {"id": 55509, "name": "Specials", "season_number": 0}]


def choose(responses, typed, kind, name="", year="", tmdb_id=None):
    """Run chooseMedia against canned TMDB responses and typed answers; return (result, stdout)."""
    out = io.StringIO()
    with mock.patch("builtins.input", side_effect=typed), redirect_stdout(out):
        found = discripper.chooseMedia(MediaLookup(FakeTmdb(responses)), kind, name, year, tmdb_id)
    return found, out.getvalue()


class ChooseMovieTest(unittest.TestCase):
    def test_lists_movies_with_popularity_and_returns_the_chosen_one(self):
        search = {"total_results": 2, "results": [FAN_CUT, DRAGON]}

        found, printed = choose({"search/movie": search}, ["999001"], "movie", "How to train your dragon")

        self.assertEqual(found, (Media("movie", 999001, "How to Train Your Dragon: Fan Cut", ""), None))
        self.assertIn("How to Train Your Dragon: Fan Cut", printed)
        self.assertIn("1.25", printed)
        self.assertLess(printed.index("50.0"), printed.index("1.25"))

    def test_blank_or_unlisted_id_asks_again(self):
        search = {"total_results": 1, "results": [DRAGON]}

        found, printed = choose({"search/movie": search}, ["", "12345", "10191"], "movie", "Dragon")

        self.assertEqual(found[0].tmdb_id, 10191)
        self.assertIn("You need to input a value from the ID column.", printed)
        self.assertIn("You need to select a valid ID from the table.", printed)


class ChooseShowTest(unittest.TestCase):
    def test_show_search_then_asks_which_season_by_its_number(self):
        responses = {"search/tv": {"total_results": 1, "results": [DRAGONS_SHOW]},
                     "tv/44305": {"seasons": SEASONS}}

        found, printed = choose(responses, ["44305", "0"], "tv", "Dragons")

        self.assertEqual(found, (Media("tv", 44305, "DreamWorks Dragons", "2012"),
                                 Season(55509, 0, "Specials", "")))
        self.assertIn("Specials", printed)

    def test_the_season_table_shows_season_numbers_not_tmdb_ids(self):
        _, printed = choose({"tv/44305": dict(DRAGONS_SHOW, seasons=SEASONS)}, ["1"], "tv",
                            tmdb_id=44305)

        season_table = printed[printed.index("Search season information"):]
        self.assertIn("Season #", season_table)
        self.assertNotIn("55501", season_table)

    def test_a_season_tmdb_id_is_asked_again(self):
        found, printed = choose({"tv/44305": dict(DRAGONS_SHOW, seasons=SEASONS)},
                                ["55509", "", "1"], "tv", tmdb_id=44305)

        self.assertEqual(found[1].number, 1)
        self.assertIn("You need to select a valid Season # from the table.", printed)
        self.assertIn("You need to input a value from the Season # column.", printed)


class ChooseByTmdbIdTest(unittest.TestCase):
    def test_movie_by_tmdb_id_asks_nothing(self):
        found, _ = choose({"movie/10191": DRAGON}, [], "movie", tmdb_id=10191)

        self.assertEqual(found, (Media("movie", 10191, "How to Train Your Dragon", "2010"), None))

    def test_show_by_tmdb_id_reads_show_and_asks_which_season(self):
        show = dict(DRAGONS_SHOW, seasons=SEASONS)

        found, _ = choose({"tv/44305": show}, ["1"], "tv", tmdb_id=44305)

        self.assertEqual(found, (Media("tv", 44305, "DreamWorks Dragons", "2012"),
                                 Season(55501, 1, "Season 1", "2013-01-01")))


class LookupErrorExitTest(unittest.TestCase):
    def setUp(self):
        self.out = io.StringIO()

    def run_choose(self, fetch, year=""):
        with redirect_stdout(self.out), self.assertRaises(SystemExit) as raised:
            discripper.chooseMedia(MediaLookup(fetch), "movie", "Dragon", year, None)
        self.assertEqual(raised.exception.code, 1)
        return self.out.getvalue()

    def test_failed_tmdb_request_exits_with_its_message(self):
        def failing(path, params):
            raise LookupFailed("401 Client Error: Unauthorized")

        self.assertIn("401 Client Error", self.run_choose(failing))

    def test_zero_results_exits_asking_for_more_text(self):
        printed = self.run_choose(FakeTmdb({"search/movie": {"total_results": 0, "results": []}}))
        self.assertIn("Zero results...", printed)
        self.assertIn("Try to add more text to the title search", printed)

    def test_too_many_results_without_year_asks_for_a_year(self):
        printed = self.run_choose(FakeTmdb({"search/movie": {"total_results": 40, "results": []}}))
        self.assertIn("Too many results...", printed)
        self.assertIn("Please add a year to narrow down results", printed)

    def test_too_many_results_with_year_asks_for_more_text(self):
        printed = self.run_choose(FakeTmdb({"search/movie": {"total_results": 40, "results": []}}), 2010)
        self.assertIn("Try to add more text to the title search", printed)


if __name__ == "__main__":
    unittest.main()

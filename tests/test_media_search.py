import argparse
import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import discripper  # noqa: E402


def fake_tmdb_response(payload):
    response = mock.Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


class MovieSearchTest(unittest.TestCase):
    def setUp(self):
        discripper.args = argparse.Namespace(media="movie", tmdbid=None)
        discripper.dotenv = {"TMDB_API_KEY": "test-key"}

    def search(self, results, chosen_id):
        payload = {"total_results": len(results), "results": results}
        out = io.StringIO()
        with mock.patch.object(discripper.requests, "get", return_value=fake_tmdb_response(payload)), \
             mock.patch("builtins.input", return_value=str(chosen_id)), \
             redirect_stdout(out):
            found = discripper.getMediaInfo("How to train your dragon", "")
        return found, out.getvalue()

    def test_result_without_release_date_is_listed_and_selectable(self):
        results = [
            {"id": 10191, "original_title": "How to Train Your Dragon",
             "release_date": "2010-03-18", "popularity": 50.0},
            {"id": 999001, "original_title": "How to Train Your Dragon: Fan Cut",
             "popularity": 1.0},
        ]

        found, printed = self.search(results, 999001)

        self.assertIn("How to Train Your Dragon: Fan Cut", printed)
        self.assertEqual(found[0], "999001")
        self.assertEqual(found[1], "How to Train Your Dragon: Fan Cut")
        self.assertEqual(found[2], "")


class TvSearchTest(unittest.TestCase):
    def setUp(self):
        discripper.args = argparse.Namespace(media="tv", tmdbid=None)
        discripper.dotenv = {"TMDB_API_KEY": "test-key"}

    def search(self, shows, chosen_show_id, seasons, chosen_season_id):
        search_payload = {"total_results": len(shows), "results": shows}
        show_payload = {"seasons": seasons}
        out = io.StringIO()
        with mock.patch.object(discripper.requests, "get", side_effect=[
                 fake_tmdb_response(search_payload), fake_tmdb_response(show_payload)]), \
             mock.patch("builtins.input", side_effect=[str(chosen_show_id), str(chosen_season_id)]), \
             redirect_stdout(out):
            found = discripper.getMediaInfo("Dragons", "")
        return found, out.getvalue()

    def test_show_without_first_air_date_is_listed_and_selectable(self):
        shows = [
            {"id": 44305, "original_name": "DreamWorks Dragons",
             "first_air_date": "2012-08-07", "popularity": 40.0},
            {"id": 888001, "original_name": "Dragons: Untitled Pilot",
             "popularity": 0.5},
        ]
        seasons = [{"id": 55501, "name": "Season 1", "season_number": 1, "air_date": "2013-01-01"}]

        found, printed = self.search(shows, 888001, seasons, 55501)

        self.assertIn("Dragons: Untitled Pilot", printed)
        self.assertEqual(found, ("888001", "Dragons: Untitled Pilot", "", 1))

    def test_season_without_air_date_is_listed_and_selectable(self):
        shows = [{"id": 44305, "original_name": "DreamWorks Dragons",
                  "first_air_date": "2012-08-07", "popularity": 40.0}]
        seasons = [
            {"id": 55501, "name": "Season 1", "season_number": 1, "air_date": "2013-01-01"},
            {"id": 55509, "name": "Specials", "season_number": 0},
        ]

        found, printed = self.search(shows, 44305, seasons, 55509)

        self.assertIn("Specials", printed)
        self.assertEqual(found, ("44305", "DreamWorks Dragons", "2012-08-07", 0))


if __name__ == "__main__":
    unittest.main()

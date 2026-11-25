import os
import sys
import unittest
from unittest import mock

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from media_lookup import (  # noqa: E402
    LookupFailed, Media, MediaLookup, NoResults, SearchResult, Season, TooManyResults, tmdb_fetch)


class FakeTmdb:
    """In-memory adapter for the fetch seam: canned JSON keyed by path."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, path, params):
        self.calls.append((path, params))
        return self.responses[path]


class FindMovieTest(unittest.TestCase):
    def test_results_come_back_most_popular_first(self):
        tmdb = FakeTmdb({"search/movie": {"total_results": 2, "results": [
            {"id": 999001, "original_title": "How to Train Your Dragon: Fan Cut",
             "release_date": "2011-01-01", "popularity": 1.0},
            {"id": 10191, "original_title": "How to Train Your Dragon",
             "release_date": "2010-03-18", "popularity": 50.0},
        ]}})

        found = MediaLookup(tmdb).find("movie", "How to train your dragon", "")

        self.assertEqual(found, [
            SearchResult(Media("movie", 10191, "How to Train Your Dragon", "2010"), 50.0),
            SearchResult(Media("movie", 999001, "How to Train Your Dragon: Fan Cut", "2011"), 1.0),
        ])

    def test_movie_without_release_date_has_empty_year(self):
        tmdb = FakeTmdb({"search/movie": {"total_results": 1, "results": [
            {"id": 999001, "original_title": "How to Train Your Dragon: Fan Cut", "popularity": 1.0},
        ]}})

        found = MediaLookup(tmdb).find("movie", "How to train your dragon", "")

        self.assertEqual(found[0].media, Media("movie", 999001, "How to Train Your Dragon: Fan Cut", ""))


class SearchQueryTest(unittest.TestCase):
    def search_params(self, year):
        tmdb = FakeTmdb({"search/movie": {"total_results": 0, "results": []}})
        try:
            MediaLookup(tmdb).find("movie", "Pacific Rim", year)
        except NoResults:
            pass
        return tmdb.calls[0]

    def test_search_sends_name_and_year_to_tmdb(self):
        self.assertEqual(self.search_params(2013), ("search/movie", {
            "query": "Pacific Rim", "include_adult": "false", "language": "en-US",
            "page": 1, "year": 2013}))

    def test_search_without_year_leaves_year_out(self):
        for no_year in ("", None):
            path, params = self.search_params(no_year)
            self.assertNotIn("year", params)


class SearchResultCountTest(unittest.TestCase):
    def find(self, total_results, year):
        rows = [{"id": n, "original_title": f"Dragon {n}", "popularity": 1.0}
                for n in range(min(total_results, 20))]
        tmdb = FakeTmdb({"search/movie": {"total_results": total_results, "results": rows}})
        return MediaLookup(tmdb).find("movie", "Dragon", year)

    def test_zero_results_raises_no_results(self):
        with self.assertRaises(NoResults):
            self.find(0, "")

    def test_more_than_25_results_without_year_says_no_year_was_given(self):
        with self.assertRaises(TooManyResults) as raised:
            self.find(26, "")
        self.assertFalse(raised.exception.year_given)

    def test_more_than_25_results_with_year_says_year_was_given(self):
        with self.assertRaises(TooManyResults) as raised:
            self.find(26, 2010)
        self.assertTrue(raised.exception.year_given)

    def test_exactly_25_results_are_returned(self):
        self.assertEqual(len(self.find(25, "")), 20)


class FindShowTest(unittest.TestCase):
    def test_shows_use_tmdb_tv_fields_and_tolerate_missing_air_date(self):
        tmdb = FakeTmdb({"search/tv": {"total_results": 2, "results": [
            {"id": 44305, "original_name": "DreamWorks Dragons",
             "first_air_date": "2012-08-07", "popularity": 40.0},
            {"id": 888001, "original_name": "Dragons: Untitled Pilot", "popularity": 0.5},
        ]}})

        found = MediaLookup(tmdb).find("tv", "Dragons", "")

        self.assertEqual(found, [
            SearchResult(Media("tv", 44305, "DreamWorks Dragons", "2012"), 40.0),
            SearchResult(Media("tv", 888001, "Dragons: Untitled Pilot", ""), 0.5),
        ])


class GetByTmdbIdTest(unittest.TestCase):
    def test_movie_by_tmdb_id(self):
        tmdb = FakeTmdb({"movie/10191": {"id": 10191, "original_title": "How to Train Your Dragon",
                                         "release_date": "2010-03-18"}})

        media = MediaLookup(tmdb).get("movie", 10191)

        self.assertEqual(media, Media("movie", 10191, "How to Train Your Dragon", "2010"))
        self.assertEqual(tmdb.calls, [("movie/10191", {"language": "en-US"})])

    def test_show_by_tmdb_id_reads_tv_fields(self):
        tmdb = FakeTmdb({"tv/44305": {"id": 44305, "original_name": "DreamWorks Dragons",
                                      "first_air_date": "2012-08-07", "seasons": []}})

        media = MediaLookup(tmdb).get("tv", 44305)

        self.assertEqual(media, Media("tv", 44305, "DreamWorks Dragons", "2012"))


class UnknownKindTest(unittest.TestCase):
    def test_unknown_kind_is_rejected_before_calling_tmdb(self):
        tmdb = FakeTmdb({})
        lookup = MediaLookup(tmdb)
        with self.assertRaises(ValueError):
            lookup.find("music", "Dragons", "")
        with self.assertRaises(ValueError):
            lookup.get("music", 1)
        self.assertEqual(tmdb.calls, [])


class SeasonsTest(unittest.TestCase):
    def test_seasons_come_back_in_season_order_including_specials_without_air_date(self):
        tmdb = FakeTmdb({"tv/44305": {"id": 44305, "original_name": "DreamWorks Dragons", "seasons": [
            {"id": 55501, "name": "Season 1", "season_number": 1, "air_date": "2013-01-01"},
            {"id": 55509, "name": "Specials", "season_number": 0},
        ]}})
        show = Media("tv", 44305, "DreamWorks Dragons", "2012")

        seasons = MediaLookup(tmdb).seasons(show)

        self.assertEqual(seasons, [
            Season(55509, 0, "Specials", ""),
            Season(55501, 1, "Season 1", "2013-01-01"),
        ])

    def test_movies_have_no_seasons(self):
        with self.assertRaises(ValueError):
            MediaLookup(FakeTmdb({})).seasons(Media("movie", 10191, "How to Train Your Dragon", "2010"))


class TmdbFetchAdapterTest(unittest.TestCase):
    def test_sends_bearer_token_to_tmdb_v3_and_returns_json(self):
        response = mock.Mock()
        response.json.return_value = {"ok": True}
        with mock.patch.object(requests, "get", return_value=response) as get:
            body = tmdb_fetch("test-key")("movie/10191", {"language": "en-US"})

        self.assertEqual(body, {"ok": True})
        get.assert_called_once_with(
            "https://api.themoviedb.org/3/movie/10191", params={"language": "en-US"},
            headers={"accept": "application/json", "Authorization": "Bearer test-key"}, timeout=30)

    def test_http_error_becomes_lookup_failed(self):
        response = mock.Mock()
        response.raise_for_status.side_effect = requests.HTTPError("401 Client Error: Unauthorized")
        with mock.patch.object(requests, "get", return_value=response), \
             self.assertRaises(LookupFailed) as raised:
            tmdb_fetch("bad-key")("search/movie", {})
        self.assertIn("401 Client Error", str(raised.exception))

    def test_network_error_becomes_lookup_failed(self):
        with mock.patch.object(requests, "get", side_effect=requests.ConnectionError("no route")), \
             self.assertRaises(LookupFailed):
            tmdb_fetch("test-key")("search/movie", {})


if __name__ == "__main__":
    unittest.main()

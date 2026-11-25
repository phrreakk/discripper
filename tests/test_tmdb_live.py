"""Media lookup against the real TMDB.

These need a TMDB read token (see tests/tmdb_key.py) and are skipped without
one. They check facts TMDB shouldn't change, not rankings or popularity.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from media_lookup import LookupFailed, Media, MediaLookup, tmdb_fetch  # noqa: E402
from tests.tmdb_key import requires_tmdb_key, tmdb_read_key  # noqa: E402

DRAGON = Media("movie", 10191, "How to Train Your Dragon", "2010")
DRAGONS_SHOW = Media("tv", 44305, "DreamWorks Dragons", "2012")


@requires_tmdb_key
class LiveTmdbTest(unittest.TestCase):
    def setUp(self):
        self.lookup = MediaLookup(tmdb_fetch(tmdb_read_key()))

    def test_movie_search_with_year_finds_the_movie(self):
        found = self.lookup.find("movie", "How to Train Your Dragon", 2010)

        self.assertIn(DRAGON, [result.media for result in found])

    def test_movie_by_tmdb_id_matches_the_search_result(self):
        self.assertEqual(self.lookup.get("movie", 10191), DRAGON)

    def test_show_search_finds_the_show(self):
        found = self.lookup.find("tv", "DreamWorks Dragons", "")

        self.assertIn(DRAGONS_SHOW, [result.media for result in found])

    def test_show_seasons_have_names_and_air_dates(self):
        seasons = {season.number: season for season in self.lookup.seasons(DRAGONS_SHOW)}

        self.assertEqual((seasons[1].name, seasons[1].air_date), ("Riders of Berk", "2012-08-07"))
        self.assertEqual((seasons[2].name, seasons[2].air_date), ("Defenders of Berk", "2013-09-19"))

    def test_season_episodes_have_names(self):
        episodes = {episode.number: episode for episode in self.lookup.episodes(DRAGONS_SHOW, 1)}

        self.assertEqual(episodes[1].name, "How to Start a Dragon Academy")
        self.assertEqual(episodes[20].name, "We Are Family (2)")

    def test_bad_token_becomes_lookup_failed(self):
        with self.assertRaises(LookupFailed) as raised:
            MediaLookup(tmdb_fetch("not-a-real-token")).get("movie", 10191)

        self.assertIn("401", str(raised.exception))


if __name__ == "__main__":
    unittest.main()

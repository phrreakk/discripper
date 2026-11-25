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

    def test_movie_by_tmdb_id(self):
        self.assertEqual(self.lookup.get("movie", 10191), DRAGON)

    def test_show_search_finds_the_show(self):
        found = self.lookup.find("tv", "DreamWorks Dragons", "")

        self.assertIn(DRAGONS_SHOW, [result.media for result in found])

    def test_show_seasons_come_back_in_order_with_names_and_air_dates(self):
        seasons = self.lookup.seasons(self.lookup.get("tv", 44305))

        self.assertEqual([season.number for season in seasons][:2], [1, 2])
        self.assertEqual((seasons[0].name, seasons[0].air_date), ("Riders of Berk", "2012-08-07"))

    def test_bad_token_becomes_lookup_failed(self):
        with self.assertRaises(LookupFailed) as raised:
            MediaLookup(tmdb_fetch("not-a-real-token")).get("movie", 10191)

        self.assertIn("401", str(raised.exception))


if __name__ == "__main__":
    unittest.main()

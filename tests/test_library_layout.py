import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library_layout import episode_code, folder_for, path_for  # noqa: E402
from media_lookup import Media  # noqa: E402

MOVIE = Media(kind="movie", tmdb_id=10191, name="How to Train Your Dragon", year="2010")
SHOW = Media(kind="tv", tmdb_id=1396, name="Breaking Bad", year="2008")


class MovieLayoutTest(unittest.TestCase):
    def test_movie_folder_carries_name_year_and_tmdb_id(self):
        self.assertEqual(str(folder_for(MOVIE)),
                         "How_to_Train_Your_Dragon (2010) [tmdbid-10191]")

    def test_each_format_gets_its_own_version_suffix(self):
        self.assertEqual(
            str(path_for(MOVIE, "4k")),
            "How_to_Train_Your_Dragon (2010) [tmdbid-10191]/"
            "How_to_Train_Your_Dragon (2010) [tmdbid-10191] - 2160p.mkv")
        self.assertEqual(
            str(path_for(MOVIE, "1080p")),
            "How_to_Train_Your_Dragon (2010) [tmdbid-10191]/"
            "How_to_Train_Your_Dragon (2010) [tmdbid-10191] - 1080p.mkv")

    def test_a_movie_has_no_season_or_episode(self):
        with self.assertRaises(ValueError):
            folder_for(MOVIE, season=1)
        with self.assertRaises(ValueError):
            path_for(MOVIE, "4k", episode=1)


class TvLayoutTest(unittest.TestCase):
    def test_season_folder_is_zero_padded_under_the_show_folder(self):
        self.assertEqual(str(folder_for(SHOW, season=2)),
                         "Breaking_Bad (2008) [tmdbid-1396]/Season 02")

    def test_specials_are_season_00(self):
        self.assertEqual(str(folder_for(SHOW, season=0)),
                         "Breaking_Bad (2008) [tmdbid-1396]/Season 00")

    def test_episode_file_is_named_by_season_and_episode(self):
        self.assertEqual(
            str(path_for(SHOW, "1080p", season=1, episode=3)),
            "Breaking_Bad (2008) [tmdbid-1396]/Season 01/Breaking_Bad S01E03 - 1080p.mkv")

    def test_4k_and_1080p_encodes_of_an_episode_do_not_collide(self):
        self.assertNotEqual(path_for(SHOW, "4k", season=1, episode=3),
                            path_for(SHOW, "1080p", season=1, episode=3))

    def test_episode_numbers_past_99_are_not_truncated(self):
        self.assertTrue(str(path_for(SHOW, "4k", season=1, episode=101)).endswith("S01E101 - 2160p.mkv"))

    def test_an_episode_code_is_the_zero_padded_season_and_episode(self):
        self.assertEqual(episode_code(0, 1), "S00E01")
        self.assertEqual(episode_code(1, 101), "S01E101")

    def test_tv_needs_season_and_episode(self):
        with self.assertRaises(ValueError):
            folder_for(SHOW)
        with self.assertRaises(ValueError):
            path_for(SHOW, "4k", season=1)


class FormatTest(unittest.TestCase):
    def test_all_is_not_a_single_format(self):
        with self.assertRaises(ValueError):
            path_for(MOVIE, "all")


if __name__ == "__main__":
    unittest.main()

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import discripper  # noqa: E402
from disc import Disc, DiscTitle  # noqa: E402
from encoder import Encoder  # noqa: E402
from media_lookup import Media  # noqa: E402
from tests.fakes import FakeTool, handbrake_that_finishes, makemkv_that_copies  # noqa: E402

MOVIE = Media(kind="movie", tmdb_id=10191, name="How to Train Your Dragon", year="2010")
SHOW = Media(kind="tv", tmdb_id=44305, name="DreamWorks Dragons", year="2012")
MOVIE_FOLDER = "How_to_Train_Your_Dragon (2010) [tmdbid-10191]"
SEASON_FOLDER = "DreamWorks_Dragons (2012) [tmdbid-44305]/Season 01"


def title(number):
    return DiscTitle(number=number, file_name=f"title_t{number:02d}.mkv", duration="0:22:10",
                     chapters=5, size="4.0 GB")


class EncodeFullMkvTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.handbrake = FakeTool(handbrake_that_finishes)
        self.encoder = Encoder(self.handbrake, "x265_10bit")
        self.enterContext(redirect_stdout(io.StringIO()))

    def encode(self, media, rip_name, season, formats):
        return discripper.encodeFullMkv(self.encoder, self.folder / rip_name, media, self.folder,
                                        season, formats)

    def test_a_movie_is_encoded_at_each_format_into_the_library_layout(self):
        encoded = self.encode(MOVIE, "title_t00.mkv", None, ["4k", "1080p"])

        self.assertEqual(encoded, [
            self.folder / MOVIE_FOLDER / f"{MOVIE_FOLDER} - 2160p.mkv",
            self.folder / MOVIE_FOLDER / f"{MOVIE_FOLDER} - 1080p.mkv",
        ])

    def test_only_the_chosen_format_is_encoded(self):
        encoded = self.encode(MOVIE, "title_t00.mkv", None, ["1080p"])

        self.assertEqual([path.name for path in encoded], [f"{MOVIE_FOLDER} - 1080p.mkv"])
        self.assertEqual(len(self.handbrake.calls), 1)

    def test_tv_rips_become_episodes_in_the_order_they_are_encoded(self):
        first = self.encode(SHOW, "title_t03.mkv", 1, ["4k"])
        second = self.encode(SHOW, "title_t04.mkv", 1, ["4k"])

        self.assertEqual(first, [self.folder / SEASON_FOLDER / "DreamWorks_Dragons S01E01 - 2160p.mkv"])
        self.assertEqual(second, [self.folder / SEASON_FOLDER / "DreamWorks_Dragons S01E02 - 2160p.mkv"])

    def test_a_tv_rip_encoded_again_keeps_its_episode_number_at_every_format(self):
        self.encode(SHOW, "title_t03.mkv", 1, ["4k", "1080p"])
        self.encode(SHOW, "title_t04.mkv", 1, ["4k", "1080p"])

        again = self.encode(SHOW, "title_t03.mkv", 1, ["4k", "1080p"])

        self.assertEqual([path.name for path in again], ["DreamWorks_Dragons S01E01 - 2160p.mkv",
                                                         "DreamWorks_Dragons S01E01 - 1080p.mkv"])


class RipAndEncodeTest(unittest.TestCase):
    def test_every_title_in_a_tv_range_is_ripped_and_encoded(self):
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        makemkv = FakeTool(makemkv_that_copies)
        handbrake = FakeTool(handbrake_that_finishes)
        out = io.StringIO()

        with redirect_stdout(out):
            discripper.ripAndEncode(Disc(makemkv), Encoder(handbrake, "x265_10bit"),
                                    [title(2), title(3)], SHOW, folder, 1, ["1080p"])

        self.assertEqual([args[-2] for args in makemkv.calls], ["2", "3"])
        self.assertIn("S01E02 - 1080p.mkv", out.getvalue())

    def test_a_failed_rip_exits_and_points_at_its_log(self):
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        out = io.StringIO()

        with redirect_stdout(out), self.assertRaises(SystemExit) as exit:
            discripper.ripAndEncode(Disc(FakeTool(lambda args: "")),
                                    Encoder(FakeTool(handbrake_that_finishes), "x265_10bit"),
                                    [title(7)], MOVIE, folder, None, ["4k"])

        self.assertEqual(exit.exception.code, 1)
        self.assertIn("makemkvrip_t07.log", out.getvalue())


class ChooseDiscTitlesTest(unittest.TestCase):
    TITLES = [title(0), title(1), title(2), title(3)]

    def choose(self, kind, typed):
        with mock.patch("builtins.input", side_effect=typed), redirect_stdout(io.StringIO()):
            return discripper.chooseDiscTitles(kind, self.TITLES)

    def test_a_movie_rips_the_one_title_typed(self):
        self.assertEqual(self.choose("movie", ["2"]), [title(2)])

    def test_tv_rips_every_title_from_start_to_end(self):
        self.assertEqual(self.choose("tv", ["1", "3"]), [title(1), title(2), title(3)])

    def test_anything_but_a_listed_number_is_asked_again(self):
        self.assertEqual(self.choose("movie", ["", "two", "9", "1"]), [title(1)])

    def test_tv_end_before_start_is_asked_again(self):
        self.assertEqual(self.choose("tv", ["2", "1", "2"]), [title(2)])


if __name__ == "__main__":
    unittest.main()

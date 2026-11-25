import dataclasses
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
from media_lookup import Media, MediaLookup  # noqa: E402
from tests.test_choose_media import DRAGON, DRAGONS_SHOW, SEASONS  # noqa: E402
from tests.test_media_lookup import FakeTmdb  # noqa: E402
from tests.planes_titles import EXTRA, T02, T03, T04  # noqa: E402
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


def plan(media, folder, titles, season=None, formats=("4k",)):
    return discripper.RipPlan(media=media, season=season, titles=titles, formats=list(formats),
                              folder=folder)


class RunRipTest(unittest.TestCase):
    def test_every_title_in_a_tv_range_is_ripped_and_encoded(self):
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        makemkv = FakeTool(makemkv_that_copies)
        handbrake = FakeTool(handbrake_that_finishes)
        out = io.StringIO()

        with redirect_stdout(out):
            discripper.runRip(plan(SHOW, folder, [title(2), title(3)], 1, ["1080p"]),
                              Disc(makemkv), Encoder(handbrake, "x265_10bit"))

        self.assertEqual([args[-2] for args in makemkv.calls], ["2", "3"])
        self.assertIn("S01E02 - 1080p.mkv", out.getvalue())

    def test_a_failed_rip_exits_and_points_at_its_log(self):
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        out = io.StringIO()

        with redirect_stdout(out), self.assertRaises(SystemExit) as exit:
            discripper.runRip(plan(MOVIE, folder, [title(7)]), Disc(FakeTool(lambda args: "")),
                              Encoder(FakeTool(handbrake_that_finishes), "x265_10bit"))

        self.assertEqual(exit.exception.code, 1)
        self.assertIn("makemkvrip_t07.log", out.getvalue())


class RipPlanSummaryTest(unittest.TestCase):
    def test_a_movie_summary_names_the_media_and_folder(self):
        summary = plan(MOVIE, Path("/rips/x"), []).summary()

        self.assertEqual(summary, "We are going to rip How to Train Your Dragon (2010) "
                                  "with TMDBID [tmdbid-10191] to /rips/x")

    def test_a_tv_summary_also_names_the_season(self):
        self.assertIn("DreamWorks Dragons - Season 2 (2012)",
                      plan(SHOW, Path("/rips/x"), [], season=2).summary())


def makemkv_listing(titles):
    """What makemkvcon -r info prints for titles numbered 0 up."""
    def output(args):
        lines = []
        for number in range(titles):
            lines += [f'TINFO:{number},8,0,"5"', f'TINFO:{number},9,0,"0:22:10"',
                      f'TINFO:{number},10,0,"4.0 GB"', f'TINFO:{number},27,0,"title_t{number:02d}.mkv"']
        return "\n".join(lines) + "\n"
    return output


class PlanRipTest(unittest.TestCase):
    def setUp(self):
        self.folder = self.enterContext(tempfile.TemporaryDirectory())
        self.out = io.StringIO()
        self.enterContext(redirect_stdout(self.out))

    def planRip(self, argv, typed, responses, titles=3):
        args = discripper.parseArgs(argv + [self.folder])
        lookup = MediaLookup(FakeTmdb(responses))
        with mock.patch("builtins.input", side_effect=typed):
            return discripper.planRip(args, lookup, Disc(FakeTool(makemkv_listing(titles))))

    def test_a_movie_found_by_tmdb_id_asks_only_for_the_disc_title(self):
        got = self.planRip(["--tmdbid", "10191", "-f", "1080p"], ["1"],
                           {"movie/10191": DRAGON})

        self.assertEqual(got, discripper.RipPlan(
            media=MOVIE, season=None, titles=[title(1)], formats=["1080p"],
            folder=Path(self.folder) / "How_to_Train_Your_Dragon"))
        self.assertTrue(got.folder.is_dir())

    def test_tv_asks_for_title_year_show_season_and_a_range(self):
        typed = ["", "Dragons", "", "44305", "55501", "0", "2"]
        got = self.planRip(["-m", "tv"], typed, {
            "search/tv": {"total_results": 1, "results": [DRAGONS_SHOW]},
            "tv/44305": DRAGONS_SHOW | {"seasons": SEASONS},
        })

        self.assertEqual(got.media, SHOW)
        self.assertEqual(got.season, 1)
        self.assertEqual([t.number for t in got.titles], [0, 1, 2])
        self.assertEqual(got.formats, ["4k", "1080p"])
        self.assertIn("You need a search term", self.out.getvalue())

    def test_no_disc_titles_exits_before_asking_for_one(self):
        with self.assertRaises(SystemExit) as exit:
            self.planRip(["--tmdbid", "10191"], [], {"movie/10191": DRAGON}, titles=0)

        self.assertEqual(exit.exception.code, 1)
        self.assertIn("makemkvinfo.log", self.out.getvalue())


class ShowDiscTitlesTest(unittest.TestCase):
    def rows(self, titles):
        out = io.StringIO()
        with redirect_stdout(out):
            discripper.showDiscTitles(titles)
        lines = [line for line in out.getvalue().splitlines() if line.startswith("|")]
        header = [cell.strip() for cell in lines[0].strip("|").split("|")]
        return [dict(zip(header, (cell.strip() for cell in line.strip("|").split("|"))))
                for line in lines[1:]]

    def test_copies_of_the_same_length_show_how_much_they_differ(self):
        rows = self.rows([T02, T03, T04, EXTRA])

        self.assertEqual([row["Playlist"] for row in rows],
                         ["00801.mpls", "00800.mpls", "00802.mpls", "00036.m2ts"])
        self.assertEqual([row["Segments differ from"] for row in rows], [
            "title 3 in 2, title 4 in 42",
            "title 2 in 2, title 4 in 42",
            "title 2 in 42, title 3 in 42",
            "",
        ])

    def test_a_skipped_duplicate_playlist_shows_next_to_its_title(self):
        english = dataclasses.replace(T03, duplicates=("00803.mpls",))

        rows = self.rows([T02, english])

        self.assertEqual([row["Playlist"] for row in rows],
                         ["00801.mpls", "00800.mpls (+00803)"])

    def test_the_table_stays_narrow(self):
        out = io.StringIO()
        with redirect_stdout(out):
            discripper.showDiscTitles([T02, T03, T04, EXTRA])

        self.assertLess(max(len(line) for line in out.getvalue().splitlines()), 120)


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

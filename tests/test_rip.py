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
from tests.fakes import StrictTmdb  # noqa: E402
from tests.planes_titles import EXTRA, T02, T03, T04  # noqa: E402
from tests.fakes import FakeTool, handbrake_that_finishes, makemkv_that_copies  # noqa: E402

MOVIE = Media(kind="movie", tmdb_id=10191, name="How to Train Your Dragon", year="2010")
SHOW = Media(kind="tv", tmdb_id=44305, name="DreamWorks Dragons", year="2012")
EPISODES = {"episodes": [{"episode_number": n, "name": f"Episode {n}", "runtime": 22}
                         for n in range(1, 21)]}
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

    def encode(self, media, rip_name, season, formats, episode=None):
        return discripper.encodeFullMkv(self.encoder, self.folder / rip_name, media, self.folder,
                                        season, episode, formats)

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

    def test_a_tv_rip_is_named_from_the_episode_it_is_paired_with(self):
        encoded = self.encode(SHOW, "title_t03.mkv", 1, ["4k", "1080p"], episode=7)

        self.assertEqual(encoded, [
            self.folder / SEASON_FOLDER / "DreamWorks_Dragons S01E07 - 2160p.mkv",
            self.folder / SEASON_FOLDER / "DreamWorks_Dragons S01E07 - 1080p.mkv",
        ])

    def test_an_old_episode_list_is_ignored(self):
        (self.folder / SEASON_FOLDER).mkdir(parents=True)
        listing = self.folder / SEASON_FOLDER / "episode.list"
        listing.write_text(f"{self.folder / 'D1' / 'title_t03.mkv'}\n", encoding="utf-8")

        encoded = self.encode(SHOW, "D1/title_t03.mkv", 1, ["4k"], episode=4)

        self.assertEqual([path.name for path in encoded], ["DreamWorks_Dragons S01E04 - 2160p.mkv"])
        self.assertEqual(listing.read_text(encoding="utf-8").count("\n"), 1)


def planned(number, season, episode):
    """Disc title number in a TV Rip plan, paired with Episode episode of season."""
    return discripper.PlannedTitle(title(number), season, episode)


def plan(media, folder, titles, season=None, formats=("4k",), library=None):
    return discripper.RipPlan(media=media, season=season, titles=titles, formats=list(formats),
                              folder=folder, library=folder if library is None else library)


class RunRipTest(unittest.TestCase):
    def test_every_title_in_a_tv_range_is_ripped_and_encoded(self):
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        makemkv = FakeTool(makemkv_that_copies)
        handbrake = FakeTool(handbrake_that_finishes)
        out = io.StringIO()

        with redirect_stdout(out):
            discripper.runRip(plan(SHOW, folder, [planned(2, 1, 5), planned(3, 1, 6)], 1, ["1080p"]),
                              Disc(makemkv), Encoder(handbrake, "x265_10bit"))

        self.assertEqual([args[-2] for args in makemkv.calls], ["2", "3"])
        self.assertIn("S01E05 - 1080p.mkv", out.getvalue())
        self.assertIn("S01E06 - 1080p.mkv", out.getvalue())

    def test_rips_go_in_the_disc_folder_and_encodes_in_the_library(self):
        show = Path(self.enterContext(tempfile.TemporaryDirectory()))
        with redirect_stdout(io.StringIO()):
            discripper.runRip(plan(SHOW, show / "D2", [planned(0, 1, 1)], 1, ["1080p"], library=show),
                              Disc(FakeTool(makemkv_that_copies)),
                              Encoder(FakeTool(handbrake_that_finishes), "x265_10bit"))

        self.assertTrue((show / "D2" / "title_t00.mkv").is_file())
        self.assertTrue((show / SEASON_FOLDER / "DreamWorks_Dragons S01E01 - 1080p.mkv").is_file())

    def test_two_discs_whose_rips_share_file_names_become_different_episodes(self):
        show = Path(self.enterContext(tempfile.TemporaryDirectory()))
        makemkv = FakeTool(makemkv_that_copies)
        handbrake = FakeTool(handbrake_that_finishes)
        with redirect_stdout(io.StringIO()):
            for number, disc in enumerate(["D1", "D2"], start=1):
                discripper.runRip(plan(SHOW, show / disc, [planned(0, 1, number)], 1, ["1080p"],
                                       library=show),
                                  Disc(makemkv), Encoder(handbrake, "x265_10bit"))

        self.assertEqual(len(makemkv.calls), 2)
        self.assertTrue((show / "D1" / "title_t00.mkv").is_file())
        self.assertTrue((show / "D2" / "title_t00.mkv").is_file())
        self.assertEqual(sorted(path.name for path in (show / SEASON_FOLDER).glob("*.mkv")),
                         ["DreamWorks_Dragons S01E01 - 1080p.mkv",
                          "DreamWorks_Dragons S01E02 - 1080p.mkv"])

    def test_a_title_paired_with_another_season_is_encoded_into_that_seasons_folder(self):
        show = Path(self.enterContext(tempfile.TemporaryDirectory()))
        with redirect_stdout(io.StringIO()):
            discripper.runRip(plan(SHOW, show / "D1", [planned(1, 0, 1), planned(4, 1, 1)], 1,
                                   ["4k"], library=show),
                              Disc(FakeTool(makemkv_that_copies)),
                              Encoder(FakeTool(handbrake_that_finishes), "x265_10bit"))

        showFolder = show / "DreamWorks_Dragons (2012) [tmdbid-44305]"
        self.assertTrue((showFolder / "Season 00" / "DreamWorks_Dragons S00E01 - 2160p.mkv").is_file())
        self.assertTrue((showFolder / "Season 01" / "DreamWorks_Dragons S01E01 - 2160p.mkv").is_file())

    def test_a_failed_rip_exits_and_points_at_its_log(self):
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        out = io.StringIO()

        with redirect_stdout(out), self.assertRaises(SystemExit) as exit:
            discripper.runRip(plan(MOVIE, folder, [discripper.PlannedTitle(title(7))]), Disc(FakeTool(lambda args: "")),
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


def makemkv_listing(titles, label=None):
    """What makemkvcon -r info prints for titles numbered 0 up, on a disc with volume label."""
    def output(args):
        lines = [] if label is None else [f'CINFO:32,0,"{label}"']
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

    def planRip(self, argv, typed, responses, titles=3, label=None):
        args = discripper.parseArgs(argv + [self.folder])
        lookup = MediaLookup(StrictTmdb(responses))
        with mock.patch("builtins.input", side_effect=typed):
            return discripper.planRip(args, lookup, Disc(FakeTool(makemkv_listing(titles, label))))

    def planTv(self, typed, label=None, pairing=("",)):
        """Plan a TV rip of DreamWorks Dragons Season 1 found by TMDB id, ripping titles 0 to 2.

        typed answers the questions before the Disc titles; pairing answers the reassign prompt.
        """
        return self.planRip(["-m", "tv", "--tmdbid", "44305"], ["55501", *typed, "0-2", *pairing],
                            {"tv/44305": DRAGONS_SHOW | {"seasons": SEASONS},
                             "tv/44305/season/1": EPISODES, "tv/44305/season/0": EPISODES},
                            label=label)

    def test_a_movie_found_by_tmdb_id_asks_only_for_the_disc_title(self):
        got = self.planRip(["--tmdbid", "10191", "-f", "1080p"], ["1"],
                           {"movie/10191": DRAGON})

        self.assertEqual(got, discripper.RipPlan(
            media=MOVIE, season=None, titles=[discripper.PlannedTitle(title(1))], formats=["1080p"],
            folder=Path(self.folder) / "How_to_Train_Your_Dragon",
            library=Path(self.folder) / "How_to_Train_Your_Dragon"))
        self.assertTrue(got.folder.is_dir())

    def test_tv_asks_for_name_year_show_season_and_a_list_of_disc_titles(self):
        typed = ["", "Dragons", "", "44305", "55501", "1", "0-2", ""]
        got = self.planRip(["-m", "tv"], typed, {
            "search/tv": {"total_results": 1, "results": [DRAGONS_SHOW]},
            "tv/44305": DRAGONS_SHOW | {"seasons": SEASONS},
            "tv/44305/season/1": EPISODES,
        })

        self.assertEqual(got.media, SHOW)
        self.assertEqual(got.season, 1)
        self.assertEqual([t.title.number for t in got.titles], [0, 1, 2])
        self.assertEqual(got.formats, ["4k", "1080p"])
        self.assertIn("You need a search term", self.out.getvalue())

    def test_a_movie_rips_into_its_media_folder_even_when_the_disc_has_a_label(self):
        got = self.planRip(["--tmdbid", "10191"], ["1"], {"movie/10191": DRAGON}, label="DRAGON")

        self.assertEqual(got.folder, Path(self.folder) / "How_to_Train_Your_Dragon")

    def test_a_tv_disc_rips_into_a_folder_named_after_its_disc_label(self):
        got = self.planTv([], label="DRAGONS_S1_D2")

        self.assertEqual(got.folder, Path(self.folder) / "DreamWorks_Dragons" / "DRAGONS_S1_D2")
        self.assertEqual(got.library, Path(self.folder) / "DreamWorks_Dragons")
        self.assertTrue(got.folder.is_dir())

    def test_a_tv_disc_without_a_label_asks_for_its_disc_number(self):
        got = self.planTv(["", "two", "3"])

        self.assertEqual(got.folder, Path(self.folder) / "DreamWorks_Dragons" / "Disc 3")
        self.assertEqual(self.out.getvalue().count("You need a disc number"), 2)

    def test_the_tv_rip_plan_holds_each_titles_episode_and_leaves_skipped_titles_out(self):
        got = self.planTv([], label="D1", pairing=["1=-", "2=S0E1", ""])

        self.assertEqual(got.titles, [planned(0, 1, 1), planned(2, 0, 1)])

    def test_a_season_tmdb_cannot_fetch_exits(self):
        with self.assertRaises(SystemExit) as exit:
            self.planRip(["-m", "tv", "--tmdbid", "44305"], ["55501", "0-2"],
                         {"tv/44305": DRAGONS_SHOW | {"seasons": SEASONS}}, label="D1")

        self.assertEqual(exit.exception.code, 1)
        self.assertIn("TMDB request failed", self.out.getvalue())

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

    def choose(self, kind, typed, titles=None):
        self.out = io.StringIO()
        with mock.patch("builtins.input", side_effect=typed), redirect_stdout(self.out):
            return discripper.chooseDiscTitles(kind, self.TITLES if titles is None else titles)

    def test_a_movie_rips_the_one_title_typed(self):
        self.assertEqual(self.choose("movie", ["2"]), [title(2)])

    def test_tv_rips_the_listed_disc_titles_and_ranges(self):
        chosen = self.choose("tv", ["1-4,6"], titles=[title(n) for n in range(8)])

        self.assertEqual(chosen, [title(1), title(2), title(3), title(4), title(6)])

    def test_tv_asks_again_until_the_list_parses(self):
        typed = ["", "two", "1-", "-2", "3-1", "1,,2", "1 2", "1.5", "1, 2 - 3"]

        self.assertEqual(self.choose("tv", typed), [title(1), title(2), title(3)])

    def test_tv_asks_again_when_a_number_is_not_in_the_table(self):
        self.assertEqual(self.choose("tv", ["1-4", "9", "2"]), [title(2)])
        self.assertIn("Not in the table: 4", self.out.getvalue())
        self.assertIn("Not in the table: 9", self.out.getvalue())

    def test_tv_range_far_past_the_table_is_asked_again(self):
        self.assertEqual(self.choose("tv", ["1-99999999999", "1"]), [title(1)])
        self.assertIn("Not in the table: 1-99999999999", self.out.getvalue())

    def test_tv_disc_titles_come_back_in_title_number_order_once_each(self):
        self.assertEqual(self.choose("tv", ["3,0-1,1"]), [title(0), title(1), title(3)])

    def test_anything_but_a_listed_number_is_asked_again(self):
        self.assertEqual(self.choose("movie", ["", "two", "9", "1"]), [title(1)])



if __name__ == "__main__":
    unittest.main()

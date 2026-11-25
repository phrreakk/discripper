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
from disc import DiscTitle  # noqa: E402
from media_lookup import Media, MediaLookup  # noqa: E402
from tests.fakes import StrictTmdb  # noqa: E402

SHOW = Media(kind="tv", tmdb_id=4269, name="The Transformers", year="1984")
SEASON_FOLDER = "The_Transformers (1984) [tmdbid-4269]/Season {:02d}"


def title(number, duration="0:22:10"):
    return DiscTitle(number=number, file_name=f"title_t{number:02d}.mkv", duration=duration,
                     chapters=5, size="4.0 GB")


def season(number, count, runtime=22):
    return {"episodes": [{"episode_number": n, "name": f"S{number} Episode {n}", "runtime": runtime}
                         for n in range(1, count + 1)]}


def tables(printed):
    """Every table printed, each as a list of rows, each row a dict of column to cell.

    A PrettyTable has three border lines: above the header, below it, and at the end.
    """
    found, lines, borders = [], [], 0
    for line in printed.splitlines():
        if line.startswith("+"):
            borders += 1
            if borders == 3:
                header = [cell.strip() for cell in lines[0].strip("|").split("|")]
                found.append([dict(zip(header, (cell.strip() for cell in row.strip("|").split("|"))))
                              for row in lines[1:]])
                lines, borders = [], 0
        elif line.startswith("|"):
            lines.append(line)
    return found


class PairEpisodesTest(unittest.TestCase):
    def setUp(self):
        self.library = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.tmdb = StrictTmdb({"tv/4269/season/1": season(1, 13), "tv/4269/season/0": season(0, 3)})

    def encode(self, season_number, episode, label="2160p"):
        folder = self.library / SEASON_FOLDER.format(season_number)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"The_Transformers S{season_number:02d}E{episode:02d} - {label}.mkv").touch()

    def pair(self, typed, titles=None, picked=1, formats=("4k", "1080p")):
        titles = [title(n) for n in range(1, 6)] if titles is None else titles
        self.out = io.StringIO()
        with mock.patch("builtins.input", side_effect=typed), redirect_stdout(self.out):
            pairings = discripper.pairEpisodes(titles, SHOW, picked, MediaLookup(self.tmdb),
                                               self.library, list(formats))
        self.tables = tables(self.out.getvalue())
        return [(p.title.number, p.season, p.episode.number if p.episode else None)
                for p in pairings]

    def test_enter_accepts_the_proposal_starting_after_the_encoded_episodes(self):
        for episode in range(1, 5):
            self.encode(1, episode, "1080p" if episode % 2 else "2160p")

        got = self.pair([""])

        self.assertEqual(got, [(1, 1, 5), (2, 1, 6), (3, 1, 7), (4, 1, 8), (5, 1, 9)])
        self.assertEqual([row["Episode"] for row in self.tables[0]],
                         ["S01E05", "S01E06", "S01E07", "S01E08", "S01E09"])
        self.assertEqual(self.tables[0][0]["Name"], "S1 Episode 5")

    def test_each_change_redraws_the_table(self):
        got = self.pair(["3=5", "2=-", ""])

        self.assertEqual(got, [(1, 1, 1), (2, 1, None), (3, 1, 5), (4, 1, 6), (5, 1, 7)])
        self.assertEqual(len(self.tables), 3)
        self.assertEqual([row["Episode"] for row in self.tables[1]],
                         ["S01E01", "S01E02", "S01E05", "S01E06", "S01E07"])
        self.assertEqual(self.tables[2][1]["Episode"], "-")
        self.assertEqual(self.tables[2][1]["Flags"], "skipped")

    def test_invalid_input_asks_again(self):
        got = self.pair(["three=5", "9=1", "3=99", "3=S7E1", "3=4", ""])

        self.assertEqual(got[2], (3, 1, 4))
        self.assertEqual(len(self.tables), 2)
        printed = self.out.getvalue()
        self.assertIn("such as 3=5", printed)
        self.assertIn("Disc title 9", printed)
        self.assertIn("Season 1 has no Episode 99", printed)
        self.assertIn("Season 7", printed)

    def test_another_season_is_fetched_only_when_it_is_mentioned(self):
        got = self.pair(["1=S0E1", "4=1", ""])

        self.assertEqual(got, [(1, 0, 1), (2, 0, 2), (3, 0, 3), (4, 1, 1), (5, 1, 2)])
        self.assertEqual([path for path, _ in self.tmdb.calls],
                         ["tv/4269/season/1", "tv/4269/season/0"])
        self.assertEqual(self.tables[1][1]["Name"], "S0 Episode 2")

    def test_titles_past_the_last_episode_show_no_episode(self):
        got = self.pair([""], titles=[title(n) for n in range(1, 15)])

        self.assertEqual(got[-1], (14, 1, None))
        self.assertEqual(self.tables[0][-1]["Flags"], "no episode")

    def test_a_title_far_off_its_runtime_is_flagged(self):
        self.pair([""], titles=[title(1, "0:44:00"), title(2)])

        self.assertEqual([row["Flags"] for row in self.tables[0]],
                         ["runtime 44 min, TMDB 22 min", ""])

    def test_replacing_encodes_is_confirmed_once_and_no_goes_back_to_the_prompt(self):
        self.encode(1, 2)
        self.encode(1, 3, "1080p")

        with mock.patch("builtins.input", side_effect=["1=1", "", "n", "", "y"]) as typed, \
                redirect_stdout(io.StringIO()):
            pairings = discripper.pairEpisodes([title(n) for n in range(1, 4)], SHOW, 1,
                                               MediaLookup(self.tmdb), self.library,
                                               ["4k", "1080p"])

        self.assertEqual([p.episode.number for p in pairings], [1, 2, 3])
        prompts = [call.args[0] for call in typed.call_args_list]
        self.assertIn("S01E02, S01E03", prompts[2])
        self.assertEqual(prompts[3], prompts[0])

    def test_a_skipped_already_encoded_episode_is_not_confirmed(self):
        self.encode(1, 1)
        self.encode(1, 2)

        got = self.pair(["3=1", "3=-", ""], titles=[title(3)])

        self.assertEqual(got, [(3, 1, None)])

    def test_only_encodes_this_run_would_write_are_confirmed_for_replacing(self):
        self.encode(1, 1, "2160p")
        self.encode(1, 2, "1080p")

        with mock.patch("builtins.input", side_effect=["1=1", "", "y"]) as typed, \
                redirect_stdout(io.StringIO()):
            discripper.pairEpisodes([title(1), title(2)], SHOW, 1, MediaLookup(self.tmdb),
                                    self.library, ["1080p"])

        prompts = [call.args[0] for call in typed.call_args_list]
        self.assertIn("S01E02", prompts[2])
        self.assertNotIn("S01E01", prompts[2])

    def test_an_encode_at_another_format_is_not_confirmed(self):
        self.encode(1, 1, "2160p")

        got = self.pair(["1=1", ""], titles=[title(1)], formats=["1080p"])

        self.assertEqual(got, [(1, 1, 1)])
        self.assertEqual(self.tables[1][0]["Flags"], "already encoded")

    def test_enter_is_refused_while_two_titles_share_an_episode(self):
        got = self.pair(["3=1", "", "3=-", ""], titles=[title(1), title(2), title(3)])

        self.assertEqual(got, [(1, 1, 1), (2, 1, 2), (3, 1, None)])
        self.assertEqual(self.tables[1][0]["Flags"], "also title 3")
        self.assertIn("Disc titles 1 and 3 share S01E01", self.out.getvalue())


if __name__ == "__main__":
    unittest.main()

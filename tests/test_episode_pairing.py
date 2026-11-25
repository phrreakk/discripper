import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from disc import DiscTitle  # noqa: E402
from episode_pairing import (  # noqa: E402
    RUNTIME_TOLERANCE_MINUTES, Change, Pairing, flags, parse_change, propose, reassign, skip)
from media_lookup import Episode  # noqa: E402


def title(number, duration="0:22:10"):
    return DiscTitle(number=number, file_name=f"title_t{number:02d}.mkv", duration=duration,
                     chapters=5, size="4.0 GB")


SEASON_1 = [Episode(n, f"Episode {n}", 22) for n in range(1, 8)]


def episodes_of(pairings):
    """Each pairing as (Disc title, Season, Episode number or None)."""
    return [(p.title.number, p.season, p.episode.number if p.episode else None) for p in pairings]


class ProposeTest(unittest.TestCase):
    def test_the_proposal_starts_at_the_first_episode_without_an_encode(self):
        pairings = propose([title(0), title(1), title(2)], 1, SEASON_1, encoded={1, 2, 3, 4})

        self.assertEqual(episodes_of(pairings), [(0, 1, 5), (1, 1, 6), (2, 1, 7)])

    def test_titles_past_the_last_episode_have_no_episode(self):
        pairings = propose([title(0), title(1), title(2)], 1, SEASON_1, encoded={1, 2, 3, 4, 5, 6})

        self.assertEqual(episodes_of(pairings), [(0, 1, 7), (1, 1, None), (2, 1, None)])
        self.assertFalse(pairings[1].skipped)


SEASON_0 = [Episode(n, f"Special {n}", 22) for n in range(1, 4)]
FIVE_TITLES = [title(n) for n in range(1, 6)]


class ReassignTest(unittest.TestCase):
    def setUp(self):
        self.pairings = propose(FIVE_TITLES, 1, SEASON_1, encoded=set())

    def test_a_reassigned_title_takes_the_episode_and_later_titles_follow_on(self):
        pairings = reassign(self.pairings, 3, 1, 5, SEASON_1)

        self.assertEqual(episodes_of(pairings),
                         [(1, 1, 1), (2, 1, 2), (3, 1, 5), (4, 1, 6), (5, 1, 7)])
        self.assertTrue(pairings[2].explicit)

    def test_titles_set_explicitly_keep_their_pairing_when_an_earlier_title_is_reassigned(self):
        pairings = reassign(self.pairings, 4, 1, 7, SEASON_1)

        pairings = reassign(pairings, 2, 1, 1, SEASON_1)

        self.assertEqual(episodes_of(pairings),
                         [(1, 1, 1), (2, 1, 1), (3, 1, 2), (4, 1, 7), (5, 1, 3)])

    def test_a_title_can_move_to_another_season_and_later_titles_follow_it_there(self):
        # The Transformers: TMDB has the disc's first three episodes as S0E1-3.
        pairings = reassign(self.pairings, 1, 0, 1, SEASON_0)

        self.assertEqual(episodes_of(pairings),
                         [(1, 0, 1), (2, 0, 2), (3, 0, 3), (4, 0, None), (5, 0, None)])

        pairings = reassign(pairings, 4, 1, 1, SEASON_1)

        self.assertEqual(episodes_of(pairings),
                         [(1, 0, 1), (2, 0, 2), (3, 0, 3), (4, 1, 1), (5, 1, 2)])

    def test_an_episode_the_season_does_not_have_is_refused(self):
        with self.assertRaises(ValueError):
            reassign(self.pairings, 3, 1, 99, SEASON_1)

    def test_a_title_that_is_not_being_ripped_is_refused(self):
        with self.assertRaises(ValueError):
            reassign(self.pairings, 9, 1, 1, SEASON_1)


class SkipTest(unittest.TestCase):
    def test_a_skipped_title_has_no_episode_and_the_others_stay(self):
        pairings = skip(propose(FIVE_TITLES, 1, SEASON_1, encoded=set()), 3)

        self.assertEqual(episodes_of(pairings),
                         [(1, 1, 1), (2, 1, 2), (3, 1, None), (4, 1, 4), (5, 1, 5)])
        self.assertTrue(pairings[2].skipped)
        self.assertTrue(pairings[2].explicit)

    def test_a_skipped_title_keeps_its_skip_when_an_earlier_title_is_reassigned(self):
        pairings = skip(propose(FIVE_TITLES, 1, SEASON_1, encoded=set()), 3)

        pairings = reassign(pairings, 1, 1, 4, SEASON_1)

        self.assertEqual(episodes_of(pairings),
                         [(1, 1, 4), (2, 1, 5), (3, 1, None), (4, 1, 6), (5, 1, 7)])


def nothing_encoded(season, episode):
    return False


class FlagsTest(unittest.TestCase):
    def flags(self, duration="0:22:10", runtime=22, encoded=nothing_encoded):
        return flags(Pairing(title(1, duration), 1, Episode(3, "Animal House", runtime)), encoded)

    def test_a_pairing_close_to_its_tmdb_runtime_has_no_flags(self):
        self.assertEqual(self.flags(duration="0:26:59"), [])

    def test_a_pairing_more_than_the_tolerance_off_its_tmdb_runtime_is_flagged(self):
        self.assertEqual(RUNTIME_TOLERANCE_MINUTES, 5)
        self.assertEqual(self.flags(duration="0:27:01"), ["runtime 27 min, TMDB 22 min"])
        self.assertEqual(self.flags(duration="0:16:30"), ["runtime 16 min, TMDB 22 min"])

    def test_no_runtime_flag_when_tmdb_has_no_runtime(self):
        self.assertEqual(self.flags(duration="1:30:00", runtime=None), [])

    def test_an_episode_that_already_has_an_encode_is_flagged(self):
        self.assertEqual(self.flags(encoded=lambda season, episode: (season, episode) == (1, 3)),
                         ["already encoded"])

    def test_a_title_past_the_end_of_the_season_is_flagged_no_episode(self):
        self.assertEqual(flags(Pairing(title(1), 1, None), nothing_encoded), ["no episode"])

    def test_a_skipped_title_is_flagged_skipped(self):
        self.assertEqual(flags(Pairing(title(1), 1, None, skipped=True), nothing_encoded),
                         ["skipped"])


class ParseChangeTest(unittest.TestCase):
    def test_a_bare_episode_number_is_in_the_season_picked(self):
        self.assertEqual(parse_change("3=5", 2), Change(3, 2, 5))

    def test_another_season_is_named_with_s_and_e(self):
        self.assertEqual(parse_change("1=S0E1", 2), Change(1, 0, 1))
        self.assertEqual(parse_change("1=s00e01", 2), Change(1, 0, 1))

    def test_a_dash_skips_the_title(self):
        self.assertEqual(parse_change("3=-", 2), Change(3, None, None))

    def test_spaces_around_the_parts_are_allowed(self):
        self.assertEqual(parse_change(" 3 = S1E5 ", 2), Change(3, 1, 5))

    def test_anything_else_is_not_a_change(self):
        for typed in ["3", "=5", "x=5", "3=", "3=S0", "3=E1", "3=5-6", "3=5=6", "3=S0 E1"]:
            with self.subTest(typed=typed):
                self.assertIsNone(parse_change(typed, 2))


if __name__ == "__main__":
    unittest.main()

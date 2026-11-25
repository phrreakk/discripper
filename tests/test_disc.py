import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from disc import MIN_LENGTH, Disc, DiscTitle, RipFailed  # noqa: E402
from tests.fakes import FakeTool, makemkv_that_copies  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "makemkv"

# Written by hand in makemkvcon's robot format (-r info); not recorded from a disc.
TWO_TITLES = """\
MSG:1005,0,1,"MakeMKV v1.18.4 linux(x64-release) started","%1 started","MakeMKV v1.18.4 linux(x64-release)"
TCOUNT:2
CINFO:2,0,"HOW_TO_TRAIN"
TINFO:0,2,0,"How to Train Your Dragon"
TINFO:0,8,0,"24"
TINFO:0,9,0,"1:38:02"
TINFO:0,10,0,"31.4 GB"
TINFO:0,27,0,"title_t00.mkv"
SINFO:0,0,1,6201,"Video"
TINFO:1,8,0,"1"
TINFO:1,9,0,"0:05:12"
TINFO:1,10,0,"1.1 GB"
TINFO:1,27,0,"title_t01.mkv"
"""

MAIN_FEATURE = DiscTitle(number=0, file_name="title_t00.mkv", duration="1:38:02",
                         chapters=24, size="31.4 GB")


def info(text):
    return FakeTool(lambda args: text)


class TitlesTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_each_title_comes_back_with_its_file_name_duration_chapters_and_size(self):
        titles = Disc(info(TWO_TITLES)).titles(self.folder / "info.log")

        self.assertEqual(titles, [
            MAIN_FEATURE,
            DiscTitle(number=1, file_name="title_t01.mkv", duration="0:05:12",
                      chapters=1, size="1.1 GB"),
        ])

    def test_no_drive_means_no_titles(self):
        no_drive = (FIXTURES / "info_no_drive.txt").read_text(encoding="utf-8")

        self.assertEqual(Disc(info(no_drive)).titles(self.folder / "info.log"), [])

    def test_a_title_with_no_file_name_is_not_offered(self):
        text = 'TINFO:0,9,0,"1:38:02"\nTINFO:1,27,0,"title_t01.mkv"\n'

        titles = Disc(info(text)).titles(self.folder / "info.log")

        self.assertEqual([title.number for title in titles], [1])

    def test_the_makemkvcon_output_is_kept_in_the_log(self):
        log = self.folder / "info.log"

        Disc(info(TWO_TITLES)).titles(log)

        self.assertIn("TCOUNT:2", log.read_text(encoding="utf-8"))


class RipTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_rip_returns_the_path_of_the_ripped_file(self):
        rip = Disc(FakeTool(makemkv_that_copies)).rip(MAIN_FEATURE, self.folder)

        self.assertEqual(rip, self.folder / "title_t00.mkv")

    def test_listing_and_ripping_leave_out_the_same_short_titles(self):
        # makemkvcon numbers titles after dropping short ones, so the numbers only
        # match between info and mkv when both use the same --minlength.
        makemkv = FakeTool(lambda args: makemkv_that_copies(args) if "mkv" in args else TWO_TITLES)
        disc = Disc(makemkv)

        disc.rip(disc.titles(self.folder / "info.log")[0], self.folder)

        info_args, rip_args = makemkv.calls
        self.assertIn(f"--minlength={MIN_LENGTH}", info_args)
        self.assertIn(f"--minlength={MIN_LENGTH}", rip_args)
        self.assertEqual(rip_args[-3:], ["disc:0", "0", str(self.folder)])

    def test_a_copy_that_does_not_complete_raises_with_the_log(self):
        makemkv = FakeTool(lambda args: 'MSG:5003,0,0,"Failed to save title 0"\n')

        with self.assertRaises(RipFailed) as failed:
            Disc(makemkv).rip(MAIN_FEATURE, self.folder)

        self.assertEqual(failed.exception.log, self.folder / "makemkvrip_t00.log")

    def test_a_finished_rip_is_not_ripped_again(self):
        Disc(FakeTool(makemkv_that_copies)).rip(MAIN_FEATURE, self.folder)
        again = FakeTool(makemkv_that_copies)

        Disc(again).rip(MAIN_FEATURE, self.folder)

        self.assertEqual(again.calls, [])

    def test_a_rip_left_by_an_interrupted_copy_is_ripped_again(self):
        (self.folder / "title_t00.mkv").write_text("partial", encoding="utf-8")
        (self.folder / "makemkvrip_t00.log").write_text("Start: ...\n", encoding="utf-8")
        makemkv = FakeTool(makemkv_that_copies)

        Disc(makemkv).rip(MAIN_FEATURE, self.folder)

        self.assertEqual(len(makemkv.calls), 1)

    def test_each_title_in_a_range_keeps_its_own_log(self):
        disc = Disc(FakeTool(makemkv_that_copies))
        second = DiscTitle(number=1, file_name="title_t01.mkv", duration="0:22:10",
                           chapters=5, size="4.0 GB")

        disc.rip(MAIN_FEATURE, self.folder)
        disc.rip(second, self.folder)

        self.assertTrue((self.folder / "makemkvrip_t00.log").is_file())
        self.assertTrue((self.folder / "makemkvrip_t01.log").is_file())


if __name__ == "__main__":
    unittest.main()

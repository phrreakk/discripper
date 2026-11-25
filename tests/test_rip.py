import argparse
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import discripper  # noqa: E402
from media_lookup import Media  # noqa: E402

MOVIE = Media(kind="movie", tmdb_id=10191, name="How to Train Your Dragon", year="2010")


def fake_makemkv_info(lines):
    process = mock.Mock()
    process.stdout = iter(lines)
    return process


class RipFullMkvTest(unittest.TestCase):
    def setUp(self):
        discripper.pathRipApp = "/usr/bin/makemkvcon"

    def test_title_with_no_file_name_exits_with_message_instead_of_crashing(self):
        info_output = [
            'TINFO:0,27,0,"Main_Feature_t00.mkv"\n',
            'TINFO:1,27,0,"Bonus_t01.mkv"\n',
        ]
        out = io.StringIO()

        with tempfile.TemporaryDirectory() as folder, \
             mock.patch.object(discripper.subprocess, "Popen", return_value=fake_makemkv_info(info_output)), \
             redirect_stdout(out), \
             self.assertRaises(SystemExit) as exit:
            discripper.ripFullMkv(folder, 7)

        self.assertEqual(exit.exception.code, 1)
        self.assertIn("title 7", out.getvalue())


class EncodeFullMkvTest(unittest.TestCase):
    def setUp(self):
        for name, value in [("pathTranscodeApp", "/usr/bin/HandBrakeCLI"),
                            ("args", argparse.Namespace(format="all"))]:
            patcher = mock.patch.object(discripper, name, value, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_chosen_encoder_goes_to_both_the_4k_and_1080p_encodes(self):
        commands = []

        def fake_handbrake(command, stdout, stderr):
            commands.append(command)
            print(f'"File": "{command[-1]}"', file=stdout)
            print("Encode done!", file=stdout)
            return mock.Mock()

        with tempfile.TemporaryDirectory() as folder, \
             mock.patch.object(discripper.subprocess, "Popen", side_effect=fake_handbrake), \
             redirect_stdout(io.StringIO()):
            discripper.encodeFullMkv(os.path.join(folder, "title_t00.mkv"), MOVIE, folder, None,
                                     "nvenc_h265_10bit")

        presets = [command[command.index("-Z") + 1] for command in commands]
        encoders = [command[command.index("-e") + 1] for command in commands]
        self.assertEqual(presets, ["H.265 MKV 2160p60 4K", "H.265 MKV 1080p30"])
        self.assertEqual(encoders, ["nvenc_h265_10bit", "nvenc_h265_10bit"])


if __name__ == "__main__":
    unittest.main()

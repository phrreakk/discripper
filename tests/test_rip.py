import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import discripper  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()

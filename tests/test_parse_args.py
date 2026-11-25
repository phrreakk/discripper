import io
import os
import sys
import unittest
from contextlib import redirect_stderr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import discripper  # noqa: E402


class EncoderOptionTest(unittest.TestCase):
    def test_encoder_defaults_to_intel_qsv(self):
        args = discripper.parseArgs(["/media"])

        self.assertEqual(args.encoder, "qsv_h265_10bit")

    def test_encoder_can_be_nvidia_nvenc_or_software_x265(self):
        for encoder in ["nvenc_h265_10bit", "x265_10bit"]:
            with self.subTest(encoder=encoder):
                args = discripper.parseArgs(["--encoder", encoder, "/media"])

                self.assertEqual(args.encoder, encoder)

    def test_encoder_outside_the_list_is_refused(self):
        err = io.StringIO()

        with redirect_stderr(err), self.assertRaises(SystemExit) as exit:
            discripper.parseArgs(["--encoder", "vce_h265", "/media"])

        self.assertEqual(exit.exception.code, 2)
        self.assertIn("invalid choice: 'vce_h265'", err.getvalue())


if __name__ == "__main__":
    unittest.main()

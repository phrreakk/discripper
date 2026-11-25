import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from encoder import EncodeFailed, Encoder  # noqa: E402
from tests.fakes import FakeTool, handbrake_that_finishes  # noqa: E402


class EncodeTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.rip = self.folder / "title_t00.mkv"
        self.output = self.folder / "Movie" / "Movie - 2160p.mkv"

    def test_each_format_uses_its_preset_and_the_chosen_encoder(self):
        handbrake = FakeTool(handbrake_that_finishes)
        encoder = Encoder(handbrake, "nvenc_h265_10bit")

        encoder.encode(self.rip, self.folder / "a - 2160p.mkv", "4k")
        encoder.encode(self.rip, self.folder / "a - 1080p.mkv", "1080p")

        presets = [args[args.index("-Z") + 1] for args in handbrake.calls]
        encoders = [args[args.index("-e") + 1] for args in handbrake.calls]
        self.assertEqual(presets, ["H.265 MKV 2160p60 4K", "H.265 MKV 1080p30"])
        self.assertEqual(encoders, ["nvenc_h265_10bit", "nvenc_h265_10bit"])

    def test_encode_reads_the_rip_and_writes_the_output_folder(self):
        handbrake = FakeTool(handbrake_that_finishes)

        encoded = Encoder(handbrake, "x265_10bit").encode(self.rip, self.output, "4k")

        self.assertEqual(encoded, self.output)
        args = handbrake.calls[0]
        self.assertEqual(args[args.index("-i") + 1], str(self.rip))
        self.assertTrue(self.output.is_file())

    def test_an_encode_that_does_not_finish_raises_with_the_log(self):
        handbrake = FakeTool(lambda args: "Encode failed (error 3).\n")

        with self.assertRaises(EncodeFailed) as failed:
            Encoder(handbrake, "x265_10bit").encode(self.rip, self.output, "4k")

        self.assertEqual(failed.exception.log, self.folder / "Movie" / "Movie - 2160p.log")

    def test_a_finished_encode_is_not_encoded_again(self):
        Encoder(FakeTool(handbrake_that_finishes), "x265_10bit").encode(self.rip, self.output, "4k")
        again = FakeTool(handbrake_that_finishes)

        Encoder(again, "x265_10bit").encode(self.rip, self.output, "4k")

        self.assertEqual(again.calls, [])

    def test_an_output_left_by_an_interrupted_encode_is_encoded_again(self):
        self.output.parent.mkdir()
        self.output.write_text("partial", encoding="utf-8")
        handbrake = FakeTool(handbrake_that_finishes)

        Encoder(handbrake, "x265_10bit").encode(self.rip, self.output, "4k")

        self.assertEqual(len(handbrake.calls), 1)

    def test_unknown_encoder_or_format_is_refused(self):
        with self.assertRaises(ValueError):
            Encoder(FakeTool(handbrake_that_finishes), "vce_h265")
        with self.assertRaises(ValueError):
            Encoder(FakeTool(handbrake_that_finishes), "x265_10bit").encode(
                self.rip, self.output, "720p")


if __name__ == "__main__":
    unittest.main()

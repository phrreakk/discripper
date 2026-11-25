"""Encoder: encode a Rip at one Format with HandBrakeCLI.

The only dependency is ``run(args, log)``, which runs HandBrakeCLI with ``args``
and writes everything it prints to the file ``log`` (see ``tool_run.tool``).
Each encode's log sits next to its output, with ``.log`` in place of ``.mkv``.
"""

from pathlib import Path

from library_layout import Format
from tool_run import Run

# HandBrake video encoders --encoder accepts: Intel QSV (the default), NVIDIA NVENC, and software x265.
ENCODERS = ["qsv_h265_10bit", "nvenc_h265_10bit", "x265_10bit"]

# The HandBrake preset each Format is encoded with.
PRESETS = {"4k": "H.265 MKV 2160p60 4K", "1080p": "H.265 MKV 1080p30"}


class EncodeFailed(Exception):
    """HandBrakeCLI did not report a finished encode. Details are in ``log``."""

    def __init__(self, output: Path, log: Path):
        super().__init__(f"{output} did not encode; see {log}")
        self.output = output
        self.log = log


class Encoder:
    def __init__(self, run: Run, video_encoder: str):
        if video_encoder not in ENCODERS:
            raise ValueError(f"Unknown encoder: {video_encoder!r}")
        self._run = run
        self._video_encoder = video_encoder

    def encode(self, rip: Path, output: Path, format: Format) -> Path:
        """Encode rip at format to output and return output.

        An output whose earlier log shows a finished encode is kept instead of
        encoded again. Raises EncodeFailed if HandBrakeCLI doesn't finish.
        """
        if format not in PRESETS:
            raise ValueError(f"Unknown format: {format!r}")
        log = output.with_suffix(".log")
        if output.is_file() and _encode_done(log):
            return output
        output.parent.mkdir(parents=True, exist_ok=True)
        self._run(["-Z", PRESETS[format], "-e", self._video_encoder,
                   "-i", str(rip), "-o", str(output)], log)
        if not _encode_done(log):
            raise EncodeFailed(output, log)
        return output


def _encode_done(log: Path) -> bool:
    if not log.is_file():
        return False
    return "Encode done!" in log.read_text(encoding="utf-8", errors="replace")

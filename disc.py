"""Disc: list the Disc titles in the drive and rip them, through makemkvcon.

The only dependency is ``run(args, log)``, which runs makemkvcon with ``args``
and writes everything it prints to the file ``log`` (see ``tool_run.tool``).
Disc parses makemkvcon's robot output (``-r``) from that log.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from tool_run import Run

# Disc titles shorter than this many seconds are left out. makemkvcon numbers
# Disc titles after leaving the short ones out, so listing and ripping must use
# the same value or a typed number rips a different Disc title.
MIN_LENGTH = 300

# Robot-mode title attributes (ap_iaChapterCount and friends in makemkv's apdefs.h).
_CHAPTERS = 8
_DURATION = 9
_SIZE = 10
_FILE_NAME = 27

_TINFO = re.compile(r'^TINFO:(\d+),(\d+),\d+,"(.*)"$')


@dataclass(frozen=True)
class DiscTitle:
    number: int
    file_name: str
    duration: str
    chapters: int
    size: str


class RipFailed(Exception):
    """makemkvcon did not report a finished copy. Details are in ``log``."""

    def __init__(self, title: DiscTitle, log: Path):
        super().__init__(f"Disc title {title.number} did not rip; see {log}")
        self.title = title
        self.log = log


class Disc:
    def __init__(self, run: Run, drive: str = "disc:0"):
        self._run = run
        self._drive = drive

    def titles(self, log: Path) -> list[DiscTitle]:
        """The Disc titles in the drive, lowest number first. Empty if there's no disc."""
        self._run(["-r", f"--minlength={MIN_LENGTH}", "info", self._drive], log)
        attributes: dict[int, dict[int, str]] = {}
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            match = _TINFO.match(line)
            if match:
                number, attribute, value = match.groups()
                attributes.setdefault(int(number), {})[int(attribute)] = value
        return [DiscTitle(number=number,
                          file_name=found[_FILE_NAME],
                          duration=found.get(_DURATION, ""),
                          chapters=int(found.get(_CHAPTERS, "0")),
                          size=found.get(_SIZE, ""))
                for number, found in sorted(attributes.items())
                # A Disc title with no file name can't be ripped, so it isn't offered.
                if _FILE_NAME in found]

    def rip(self, title: DiscTitle, folder: Path) -> Path:
        """Rip one Disc title into folder and return the Rip's path.

        A Rip whose earlier log shows a finished copy is kept instead of ripped
        again. Raises RipFailed if makemkvcon doesn't finish the copy.
        """
        rip = folder / title.file_name
        log = folder / f"makemkvrip_t{title.number:02d}.log"
        if rip.is_file() and _copy_complete(log):
            return rip
        folder.mkdir(parents=True, exist_ok=True)
        self._run(["-r", "--cache=2048", "--noscan", f"--minlength={MIN_LENGTH}",
                   "mkv", self._drive, str(title.number), str(folder)], log)
        if not _copy_complete(log):
            raise RipFailed(title, log)
        return rip


def _copy_complete(log: Path) -> bool:
    if not log.is_file():
        return False
    return "Copy complete." in log.read_text(encoding="utf-8", errors="replace")

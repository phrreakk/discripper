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
_PLAYLIST = 16
_SEGMENTS = 26
_FILE_NAME = 27

# The volume label (ap_iaVolumeName). The display name (CINFO:2) is often the
# show's name on every disc of a TV box set, so it can't tell discs apart.
_VOLUME_NAME = re.compile(r'^CINFO:32,\d+,"(.*)"$')
_TINFO = re.compile(r'^TINFO:(\d+),(\d+),\d+,"(.*)"$')
# "Title A is equal to title B and was skipped": makemkvcon leaves out playlist A
# because it plays the same segments as B. Its last two fields are A and B.
_EQUAL = re.compile(r'^MSG:3309,.*,"([^"]*)","([^"]*)"$')


@dataclass(frozen=True)
class DiscTitle:
    number: int
    file_name: str
    duration: str
    chapters: int
    size: str
    # The disc file the title plays (a Blu-ray .mpls playlist), and the video
    # segments it plays in order. Language versions of one movie share a length
    # but differ in a segment or two, such as a localized title card.
    playlist: str = ""
    segments: str = ""
    # Playlists makemkvcon skipped because they play exactly this title. On the
    # Planes disc, only the English copy had one.
    duplicates: tuple[str, ...] = ()


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
        duplicates: dict[str, list[str]] = {}
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            equal = _EQUAL.match(line)
            if equal:
                skipped, kept = equal.groups()
                duplicates.setdefault(kept, []).append(skipped)
            match = _TINFO.match(line)
            if match:
                number, attribute, value = match.groups()
                attributes.setdefault(int(number), {})[int(attribute)] = value
        return [DiscTitle(number=number,
                          file_name=found[_FILE_NAME],
                          duration=found.get(_DURATION, ""),
                          chapters=int(found.get(_CHAPTERS, "0")),
                          size=found.get(_SIZE, ""),
                          playlist=found.get(_PLAYLIST, ""),
                          segments=found.get(_SEGMENTS, ""),
                          duplicates=tuple(duplicates.get(found.get(_PLAYLIST, ""), ())))
                for number, found in sorted(attributes.items())
                # A Disc title with no file name can't be ripped, so it isn't offered.
                if _FILE_NAME in found]

    def label(self, log: Path) -> str | None:
        """The Disc label in the info log that titles() wrote, or None if the disc has none."""
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            match = _VOLUME_NAME.match(line)
            if match:
                return match.group(1) or None
        return None

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


def segments_differing(a: DiscTitle, b: DiscTitle) -> int:
    """How many segments one title plays that the other doesn't (the larger of the two counts)."""
    first, second = _segment_set(a.segments), _segment_set(b.segments)
    return max(len(first - second), len(second - first))


def _segment_set(segments: str) -> set[int]:
    """The segments in a makemkvcon segment map such as "1-4,9"."""
    found: set[int] = set()
    for part in segments.split(","):
        if "-" in part:
            low, high = part.split("-")
            found.update(range(int(low), int(high) + 1))
        elif part.strip():
            found.add(int(part))
    return found


def _copy_complete(log: Path) -> bool:
    if not log.is_file():
        return False
    return "Copy complete." in log.read_text(encoding="utf-8", errors="replace")

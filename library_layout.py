"""Library layout: where each encoded file goes so Jellyfin can match it to TMDB.

Pure path arithmetic. Paths are relative to the library root; nothing here
touches the filesystem.

Movie:
    Name (Year) [tmdbid-ID]/Name (Year) [tmdbid-ID] - 2160p.mkv
TV episode:
    Name (Year) [tmdbid-ID]/Season 01/Name S01E03 - 2160p.mkv

Spaces in the Name become underscores, as discripper has always done, so
libraries ripped before this module existed keep their paths.
"""

from pathlib import PurePosixPath
from typing import Literal

from media_lookup import Media

Format = Literal["4k", "1080p"]

# The resolution label Jellyfin shows when a Media has several versions.
_LABELS = {"4k": "2160p", "1080p": "1080p"}


def folder_for(media: Media, season: int | None = None) -> PurePosixPath:
    """The folder a movie's files, or one TV Season's episode files, go in."""
    _check_season(media, season)
    folder = PurePosixPath(_media_folder(media))
    if media.kind == "tv":
        folder /= f"Season {season:02d}"
    return folder


def path_for(media: Media, format: Format, season: int | None = None,
             episode: int | None = None) -> PurePosixPath:
    """The file one encode of a movie, or of one TV episode, is written to."""
    if format not in _LABELS:
        raise ValueError(f"Unknown format: {format!r}")
    label = _LABELS[format]
    folder = folder_for(media, season)
    if media.kind == "movie":
        if episode is not None:
            raise ValueError("A movie has no episode")
        return folder / f"{_media_folder(media)} - {label}.mkv"
    if episode is None:
        raise ValueError("A TV episode needs an episode number")
    return folder / f"{_name(media)} {episode_code(season, episode)} - {label}.mkv"


def episode_code(season: int, episode: int) -> str:
    """How file names and prompts name a TV episode, e.g. "S01E03"."""
    return f"S{season:02d}E{episode:02d}"


def _check_season(media: Media, season: int | None) -> None:
    if media.kind == "movie" and season is not None:
        raise ValueError("A movie has no season")
    if media.kind == "tv" and season is None:
        raise ValueError("A TV show needs a season number")


def _name(media: Media) -> str:
    return "_".join(media.name.split())


def _media_folder(media: Media) -> str:
    return f"{_name(media)} ({media.year}) [tmdbid-{media.tmdb_id}]"

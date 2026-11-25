"""Episode pairing: which TMDB Episode each chosen Disc title becomes.

Pure logic, no prompts and no TMDB calls. A pairing list holds one Pairing per
chosen Disc title, in title-number order.
"""

import re
from dataclasses import dataclass

from disc import DiscTitle
from media_lookup import Episode

# A Disc title whose length is more than this many minutes off its Episode's
# TMDB runtime is flagged, as it may be the wrong Episode. It only warns.
RUNTIME_TOLERANCE_MINUTES = 5


@dataclass(frozen=True)
class Pairing:
    """One Disc title and the Episode of season it becomes.

    episode is None when the title won't be ripped: skipped is True when the
    user skipped it, and False when it's past the end of the Season. explicit is
    True when the user set this pairing themselves.
    """
    title: DiscTitle
    season: int
    episode: Episode | None
    skipped: bool = False
    explicit: bool = False


def propose(titles, season, episodes, encoded):
    """Pair titles in order with episodes, from the first Episode whose number isn't in encoded."""
    start = next((i for i, episode in enumerate(episodes) if episode.number not in encoded),
                 len(episodes))
    return [Pairing(title, season, _at(episodes, start + i)) for i, title in enumerate(titles)]


def _at(episodes, index):
    return episodes[index] if index < len(episodes) else None


def reassign(pairings, title_number, season, episode_number, episodes):
    """Put Disc title title_number on Episode episode_number of season, whose Episodes are episodes.

    Every later title the user hasn't set themselves follows on with the next
    Episodes of that Season, in order. Raises ValueError if title_number isn't
    paired or episode_number isn't in episodes.
    """
    at = _index_of(pairings, title_number)
    start = next((i for i, episode in enumerate(episodes) if episode.number == episode_number), None)
    if start is None:
        raise ValueError(f"Season {season} has no Episode {episode_number}")
    result = list(pairings)
    result[at] = Pairing(pairings[at].title, season, episodes[start], explicit=True)
    following = start + 1
    for i in range(at + 1, len(result)):
        if not result[i].explicit:
            result[i] = Pairing(result[i].title, season, _at(episodes, following))
            following += 1
    return result


def _index_of(pairings, title_number):
    for i, pairing in enumerate(pairings):
        if pairing.title.number == title_number:
            return i
    raise ValueError(f"Disc title {title_number} isn't being ripped")


def skip(pairings, title_number):
    """Skip Disc title title_number; the other titles keep their Episodes."""
    at = _index_of(pairings, title_number)
    result = list(pairings)
    result[at] = Pairing(pairings[at].title, pairings[at].season, None, skipped=True, explicit=True)
    return result


def shared(pairings):
    """The Episodes more than one Disc title is paired with, as {(season, episode): [title numbers]}."""
    titles = {}
    for pairing in pairings:
        if pairing.episode is not None:
            titles.setdefault((pairing.season, pairing.episode.number), []).append(pairing.title.number)
    return {episode: numbers for episode, numbers in titles.items() if len(numbers) > 1}


def flags(pairing, has_encode, pairings=()):
    """Warnings to show beside a pairing.

    has_encode(season, episode) tells if that Episode has an Encode. pairings,
    the whole pairing list, lets the other titles on the same Episode be named.
    """
    if pairing.episode is None:
        return ["skipped" if pairing.skipped else "no episode"]
    found = [f"also title {number}"
             for number in shared(pairings).get((pairing.season, pairing.episode.number), [])
             if number != pairing.title.number]
    seconds = _seconds(pairing.title.duration)
    runtime = pairing.episode.runtime
    if runtime is not None and seconds is not None \
            and abs(seconds - runtime * 60) > RUNTIME_TOLERANCE_MINUTES * 60:
        found.append(f"runtime {seconds // 60} min, TMDB {runtime} min")
    if has_encode(pairing.season, pairing.episode.number):
        found.append("already encoded")
    return found


def _seconds(duration):
    """The seconds in a makemkvcon duration such as "0:22:10", or None if it isn't one."""
    try:
        hours, minutes, seconds = (int(part) for part in duration.split(":"))
    except ValueError:
        return None
    return hours * 3600 + minutes * 60 + seconds


@dataclass(frozen=True)
class Change:
    """A typed change to the pairing: Disc title title_number becomes Episode episode of season.

    season and episode are both None to skip the Disc title.
    """
    title_number: int
    season: int | None
    episode: int | None


_CHANGE = re.compile(r"(\d+)\s*=\s*(?:(-)|(\d+)|[sS](\d+)[eE](\d+))")


def parse_change(typed, season):
    """The Change in typed, such as "3=5", "3=S0E1" or "3=-", or None if it isn't one.

    A bare Episode number, as in "3=5", is in season, the Season picked for the run.
    """
    match = _CHANGE.fullmatch(typed.strip())
    if not match:
        return None
    title, dash, episode, other_season, other_episode = match.groups()
    if dash:
        return Change(int(title), None, None)
    if episode:
        return Change(int(title), season, int(episode))
    return Change(int(title), int(other_season), int(other_episode))

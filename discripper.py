#!/usr/bin/env python

import re
import sys
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import argparse
from dotenv import dotenv_values
from prettytable import PrettyTable
import library_layout
from library_layout import Format
from disc import Disc, DiscTitle, RipFailed, segments_differing
import episode_pairing
from encoder import ENCODERS, EncodeFailed, Encoder
from media_lookup import LookupFailed, Media, MediaLookup, NoResults, TooManyResults, tmdb_fetch
from tool_run import tool


# The Formats each --format choice encodes, in order.
FORMATS = {"4k": ["4k"], "1080p": ["1080p"], "all": ["4k", "1080p"]}


def tmdbKey(envFile=".env"):
    """The TMDB API key from envFile; exits with how to set it if it's missing or blank."""
    key = dotenv_values(envFile).get("TMDB_API_KEY")
    if not key:
        print(f"No TMDB_API_KEY found in {Path(envFile).resolve()}.")
        print("Add a line like this to that file: TMDB_API_KEY=<your TMDB read token>")
        sys.exit(1)
    return key


def getRequirements():
    """Return the paths to makemkvcon and HandBrakeCLI; exit if either isn't on PATH."""
    paths = []
    for app in ["makemkvcon", "HandBrakeCLI"]:
        path = shutil.which(app)
        if path is None:
            print("The path to " + app + " was not found.")
            sys.exit(1)
        paths.append(path)
    return paths


def showDiscTitles(titles):
    table = PrettyTable()
    table.field_names = ["Title", "Duration", "Chapters", "Size", "Playlist",
                         "Segments differ from", "File"]
    table.align = "l"
    for title in titles:
        table.add_row([title.number, title.duration, title.chapters, title.size, playlistCell(title),
                       sameLengthDifferences(title, titles), title.file_name])
    print(table)


def playlistCell(title):
    """The title's playlist, then any playlists makemkvcon skipped as equal to it, e.g. "00800.mpls (+00803)"."""
    if not title.duplicates:
        return title.playlist
    return f"{title.playlist} (+{', '.join(Path(name).stem for name in title.duplicates)})"


def sameLengthDifferences(title, titles):
    """How many segments title differs by from each other title of its length, e.g. "title 3 in 2"."""
    others = [other for other in titles
              if other.number != title.number and other.duration == title.duration
              and other.segments and title.segments]
    return ", ".join(f"title {other.number} in {segments_differing(title, other)}"
                     for other in others)


def askDiscTitle(prompt, titles):
    """Ask until the number of one of titles is typed; return that Disc title."""
    byNumber = {str(title.number): title for title in titles}
    while True:
        chosen = input(prompt).strip()
        if chosen in byNumber:
            return byNumber[chosen]
        print("You need to input a title number from the table: " + ", ".join(byNumber))


def pickById(prompt, columns, rows):
    """Show rows as a table and ask until a listed TMDB id is typed; return that row's item.

    rows is a list of (tmdb_id, item, cells), shown in the order given.
    """
    table = PrettyTable()
    table.field_names = columns
    table.align = "l"
    items = {}
    for tmdbId, item, cells in rows:
        table.add_row(cells)
        items[str(tmdbId)] = item
    print(table)
    while True:
        print("")
        chosen = input(prompt)
        if chosen == "":
            print("You need to input an ID from the table. ")
            print(table)
        elif chosen not in items:
            print("You need to select a valid ID from the table. ")
            print(table)
        else:
            return items[chosen]


def askYear(kind):
    """Ask for an optional production year until it's blank or a year from 1900 to this year."""
    while True:
        year = input("What is the {} production year? (Optional) ".format(kind))
        if year == "":
            return year
        try:
            number = int(year)
        except ValueError:
            number = None
        if number is not None and 1900 <= number <= datetime.today().year:
            return str(number)
        print("You need a valid year ")


def chooseMedia(lookup, kind, name, year, tmdbId):
    """Find the Media being ripped (by search, or by TMDB id) and, for TV, its Season.

    Returns (Media, Season or None). Exits with a message if the lookup fails.
    """
    try:
        return _chooseMedia(lookup, kind, name, year, tmdbId)
    except LookupFailed as err:
        print(f"TMDB request failed: {err}")
    except NoResults:
        print("Zero results...")
        print("Try to add more text to the title search")
    except TooManyResults as err:
        print("Too many results...")
        if err.year_given:
            print("Try to add more text to the title search")
        else:
            print("Please add a year to narrow down results")
    sys.exit(1)


def _chooseMedia(lookup, kind, name, year, tmdbId):
    if tmdbId is not None:
        media = lookup.get(kind, tmdbId)
    else:
        media = pickById(
            "Which {} is being ripped? ".format(kind),
            ["ID", "Name", "Year", "Popularity"],
            [(r.media.tmdb_id, r.media, [r.media.tmdb_id, r.media.name, r.media.year, r.popularity])
             for r in lookup.find(kind, name, year)])
    if kind != "tv":
        return media, None
    print("Search season information...")
    season = pickById(
        "Which {} season is being ripped? ".format(kind),
        ["ID", "Season", "Season #", "Air Date"],
        [(s.tmdb_id, s, [s.tmdb_id, s.name, s.number, s.air_date]) for s in lookup.seasons(media)])
    return media, season


def pairEpisodes(titles, media, season, lookup, library, formats):
    """Pair the chosen Disc titles with Episodes of the show, letting the user change the pairing.

    season is the Season number picked for the run; the proposal starts at its
    first Episode with an Encode at no Format under library. Accepting asks once
    before replacing Encodes at formats, the Formats this run encodes at.
    Returns the accepted Pairings, one per Disc title, in title-number order.
    """
    episodes = {season: lookup.episodes(media, season)}

    def encodedAt(seasonNumber, episode, atFormats):
        return any((library / library_layout.path_for(media, format, seasonNumber, episode)).is_file()
                   for format in atFormats)

    def hasEncode(seasonNumber, episode):
        return encodedAt(seasonNumber, episode, FORMATS["all"])

    def replaces(seasonNumber, episode):
        return encodedAt(seasonNumber, episode, formats)

    pairings = episode_pairing.propose(
        titles, season, episodes[season],
        encoded={e.number for e in episodes[season] if hasEncode(season, e.number)})
    showPairings(pairings, hasEncode)
    while True:
        typed = input("Press Enter to accept, or change a title such as 3=5, 3=S0E1 or 3=-: ")
        if typed.strip() == "":
            if _noSharedEpisodes(pairings) and _confirmReplacing(pairings, replaces):
                return pairings
            continue
        change = episode_pairing.parse_change(typed, season)
        if change is None:
            print("You need a change such as 3=5, 3=S0E1 or 3=-, or Enter to accept.")
            continue
        try:
            pairings = _applyChange(pairings, change, lambda number: _seasonEpisodes(
                episodes, lookup, media, number))
        except (ValueError, LookupFailed) as err:
            print(err)
            continue
        showPairings(pairings, hasEncode)


def _seasonEpisodes(episodes, lookup, media, season):
    """The Episodes of season, fetched from TMDB the first time it's asked for and kept in episodes."""
    if season not in episodes:
        try:
            episodes[season] = lookup.episodes(media, season)
        except LookupFailed as err:
            raise LookupFailed(f"Couldn't fetch Season {season} from TMDB: {err}") from err
    return episodes[season]


def _noSharedEpisodes(pairings):
    """True if no two Disc titles are paired with one Episode; otherwise say which are."""
    shared = episode_pairing.shared(pairings)
    for (seasonNumber, episode), numbers in shared.items():
        listed = ", ".join(str(number) for number in numbers[:-1]) + f" and {numbers[-1]}"
        print(f"Disc titles {listed} share {library_layout.episode_code(seasonNumber, episode)}. "
              "Change or skip all but one of them.")
    return not shared


def _applyChange(pairings, change, episodesOf):
    """The pairings with change made; episodesOf(season) gives the Episodes of a Season."""
    if change.episode is None:
        return episode_pairing.skip(pairings, change.title_number)
    return episode_pairing.reassign(pairings, change.title_number, change.season, change.episode,
                                    episodesOf(change.season))


def _confirmReplacing(pairings, replaces):
    """Ask once whether to replace the Encodes this run would overwrite; True if it overwrites none.

    replaces(season, episode) tells if encoding that Episode overwrites an Encode.
    """
    replacing = [library_layout.episode_code(p.season, p.episode.number) for p in pairings
                 if p.episode is not None and replaces(p.season, p.episode.number)]
    if not replacing:
        return True
    answer = input(f"Replace the existing Encodes of {', '.join(replacing)}? [y/N] ")
    return answer.strip().lower() in ("y", "yes")


def showPairings(pairings, hasEncode):
    """Print each Disc title with its Episode and flags; hasEncode(season, episode) tells if it has an Encode."""
    table = PrettyTable()
    table.field_names = ["Title", "Duration", "Episode", "Name", "Flags"]
    table.align = "l"
    for pairing in pairings:
        episode = pairing.episode
        table.add_row([pairing.title.number, pairing.title.duration,
                       library_layout.episode_code(pairing.season, episode.number) if episode else "-",
                       episode.name if episode else "",
                       ", ".join(episode_pairing.flags(pairing, hasEncode, pairings))])
    print(table)


def encodeFullMkv(encoder, rip, media, parentFolder, season, episode, formats):
    """Encode one Rip at each of formats into the Library layout under parentFolder.

    season and episode are the Rip's Season and Episode numbers for TV, and None
    for a movie. Returns the encoded paths, one per Format, in the order of formats.
    """
    parentFolder = Path(parentFolder)
    (parentFolder / library_layout.folder_for(media, season)).mkdir(parents=True, exist_ok=True)
    encoded = []
    for format in formats:
        print(f"Encoding {format} file...Please wait...")
        output = parentFolder / library_layout.path_for(media, format, season, episode)
        encoded.append(encoder.encode(rip, output, format))
    return encoded


def parseArgs(argv):
    """Parse discripper's command line arguments."""
    parser = argparse.ArgumentParser(
        prog='discripper',
        description='This program is a wrapper around makemkvcon and Handbrake while also receiving media data from TMDB API'
        )
    
    parser.add_argument("-t", "--title", help="(Partial) Title of the media")
    parser.add_argument("-y", "--year", type=int, help="Release year of the media")
    parser.add_argument("-f", "--format", default='all', choices=['4k', '1080p', 'all'], help="Format of the output file(s).")
    parser.add_argument("-m", "--media", default='movie', choices=['movie', 'tv'], help="Media format of movie or tv.")
    parser.add_argument("--encoder", default=ENCODERS[0], choices=ENCODERS,
                        help="HandBrake video encoder for every encode (default: %(default)s).")
    parser.add_argument("--tmdbid", type=int, help="The Movie DB ID of the media")
    parser.add_argument("FOLDER", help="Root directory for the ripped media")
    return parser.parse_args(argv)

def chooseDiscTitles(kind, titles):
    """Ask which Disc titles to rip: one for a movie, a list such as "1-4,6" for TV."""
    showDiscTitles(titles)
    if kind == "movie":
        print("The title with the most chapters is probably the one you want to rip. ")
        print("Titles of the same length are often language versions of the movie. Two that")
        print("differ in only a few segments usually differ just in the title card and credits.")
        print("A playlist with a (+duplicate) may be the disc's default copy; on Planes it was English.")
        return [askDiscTitle("Which single title would you like to rip? ", titles)]
    return askDiscTitleList("Which titles would you like to rip, such as 1-4,6? ", titles)


def askDiscTitleList(prompt, titles):
    """Ask until a list of Disc title numbers and ranges, such as "1-4,6", names only titles in the table.

    Returns those Disc titles in title-number order.
    """
    byNumber = {title.number: title for title in titles}
    listed = ", ".join(str(number) for number in byNumber)
    while True:
        ranges = parseNumberList(input(prompt))
        if ranges is None:
            print("You need title numbers and ranges from the table, such as 1-4,6: " + listed)
            continue
        missing = [label for first, last in ranges for label in _missingLabels(first, last, byNumber)]
        if missing:
            print(f"Not in the table: {', '.join(missing)}. The titles are: {listed}")
            continue
        return [byNumber[number] for number in sorted(byNumber)
                if any(first <= number <= last for first, last in ranges)]


def _missingLabels(first, last, byNumber):
    """Labels for the numbers from first to last that aren't in byNumber.

    A range longer than the table must hold a missing number, so it's labelled whole, e.g. "1-999".
    """
    if last - first >= len(byNumber):
        return [f"{first}-{last}"]
    return [str(number) for number in range(first, last + 1) if number not in byNumber]


_NUMBER_OR_RANGE = re.compile(r"(\d+)(?:\s*-\s*(\d+))?")


def parseNumberList(typed):
    """The (first, last) ranges in a list such as "1-4,6", or None if it isn't one."""
    ranges = []
    for part in typed.split(","):
        match = _NUMBER_OR_RANGE.fullmatch(part.strip())
        if not match:
            return None
        first, last = int(match[1]), int(match[2] or match[1])
        if last < first:
            return None
        ranges.append((first, last))
    return ranges


@dataclass(frozen=True)
class PlannedTitle:
    """A Disc title in a Rip plan, with the Season and Episode it becomes for TV (None for a movie)."""
    title: DiscTitle
    season: int | None = None
    episode: int | None = None


@dataclass(frozen=True)
class RipPlan:
    """Everything one run rips and encodes, settled before the first Disc title is ripped.

    season is the Season number picked for TV and None for a movie; a TV title
    can be paired with another Season's Episode. titles holds only the Disc
    titles to rip. folder is where the Rips go; library is the root the Encodes'
    Library layout goes under. They're the same for a movie; a TV disc's folder
    is inside library.
    """
    media: Media
    season: int | None
    titles: list[PlannedTitle]
    formats: list[Format]
    folder: Path
    library: Path

    def summary(self):
        media = self.media
        season = "" if self.season is None else f" - Season {self.season}"
        return (f"We are going to rip {media.name}{season} ({media.year}) "
                f"with TMDBID [tmdbid-{media.tmdb_id}] to {self.folder}")


def askTitle(kind):
    """Ask until a search term for the Media is typed."""
    while True:
        name = input("What is the {} title? ".format(kind))
        if name != "":
            return name
        print("You need a search term ")


def askDiscNumber():
    """Ask until a whole number from 1 up is typed, for a disc with no Disc label."""
    while True:
        number = input("This disc has no label. Which disc of the set is it? ").strip()
        if number.isdigit() and int(number) >= 1:
            return int(number)
        print("You need a disc number, such as 1 ")


def planRip(args, lookup, disc):
    """Ask everything a run needs and return its RipPlan. Exits if no Disc titles are found.

    Creates the rip folder. makemkvcon's title listing log is kept in the Media's
    folder; for TV, the Rips go in a folder for this disc inside it, named after
    its Disc label, or "Disc N" when it has none. For TV, each chosen Disc title
    is paired with an Episode, and skipped titles are left out of the plan.
    Exits if TMDB can't be reached for the Season's Episodes.
    """
    name, year = "", ""
    if args.tmdbid is None:
        name = args.title if args.title is not None else askTitle(args.media)
        year = str(args.year) if args.year is not None else askYear(args.media)
    media, season = chooseMedia(lookup, args.media, name, year, args.tmdbid)

    library = Path(args.FOLDER) / "_".join(media.name.split())
    library.mkdir(parents=True, exist_ok=True)
    infoLog = library / "makemkvinfo.log"
    titles = disc.titles(infoLog)
    if not titles:
        print("makemkvcon found no titles to rip. Check that a disc is in the drive.")
        print(f"Please review {infoLog} for additional details.")
        sys.exit(1)
    print("Titles: " + str(len(titles)))
    folder = library
    if args.media == "tv":
        # Discs of one Season can share Rip file names, so each disc gets its own folder.
        folder = library / (disc.label(infoLog) or f"Disc {askDiscNumber()}")
        folder.mkdir(exist_ok=True)
    chosen = chooseDiscTitles(args.media, titles)
    planned = [PlannedTitle(title) for title in chosen]
    if args.media == "tv":
        try:
            pairings = pairEpisodes(chosen, media, season.number, lookup, library,
                                    FORMATS[args.format])
        except LookupFailed as err:
            print(f"TMDB request failed: {err}")
            sys.exit(1)
        planned = [PlannedTitle(p.title, p.season, p.episode.number)
                   for p in pairings if p.episode is not None]
    return RipPlan(media=media, season=season.number if season else None, titles=planned,
                   formats=FORMATS[args.format], folder=folder, library=library)


def runRip(plan, disc, encoder):
    """Rip each Disc title in plan, then encode each Rip at each Format. Exits if a step fails."""
    for planned in plan.titles:
        try:
            rip = disc.rip(planned.title, plan.folder)
            print(f"Rip completed: {rip}")
            for encoded in encodeFullMkv(encoder, rip, plan.media, plan.library, planned.season,
                                         planned.episode, plan.formats):
                print(f"Encode completed: {encoded}")
        except RipFailed as err:
            print("Disc did not complete.")
            print(f"Please review {err.log} for additional details.")
            sys.exit(1)
        except EncodeFailed as err:
            print("Encode did not complete.")
            print(f"Please review {err.log} for additional details.")
            sys.exit(1)


def main():
    args = parseArgs(sys.argv[1:])
    makemkvcon, handBrake = getRequirements()
    disc = Disc(tool(makemkvcon))
    plan = planRip(args, MediaLookup(tmdb_fetch(tmdbKey())), disc)
    print(plan.summary())
    print("Ripping...Please wait...")
    runRip(plan, disc, Encoder(tool(handBrake), args.encoder))


if __name__ == "__main__":
    main()

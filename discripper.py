#!/usr/bin/env python

import sys
import shutil
from datetime import datetime
from pathlib import Path
import argparse
from dotenv import dotenv_values
from prettytable import PrettyTable
import library_layout
from disc import Disc, RipFailed
from encoder import ENCODERS, EncodeFailed, Encoder
from media_lookup import LookupFailed, MediaLookup, NoResults, TooManyResults, tmdb_fetch
from tool_run import tool


# The Formats each --format choice encodes, in order.
FORMATS = {"4k": ["4k"], "1080p": ["1080p"], "all": ["4k", "1080p"]}


def loadEnvFile():
    global dotenv
    dotenv = dotenv_values(".env")


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
    table.field_names = ["Title", "Duration", "Chapters", "Size", "File"]
    table.align = "l"
    for title in titles:
        table.add_row([title.number, title.duration, title.chapters, title.size, title.file_name])
    print(table)


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


def episodeNumber(seasonFolder, rip):
    """The episode number of rip in a Season, counting rips in the order they were first encoded.

    Each Season folder keeps episode.list, one Rip path per line. A Rip is matched
    by file name and added at the end the first time it's seen.
    """
    listing = Path(seasonFolder) / "episode.list"
    lines = listing.read_text(encoding="utf-8").splitlines() if listing.exists() else []
    names = [Path(line).name for line in lines if line.strip()]
    if rip.name not in names:
        with open(listing, "a", encoding="utf-8") as file:
            file.write(str(rip) + "\n")
        names.append(rip.name)
    return names.index(rip.name) + 1


def encodeFullMkv(encoder, rip, media, parentFolder, season, formats):
    """Encode one Rip at each of formats into the Library layout under parentFolder.

    season is the Season number for TV and None for a movie. Returns the encoded
    paths, one per Format, in the order of formats.
    """
    parentFolder = Path(parentFolder)
    seasonFolder = parentFolder / library_layout.folder_for(media, season)
    seasonFolder.mkdir(parents=True, exist_ok=True)
    episode = None
    if media.kind == "tv":
        episode = episodeNumber(seasonFolder, rip)
        print(f"Episode {episode}")
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
    """Ask which Disc titles to rip: one for a movie, a first-to-last range for TV."""
    showDiscTitles(titles)
    if kind == "movie":
        print("The title with the most chapters is probably the one you want to rip. ")
        return [askDiscTitle("Which single title would you like to rip? ", titles)]
    start = askDiscTitle("Which title should START the rip? ", titles)
    end = askDiscTitle("Which title should END the rip? ",
                       [title for title in titles if title.number >= start.number])
    return [title for title in titles if start.number <= title.number <= end.number]


def ripAndEncode(disc, encoder, titles, media, ripFolder, season, formats):
    """Rip each Disc title, then encode each Rip at each Format. Exits if a step fails."""
    for title in titles:
        try:
            rip = disc.rip(title, ripFolder)
            print(f"Rip completed: {rip}")
            for encoded in encodeFullMkv(encoder, rip, media, ripFolder, season, formats):
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
    loadEnvFile()
    args = parseArgs(sys.argv[1:])
    makemkvcon, handBrake = getRequirements()

    mediaTitle = ""
    mediaYear = ""
    if args.tmdbid is None:
        if args.title is None:
            while True:
                mediaTitle = input("What is the {} title? ".format(args.media))
                if mediaTitle == "":
                    print("You need a search term ")
                else:
                    break
        else:
            mediaTitle = args.title

        if args.year is None:
            mediaYear = askYear(args.media)
        else:
            mediaYear = args.year

    # Get movie/show info
    lookup = MediaLookup(tmdb_fetch(dotenv["TMDB_API_KEY"]))
    media, season = chooseMedia(lookup, args.media, mediaTitle, mediaYear, args.tmdbid)

    ripFolder = Path(args.FOLDER) / "_".join(media.name.split())
    ripFolder.mkdir(parents=True, exist_ok=True)

    disc = Disc(tool(makemkvcon))
    infoLog = ripFolder / "makemkvinfo.log"
    titles = disc.titles(infoLog)
    if not titles:
        print("makemkvcon found no titles to rip. Check that a disc is in the drive.")
        print(f"Please review {infoLog} for additional details.")
        sys.exit(1)
    print("Titles: " + str(len(titles)))
    chosen = chooseDiscTitles(args.media, titles)

    if season:
        print(f"We are going to rip {media.name} - Season {season.number} ({media.year}) with TMDBID [tmdbid-{media.tmdb_id}] to {ripFolder}")
    else:
        print(f"We are going to rip {media.name} ({media.year}) with TMDBID [tmdbid-{media.tmdb_id}] to {ripFolder}")
    print("Ripping...Please wait...")
    ripAndEncode(disc, Encoder(tool(handBrake), args.encoder), chosen, media, ripFolder,
                 season.number if season else None, FORMATS[args.format])


if __name__ == "__main__":
    main()

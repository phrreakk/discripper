#!/usr/bin/env python

import sys
import os
import subprocess
import re
import shutil
from datetime import datetime
import argparse
import json
from dotenv import load_dotenv, dotenv_values
from prettytable import PrettyTable
import library_layout
from media_lookup import LookupFailed, MediaLookup, NoResults, TooManyResults, tmdb_fetch


# HandBrake encoders --encoder accepts: Intel QSV (the default), NVIDIA NVENC, and software x265.
ENCODERS = ["qsv_h265_10bit", "nvenc_h265_10bit", "x265_10bit"]


def loadEnvFile():
    global dotenv
    dotenv = dotenv_values(".env")
    
    # Debug
    # print(f"Config: {dotenv["TMDB_API_KEY"]}")
    # sys.exit(0)

def getRequirements():
    ripApp = "makemkvcon"
    global pathRipApp
    pathRipApp = shutil.which(ripApp)
    
    if pathRipApp is None:
        print("The path to " + ripApp + " was not found.")
        sys.exit(1)
        
    transcodeApp = "HandBrakeCLI"
    global pathTranscodeApp
    pathTranscodeApp = shutil.which(transcodeApp)
    
    if pathTranscodeApp is None:
        print("The path to " + transcodeApp + " was not found.")
        sys.exit(1)
    
    return
        
    
def getDiscInfo(folder, title):
    global titles
    titles = 0
    fullPath = folder + "/" + "_".join(title.split())
    
    if not os.path.exists(fullPath):
        os.makedirs(fullPath)
    
    with open(fullPath + "/" + "/makemkvinfo.log", "w") as file:
        process = subprocess.Popen([pathRipApp, 'info', 'disc:0'], stdout=file, stderr=file)
        process.wait()
    
    with open(fullPath + "/" + "/makemkvinfo.log", "r") as file:   
        for line in file:
            line.strip()
            if re.search(r"skipped", line):
              continue
            # This var is there so it limits the input validation below
            if re.match(r"Title ", line):
              titles += 1
              if args.media == "tv":
                print(line)
            if args.media == "movie":
              print(line)
    return


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


def ripFullMkv(folder, title):
    print("Ripping...Please wait...")
    
    # Info returns different results with -r and without
    ripFileName = None
    process = subprocess.Popen([pathRipApp, '-r', 'info', 'disc:0'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for line in process.stdout: 
        search = re.search(rf'^TINFO:{title},27,0,\"(.+)\"', line)
        if search:
            ripFileName = search.group(1)
            # print(f"Match found: {ripFileName}")

    if ripFileName is None:
        print(f"makemkvcon did not report a file name for title {title}.")
        print("Check the title number against the list shown earlier, and that the disc is still in the drive.")
        sys.exit(1)

    if not os.path.isfile(folder + "/" + ripFileName):
        with open(folder + "/" + "/makemkvrip.log", "w") as file:
            process = subprocess.Popen([pathRipApp, 'mkv', '--cache=2048', '--noscan', '--minlength=300', '-r', 'disc:0', title, folder], stdout=file, stderr=file)
            process.wait()

    # Might have a directory in the end of the file, we'll see
    
    with open(folder + "/" + "/makemkvrip.log", "r") as file:   
        for line in file:
            line.strip()
            if re.search(r"Copy complete.", line):
                return ripFileName
        else:
            print("Disc did not complete.")
            print(f"Please review {folder}/makemkvrip.log for additional details.")
            sys.exit(1)
    

def encodeFullMkv(fullRipPath, media, parentFolder, season, encoder):
    """Encode one rip into the Library layout under parentFolder.

    season is the Season number for TV and None for a movie. encoder is the
    HandBrake video encoder (one of ENCODERS) used for every encode.
    """
    preset4k = "H.265 MKV 2160p60 4K"
    preset1080p = "H.265 MKV 1080p30"
    encodeFullFile4k = ""
    encodeFullFile1080p = ""
    found = 0
    episodeNum = None
    transcodePath = os.path.join(parentFolder, library_layout.folder_for(media, season))
    if not os.path.isdir(transcodePath):
        os.makedirs(transcodePath)
    if media.kind == "tv":
        episodeNum = 0
        if os.path.exists(transcodePath + "/" + "episode.list"):
            with open(transcodePath + "/" + "episode.list", 'r') as file:
                for line in file:
                    episodeNum += 1
                    if found < 1:
                        if fullRipPath[-20:] in line:
                            print("Episode already exists in the file.")
                            found = 1
            if found == 0:
                # Write the string to the file
                with open(transcodePath + "/" + "episode.list", 'a') as file:
                    file.write(fullRipPath + '\n')
        else:
            # Write the string to the file
            with open(transcodePath + "/" + "episode.list", 'w') as file:
                file.write(fullRipPath + '\n')

        if found == 0:
            # How many episodes are there so far
            with open(transcodePath + "/" + "episode.list", 'r') as f:
                episodeNum = sum(1 for line in f)
            print('Total number of episodes:', episodeNum)

    outputTranscodePath4k = os.path.join(parentFolder, library_layout.path_for(media, "4k", season, episodeNum))
    outputTranscodePath1080p = os.path.join(parentFolder, library_layout.path_for(media, "1080p", season, episodeNum))

    
    if args.format in ['4k', 'all']:
        print("Encoding 4k file...Please wait...")
        if found == 1:
            print("Encoded file found: " + outputTranscodePath4k)
            encodeFullFile4k = outputTranscodePath4k
            return encodeFullFile4k, encodeFullFile1080p
        # Debug
        # print(f"Path: {outputTranscodePath4k}")
        # sys.exit(0)
        if not os.path.isfile(outputTranscodePath4k):
            with open(transcodePath + "/" + "/handbrakemkv4k.log", "w") as file:
                print(f"Start: {datetime.now()}", file=file)
                process = subprocess.Popen([pathTranscodeApp, "-Z",  preset4k, "-e", encoder, "-i", fullRipPath, "-o", outputTranscodePath4k], stdout=file, stderr=file)
                process.wait()
                print(f"End: {datetime.now()}", file=file)
                
        with open(transcodePath + "/" + "/handbrakemkv4k.log", "r") as file:
            for line in file:
                line.strip()
                search = re.search(r'\"File\":\s\"(.+)\"', line)
                if search:
                    encodeFullFile4k = search.group(1)
                if re.search(r'Encode done!', line):
                    break 
            else:
                print("Encode did not complete.")
                print(f"Please review {transcodePath}/handbrakemkv4k.log for additional details.")
                sys.exit(1)
    
    if args.format in ['1080p', 'all']:
        print("Encoding 1080p file...Please wait...")
        if found == 1:
            print("Encoded file found: " + outputTranscodePath1080p)
            encodeFullFile1080p = outputTranscodePath1080p
            return encodeFullFile4k, encodeFullFile1080p
        if not os.path.isfile(outputTranscodePath1080p):
            with open(transcodePath + "/" + "/handbrakemkv1080p.log", "w") as file:
                print(f"Start: {datetime.now()}", file=file)
                process = subprocess.Popen([pathTranscodeApp, "-Z",  preset1080p, "-e", encoder, "-i", fullRipPath, "-o", outputTranscodePath1080p], stdout=file, stderr=file)
                process.wait()
                print(f"End: {datetime.now()}", file=file)
        
        with open(transcodePath + "/" + "/handbrakemkv1080p.log", "r") as file:
            for line in file:
                line.strip()
                search = re.search(r'\"File\":\s\"(.+)\"', line)
                if search:
                    encodeFullFile1080p = search.group(1)
                if re.search(r'Encode done!', line):
                    break 
            else:
                print("Encode did not complete.")
                print(f"Please review {transcodePath}/handbrakemkv1080p.log for additional details.")
                sys.exit(1)
    
    return encodeFullFile4k, encodeFullFile1080p
    
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


def main():
    loadEnvFile()
    
    global args
    args = parseArgs(sys.argv[1:])
    
    # Debug
    # print(f"Title: {args.title}")
    # print(f"Year: {args.year}")
    # print(f"Media: {args.media}")
    # print(f"TMDB ID: {args.tmdbid}")
    # print(f"Folder: {args.FOLDER}")
    # sys.exit(0)
    
    # See if requirements are satisfied
    getRequirements()
    
    # Debug    
    # print("RIP " + discTitle)
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

    mediaFolder = args.FOLDER
    if not os.path.isdir(mediaFolder):
        os.makedirs(mediaFolder)
    # Debug
    # print(f"Folder: {mediaFolder}")
    # print(f"ID: {media.tmdb_id}")
    # print(f"Title: {media.name}")
    # print(f"Year: {media.year}")
    # sys.exit(0)
    
    getDiscInfo(mediaFolder, media.name)
    
    if args.media == "movie":
      print("Titles: " + str(titles))
      print("The title with the most sections is probably the one you want to rip. ")
      while True:
          discTitle = input("Which single title would you like to rip? ")
          if int(discTitle) >= 0 and int(discTitle) < titles:
              break
    elif args.media == "tv":
        print("Titles: " + str(titles))
        while True:
            startDiscTitle = input("Which title should START the rip? ")
            if int(startDiscTitle) >= 0 and int(startDiscTitle) < titles:
                next
            endDiscTitle = input("Which title should END the rip? ")
            if int(endDiscTitle) >= int(startDiscTitle) and int(endDiscTitle) < titles:
                break
        # print(int(startDiscTitle))
        # print(int(endDiscTitle))
        # sys.exit(0)
    
    if args.media == "movie":
        ripFolder = mediaFolder + "/" + "_".join(media.name.split())     
        print(f"We are going to rip {media.name} ({media.year}) with TMDBID [tmdbid-{media.tmdb_id}] to {ripFolder}")
        ripFile = ripFullMkv(ripFolder, discTitle)
        fullRipFile = ripFolder + "/" + ripFile
        print(f"Rip completed: {fullRipFile}")
        encodeFullPath4k, encodeFullPath1080p = encodeFullMkv(fullRipFile, media, ripFolder, season.number if season else None, args.encoder)
        if args.format in ['4k', 'all']:
            print(f"Encode completed: {encodeFullPath4k}")
        if args.format in ['1080p', 'all']:
            print(f"Encode completed: {encodeFullPath1080p}")
    elif args.media == "tv":
        ripFolder = mediaFolder + "/" + "_".join(media.name.split())
        print(f"We are going to rip {media.name} - Season {season.number} ({media.year}) with TMDBID [tmdbid-{media.tmdb_id}] to {ripFolder}")
        for title in range(int(startDiscTitle), int(endDiscTitle) + 1):
            ripFile = ripFullMkv(ripFolder, str(title))
            fullRipFile = ripFolder + "/" + ripFile
            print(f"Rip completed: {fullRipFile}")
            encodeFullPath4k, encodeFullPath1080p = encodeFullMkv(fullRipFile, media, ripFolder, season.number if season else None, args.encoder)
            if args.format in ['4k', 'all']:
                print(f"Encode completed: {encodeFullPath4k}")
            if args.format in ['1080p', 'all']:
                print(f"Encode completed: {encodeFullPath1080p}")

if __name__ == "__main__":
    main()

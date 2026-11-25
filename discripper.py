#!/usr/bin/env python

import sys
import os
import subprocess
import re
import shutil
import requests
from requests.exceptions import HTTPError
from datetime import datetime
import argparse
import json
from dotenv import load_dotenv, dotenv_values
from prettytable import PrettyTable


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


def getMediaInfo(title, year):
    mediaSeasonId = ""
    if args.media == "movie":
      if args.tmdbid is None:
        searchTitle = "%20".join(title.split())
        
        if year == "" or year is None:
            url = "https://api.themoviedb.org/3/search/movie?query=" + searchTitle + "&include_adult=false&language=en-US&page=1"
        else:
            url = "https://api.themoviedb.org/3/search/movie?query=" + searchTitle + "&include_adult=false&language=en-US&page=1&year=" + str(year)

        # url = "https://api.themoviedb.org/3/search/test"

      else:
        url = "https://api.themoviedb.org/3/movie/" + str(args.tmdbid) + "?language=en-US"
    
    elif args.media == "tv":
      if args.tmdbid is None:
        searchTitle = "%20".join(title.split())
        
        if year == "" or year is None:
            url = "https://api.themoviedb.org/3/search/tv?query=" + searchTitle + "&include_adult=false&language=en-US&page=1"
        else:
            url = "https://api.themoviedb.org/3/search/tv?query=" + searchTitle + "&include_adult=false&language=en-US&page=1&year=" + str(year)

        # url = "https://api.themoviedb.org/3/search/test"

      else:
        url = "https://api.themoviedb.org/3/tv/" + str(args.tmdbid) + "?language=en-US"
      
    # Debug
    # print(f"URL: {url}")
    
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + str(dotenv["TMDB_API_KEY"])
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")
    else:
        responseDict = response.json()
    
    if args.tmdbid is None:
        if responseDict["total_results"] > 25 and year == "":
            print("Too many results...")
            print("Please add a year to narrow down results")
            sys.exit(1)
        elif responseDict["total_results"] > 25:
            print("Too many results...")
            print("Try to add more text to the title search")
            sys.exit(1)
        elif responseDict["total_results"] == 0:
            print("Zero results...")
            print("Try to add more text to the title search")
            sys.exit(1)
        else:
            table = PrettyTable()
            table.field_names = ["ID", "Title", "Year", "Popularity"]
            
            allMediaIds = []
            for row in responseDict["results"]:
                if args.media == "movie":
                  table.add_row([row["id"], row["original_title"], row.get("release_date", ""), row["popularity"]])
                elif args.media == "tv":
                  table.add_row([row["id"], row["original_name"], row.get("first_air_date", ""), row["popularity"]])
                allMediaIds.append(str(row["id"]))
            table.align = "l"
            print(table.get_string(sortby="Popularity", reversesort=True))
            
        while True:
            # print(f"Ids: {allMediaIds}")
            print("")
            mediaId = input("Which {} is being ripped? ".format(args.media))
            if mediaId == "":
                print("You need to input an ID from the table. ")
                print(table)
            elif mediaId not in allMediaIds:
                print("You need to select a valid ID from the table. ")
                print(table)
            else:
                if args.media == "movie":
                    mediaTitle = next((sub['original_title'] for sub in responseDict["results"] if sub['id'] == int(mediaId)), None)
                    mediaYear = next((sub.get('release_date', '') for sub in responseDict["results"] if sub['id'] == int(mediaId)), None)
                    return mediaId, mediaTitle, mediaYear
                elif args.media == "tv":
                    mediaTitle = next((sub['original_name'] for sub in responseDict["results"] if sub['id'] == int(mediaId)), None)
                    mediaYear = next((sub.get('first_air_date', '') for sub in responseDict["results"] if sub['id'] == int(mediaId)), None)
                    # return mediaId, mediaTitle, mediaYear
                    print("Search season information...")
                    if args.media == "tv":
                        url = "https://api.themoviedb.org/3/tv/" + mediaId + "?language=en-US"
                        headers = {
                            "accept": "application/json",
                            "Authorization": "Bearer " + str(dotenv["TMDB_API_KEY"])
                        }
                        
                        try:
                            response = requests.get(url, headers=headers)
                            response.raise_for_status()
                        except HTTPError as http_err:
                            print(f"HTTP error occurred: {http_err}")
                        except Exception as err:
                            print(f"Other error occurred: {err}")
                        else:
                            responseDict = response.json()
                            # print(responseDict["seasons"])
                            # sys.exit(0)
                        table = PrettyTable()
                        table.field_names = ["ID", "Season", "Season #", "Air Date"]
                        allMediaIds = []
                        for row in responseDict["seasons"]:
                            table.add_row([row["id"], row["name"], row["season_number"], row.get("air_date", "")])
                            allMediaIds.append(str(row["id"]))
                        table.align = "l"
                        print(table.get_string(sortby="Season #", reversesort=False))
                        while True:
                            # print(f"Ids: {allMediaIds}")
                            print("")
                            mediaSeasonId = input("Which {} season is being ripped? ".format(args.media))
                            if mediaSeasonId == "":
                                print("You need to input an ID from the table. ")
                                print(table)
                            elif mediaSeasonId not in allMediaIds:
                                print("You need to select a valid ID from the table. ")
                                print(table)
                            else:
                                mediaSeason = next((sub['season_number'] for sub in responseDict["seasons"] if sub['id'] == int(mediaSeasonId)), None)
                                return mediaId, mediaTitle, mediaYear, mediaSeason
    
    else:
        mediaId = args.tmdbid
        mediaTitle = responseDict["original_title"]
        mediaYear = responseDict["release_date"]
        return mediaId, mediaTitle, mediaYear, mediaSeason

def ripFullMkv(folder, title):
    print("Ripping...Please wait...")
    
    # Info returns different results with -r and without
    process = subprocess.Popen([pathRipApp, '-r', 'info', 'disc:0'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for line in process.stdout: 
        search = re.search(rf'^TINFO:{title},27,0,\"(.+)\"', line)
        if search:
            ripFileName = search.group(1)
            # print(f"Match found: {ripFileName}")
    
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
    

def encodeFullMkv(fullRipPath, title, year, tmdbid, parentFolder, season):
    # encodeFullMkv(fullRipFile, mediaYear[:4], mediaId, ripFolder)
    # TODO:
    #     Create folder structure for jellyfin
    #         Best_Movie_Ever (YEAR) [tmdbid-ID]
    #     Create handbrake files off of jellyfin/tmdb id
    #         MOVIE (YEAR) [tmdbid-ID] - 2160p.mp4
    #         MOVIE (YEAR) [tmdbid-ID] - 1080p.mp4
    #     Create file 4k
    #     Create file 1080p

    if season < 10:
        season = "0" + str(season)
    title = "_".join(title.split())
    year = f"({year})"
    tmdbID = f"[tmdbid-{tmdbid}]"
    # encoder = "nvenc_h265_10bit"
    encoder = "qsv_h265_10bit"
    preset4k = "H.265 MKV 2160p60 4K"
    preset1080p = "H.265 MKV 1080p30"
    encodeFullFile4k = ""
    encodeFullFile1080p = ""
    found = 0
    episodeNum = 0
    # preset2 = "H.265 NVENC 2160p 4K"
    if args.media == "movie":
        transcodePath = parentFolder + "/" + title + " " + year + " " + tmdbID
        if not os.path.isdir(transcodePath):
            os.makedirs(transcodePath)
        outputTranscodePath4k = f"{transcodePath}/{title} {year} {tmdbID} - 2160p.mkv"
        outputTranscodePath1080p = f"{transcodePath}/{title} {year} {tmdbID} - 1080p.mkv"
    elif args.media == "tv":
        transcodePath = parentFolder + "/" + title + " " + year + " " + tmdbID + "/" + "Season" + " " + str(season)
        if not os.path.isdir(transcodePath):
            os.makedirs(transcodePath)
        # Debug
        # print("Full path: " + fullRipPath)
        # print("Transcode: " + transcodePath)
        if os.path.exists(transcodePath + "/" + "episode.list"):
            with open(transcodePath + "/" + "episode.list", 'r') as file:
                for line in file:
                    episodeNum += 1
                    if found < 1:
                        if fullRipPath[-20:] in line:
                            print("Episode already exists in the file.")
                            found = 1
                            # Debug
                            # print("Found: " + str(found))
                            # print("Line: " + line)
                            # print("Full Rip Path: " + fullRipPath[-20:])
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
        
        if episodeNum < 10:
            episodeNum = "0" + str(episodeNum)
        outputTranscodePath4k = f"{transcodePath}/{title} S{season}E{episodeNum}.mkv"
        outputTranscodePath1080p = f"{transcodePath}/{title} S{season}E{episodeNum}.mkv"
        # Debug
        # print(outputTranscodePath4k)
        # print(outputTranscodePath1080p)

    # encodeCmd = f"{pathTranscodeApp} -Z {preset4k} -e {encoder} -i {fullRipPath} -o '{transcodePath}/{title} {year} {tmdbID} - 2160p.mkv'"
    # print(f"4K Command: {encodeCmd}")
    
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
    
def main():
    loadEnvFile()
    
    global args
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog='discripper',
        description='This program is a wrapper around makemkvcon and Handbrake while also receiving media data from TMDB API'
        )
    
    parser.add_argument("-t", "--title", help="(Partial) Title of the media")
    parser.add_argument("-y", "--year", type=int, help="Release year of the media")
    parser.add_argument("-f", "--format", default='all', choices=['4k', '1080p', 'all'], help="Format of the output file(s).")
    parser.add_argument("-m", "--media", default='movie', choices=['movie', 'tv'], help="Media format of movie or tv.")
    parser.add_argument("--tmdbid", type=int, help="The Movie DB ID of the media")
    parser.add_argument("FOLDER", help="Root directory for the ripped media")
    args = parser.parse_args()
    
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
    mediaYear = 0
    mediaSeason = 0
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
            while True:
                mediaYear = input("What is the {} production year? (Optional) ".format(args.media))
                if mediaYear == "":
                    break
                elif int(mediaYear) < 1900 or int(mediaYear) > datetime.today().year:
                    print("You need a valid year ")
                else:
                    break
        else:
            mediaYear = args.year
        
    # Get movie/show info
    mediaId, mediaTitle, mediaYear, mediaSeason = getMediaInfo(mediaTitle, mediaYear)

    mediaFolder = args.FOLDER
    if not os.path.isdir(mediaFolder):
        os.makedirs(mediaFolder)
    # Debug
    # print(f"Folder: {mediaFolder}")
    # print(f"ID: {mediaId}")
    # print(f"Title: {mediaTitle}")
    # print(f"Year: {mediaYear}")
    # print(f"Season: {mediaSeason}")
    # sys.exit(0)
    
    getDiscInfo(mediaFolder, mediaTitle)
    
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
        ripFolder = mediaFolder + "/" + "_".join(mediaTitle.split())     
        print(f"We are going to rip {mediaTitle} ({mediaYear[:4]}) with TMDBID [tmdbid-{mediaId}] to {ripFolder}")
        ripFile = ripFullMkv(ripFolder, discTitle)
        fullRipFile = ripFolder + "/" + ripFile
        print(f"Rip completed: {fullRipFile}")
        encodeFullPath4k, encodeFullPath1080p = encodeFullMkv(fullRipFile, mediaTitle, mediaYear[:4], mediaId, ripFolder, mediaSeason)
        if args.format in ['4k', 'all']:
            print(f"Encode completed: {encodeFullPath4k}")
        if args.format in ['1080p', 'all']:
            print(f"Encode completed: {encodeFullPath1080p}")
    elif args.media == "tv":
        ripFolder = mediaFolder + "/" + "_".join(mediaTitle.split())
        print(f"We are going to rip {mediaTitle} - Season {mediaSeason} ({mediaYear[:4]}) with TMDBID [tmdbid-{mediaId}] to {ripFolder}")
        for title in range(int(startDiscTitle), int(endDiscTitle) + 1):
            ripFile = ripFullMkv(ripFolder, str(title))
            fullRipFile = ripFolder + "/" + ripFile
            print(f"Rip completed: {fullRipFile}")
            encodeFullPath4k, encodeFullPath1080p = encodeFullMkv(fullRipFile, mediaTitle, mediaYear[:4], mediaId, ripFolder, mediaSeason)
            if args.format in ['4k', 'all']:
                print(f"Encode completed: {encodeFullPath4k}")
            if args.format in ['1080p', 'all']:
                print(f"Encode completed: {encodeFullPath1080p}")

if __name__ == "__main__":
    main()

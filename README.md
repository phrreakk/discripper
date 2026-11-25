# Discripper - Media backup utility

## Video Demo: <https://youtu.be/Ib3jZ7ScGq8>

## Description

Discripper is a frontend python script that helps to backup your media disks and helps to import those files to the Jellyfin media player/library.

The open-source applications are:

* makemkv/makemkvcon - this application decrypts your media into a usable format
* handbrake - this application transcodes the large backup to a more manageable media file for storage on a NAS device.

Inspiration for this application comes from another open-source software called Automatic Ripping Machine (ARM).  ARM is a web-based application that performs a similar task.  There were numerous times I couldn't get ARM to match the media in the disc drive.

With Discripper, I implemented a "search" function by title (or partial title) and/or year using the The Movie DB (TMDB) API.  I pass those results to a python library called PrettyTable and that presents a nice table to the user.  If you do not select a TMDB id from that list, the software will continue prompting you until you select a valid title.

Additionally, you may pass in TMDB id for the media and discripper will perform a "detail" request and return the title/year and other values, bypassing the search functionality and PrettyTable.

After receiving the media data, we process the titles on the disc.  This can be hard depending on the disc.  Discripper presents all the titles and you select which to backup.  Once that title is selected, it becomes a waiting game.  If it is a 4k movie, it can be upwards of three hours to complete.  After processing is done, discripper presents folder/file locations for the output media files.

Discipper automatically adds the TMDB id to the output folder as stipulated by the Jellyfin community documentation.  This allows the Jellyfin server to download the correct media (data, cover art) for that title.

We do not want to repear outselves so I do an os file check to see if the media files already exist.  If they do, then we do not process the media an additional time.

## Requirements

* A free TMDB user account and READ API key
    * I'm not going to spend hundreds of dollars using IMDB API.
* python requests
    * To make requests to TMDB API
* python dotenv
    * To make values not hardcoded into the code base
* python prettytable
    * To save time formatting the output from the TMDB API results

## Usage

```
usage: discripper [-h] [-t TITLE] [-y YEAR] [-f {4k,1080p,all}] [--tmdbid TMDBID] FOLDER

This program is a wrapper around makemkvcon and Handbrake while also receiving media data from TMDB API

positional arguments:
  FOLDER                Root directory for the ripped media

options:
  -h, --help            show this help message and exit
  -t TITLE, --title TITLE
                        (Partial) Title of the media
  -y YEAR, --year YEAR  Release year of the media
  -f {4k,1080p,all}, --format {4k,1080p,all}
                        Format of the output file(s).
  --tmdbid TMDBID       The Movie DB ID of the media
```

The only required argument is the root directory to store all folders/files.  The directory structure would look like this if your FOLDER is /home/kevin:

* /home/kevin
    * /MOVIE TITLE (This directory would store the large disk backup)
        * /MOVIE TITLE (YEAR) [tmdbid-ID] (This directory would store a file for each format (4k or 1080p))

TITLE can be a partial title search or the full title.  Sometimes it is better to use less characters and let the search function work for you.

YEAR is the release year of the media.  This is optional.

TMDBID is the TMDB id of the media.  If you did a title/year search, the results are sorted by popularity.

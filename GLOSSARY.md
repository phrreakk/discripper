# discripper

Backs up movie and TV discs and names the results so Jellyfin can match them to TMDB.

## Language

**Media**:
A movie or a TV show, as identified by TMDB. Has a TMDB id, a name and a year.
_Avoid_: title (for the movie or show itself), show (when movies are included too)

**Name**:
The human-readable name of a piece of Media, as TMDB records it.
_Avoid_: title

**Season**:
One season of a TV show, as TMDB lists it. Specials are season 0.

**Media lookup**:
Finding Media and Seasons on TMDB, by search or by TMDB id.
_Avoid_: media info, search (when lookup by id is meant too)

**Disc title**:
A numbered title that makemkvcon reports on the disc in the drive; one disc holds several.
_Avoid_: title (on its own), track

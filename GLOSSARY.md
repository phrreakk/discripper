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

**Episode**:
One episode of a Season, as TMDB lists it, with a number, a name and a runtime. TMDB sometimes has no runtime.

**Media lookup**:
Finding Media, Seasons and Episodes on TMDB, by search or by TMDB id.
_Avoid_: media info, search (when lookup by id is meant too)

**Disc title**:
A numbered title that makemkvcon reports on the disc in the drive; one disc holds several.
_Avoid_: title (on its own), track

**Disc label**:
The volume label of the disc in the drive, which tells the discs of a box set apart; some discs have none. It is not the disc's display name, which can be the Media's Name on every disc of a set.
_Avoid_: disc name, display name, volume name

**Library layout**:
The folders and file names Jellyfin expects, so it can match each encoded file to its Media on TMDB.
_Avoid_: naming scheme, folder structure

**Pairing**:
The Episode one Disc title becomes for TV, given as a Season and an Episode number. It's usually in the Season picked for the run, but can be in another, such as Season 0. A Disc title can also be skipped.
_Avoid_: mapping

**Format**:
The resolution an encode is made at: 4k (labelled 2160p in file names) or 1080p. One rip can be encoded in both.
_Avoid_: version, quality

**Rip**:
The full-quality MKV that makemkvcon copies from one Disc title, before it's encoded.
_Avoid_: backup, full MKV

**Rip plan**:
What one run will do, settled before anything is ripped: the Media, its Season for TV, the Disc titles to rip, the Episode each Disc title becomes for TV, the Formats to encode at, and where the Rips and Encodes go. For TV, each disc's Rips go in a folder of their own named after its Disc label, while the Encodes of every disc go into the Media's one Library layout.
_Avoid_: job, session

**Encode**:
A Rip re-encoded by HandBrake at one Format, written into the Library layout.
_Avoid_: transcode

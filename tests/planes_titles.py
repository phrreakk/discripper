"""The three copies of the movie on the Planes (2013) Blu-ray, as makemkvcon listed them.

English, French and (probably) Spanish: same length, different segments.
"""

from disc import DiscTitle


def _copy(number, playlist, segments):
    return DiscTitle(number=number, file_name=f"Planes_t{number:02d}.mkv", duration="1:31:35",
                     chapters=20, size="23.3 GB", playlist=playlist, segments=segments)


_SHARED = ("42,43,45,46,48,49,51,52,54,55,57,58,60,61,63,64,66,67,69,70,72,73,75,76,78,79,81,82,"
           "84,85,87,88,90,91,93,94,96,97,99,100,102,103,105,106,108,109,111,112,114,115,117,118,"
           "120,121,123,124,126,127,129,130,132,133,135,136,138,139,141,142,144,145,147,148,150,"
           "152,154,155,157,158,160")
T02 = _copy(2, "00801.mpls", f"39,164,{_SHARED},165,163")
T03 = _copy(3, "00800.mpls", f"39,40,{_SHARED},161,163")
T04 = _copy(4, "00802.mpls", (
    "39,41,42,44,45,47,48,50,51,53,54,56,57,59,60,62,63,65,66,68,69,71,72,74,75,77,78,80,81,83,"
    "84,86,87,89,90,92,93,95,96,98,99,101,102,104,105,107,108,110,111,113,114,116,117,119,120,"
    "122,123,125,126,128,129,131,132,134,135,137,138,140,141,143,144,146,147,149,151,153,154,"
    "156,157,159,160,162,163"))
EXTRA = DiscTitle(number=5, file_name="Planes_t05.mkv", duration="0:05:53", chapters=0,
                  size="824.8 MB", playlist="00036.m2ts", segments="36")

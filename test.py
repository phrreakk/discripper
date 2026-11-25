#!/usr/bin/env python

# import re, sys
# from prettytable import PrettyTable

# data = [{'adult': False, 'backdrop_path': '/icmmSD4vTTDKOq2vvdulafOGw93.jpg', 'genre_ids': [28, 878], 'id': 603, 'original_language': 'en', 'original_title': 'The Matrix', 'overview': 'Set in the 22nd century, The Matrix tells the story of a computer hacker who joins a group of underground insurgents fighting the vast and powerful computers who now rule the earth.', 'popularity': 132.833, 'poster_path': '/dXNAPwY7VrqMAo51EKhhCJfaGb5.jpg', 'release_date': '1999-03-31', 'title': 'The Matrix', 'video': False, 'vote_average': 8.221, 'vote_count': 25926}, {'adult': False, 'backdrop_path': None, 'genre_ids': [878, 14, 27], 'id': 259464, 'original_language': 'en', 'original_title': 'V-World Matrix', 'overview': 'Two friends take a cyber vacation to experience a world where they can act out their virtual fantasies! They soon realize they\'ve entered a virtual free-for-all. Forbidden fantasies and desires suddenly appear in the form of the even deadlier "dark woman". All the players now end up in a cyber battle for their lives, and sanity, against a beautiful virtual hunter who has one killer fixation - winning the deadly game they started!', 'popularity': 1.912, 'poster_path': '/4SU8oBoLRos8ZQQhuVMjTEJh3xU.jpg', 'release_date': '1999-01-01', 'title': 'V-World Matrix', 'video': False, 'vote_average': 3.0, 'vote_count': 3}, {'adult': False, 'backdrop_path': '/4FuxMYW1E1LHqSkWov2YwaziID3.jpg', 'genre_ids': [99], 'id': 684431, 'original_language': 'en', 'original_title': "Making 'The Matrix'", 'overview': "A promotional making-of documentary for the film Matrix, The (1999) that devotes its time to explaining the digital and practical effects contained in the film. This is very interesting, seeing as how they're giving away the cinematic secrets that they created solely for the this movie, that have now been spoofed and referenced in countless other films.", 'popularity': 3.282, 'poster_path': '/m2yIfRJYwpCgHON1Ig1pNKMWTxp.jpg', 'release_date': '1999-09-21', 'title': "Making 'The Matrix'", 'video': False, 'vote_average': 7.167, 'vote_count': 36}, {'adult': False, 'backdrop_path': None, 'genre_ids': [99], 'id': 684428, 'original_language': 'en', 'original_title': 'The Matrix: What Is Bullet-Time?', 'overview': 'Special Effects wizard John Gaeta demonstrates how the "Bullet-Time" effects were created for the film Matrix, The (1999).', 'popularity': 0.979, 'poster_path': '/hSTervHaROcTd8Ir3DPfepN80dL.jpg', 'release_date': '1999-09-21', 'title': 'The Matrix: What Is Bullet-Time?', 'video': False, 'vote_average': 5.3, 'vote_count': 10}, {'adult': False, 'backdrop_path': '/7ZuLbjfCRmKV8kGT3qdOB90qTMT.jpg', 'genre_ids': [878, 53], 'id': 60215, 'original_language': 'en', 'original_title': 'Darkdrive', 'overview': 'Set in some distant future, one man must restore order when a mainframe system crashes in a virtual reality prison where computers control the inmates thoughts.', 'popularity': 2.514, 'poster_path': '/2jjz6Gm4lDjgXkKEh9GtgrhQOhn.jpg', 'release_date': '1997-11-01', 'title': 'Darkdrive', 'video': False, 'vote_average': 3.2, 'vote_count': 8}]

# table = PrettyTable()

# table.field_names = ["ID", "Title", "Year", "Popularity"]

# allMediaIds = []
# for row in data:
#     # print(f"Row: " + str(row["popularity"]))
#     table.add_row([row["id"], row["original_title"], row["release_date"], row["popularity"]])
#     allMediaIds.append(str(row["id"]))
    
# print(table)

# while True:
#     mediaId = input("Which movie/show is being ripped? ")
#     if mediaId == "":
#         print("You need to input an ID from the table. ")
#         print(table)
#     elif mediaId not in allMediaIds:
#         print("You need to select a valid ID from the table. ")
#         print(table)
#     else:
#         mediaTitle = next((sub['original_title'] for sub in data if sub['id'] == int(mediaId)), None)
#         print(f"Id: {mediaId} Title: {mediaTitle}")


# folder = "/home/kevin/test/Pacific_Rim/Pacific_Rim (2013) [tmdbid-68726]"
# with open(folder + "/" + "/handbrakemkv.log", "r") as file:   
#     for line in file:
#         print(f"{line.strip()}")
#         search = re.search(r'\"File\":\s\"(.+)\"', line)
#         if search:
#             searchTerm = search.group(1)
#             print(f"Found it: {searchTerm}")
#             break
#     else:
#         print("Disc did not complete.")
#         print(f"Please review {folder}/makemkvrip.log for additional details.")
#         sys.exit(1)

str1 = "/home/kevin/Videos/rips/Avatar:_The_Last_Airbender/Avatar- The Last Airbender Book One- Water Disc 1_t00.mkv"
str2 = "/home/kevin/Videos/rips/Avatar:_The_Last_Airbender/Avatar- The Last Airbender Book One- Water Disc 1_t00.mkv"

print(str1)
print(str2)
if str1 == str2:
    print("Same")
else:
    print("Diff")
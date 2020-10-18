#%%
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
from pandas.io.json import json_normalize
from collections import namedtuple
import yaml

# For playing around and finding the structure of the returned json, the following
# is useful:
# playlists = get_full_list(function=sp.current_user_playlists)
# df = pd.json_normalize(playlists)

# There are 3 sorts of IDs:
# - Spotify URI: eg spotify:playlist:04au4deViCEcMwkEmyz8eg
# - Spotify URL: eg https://open.spotify.com/playlist/04au4deViCEcMwkEmyz8eg?si=aHux3al8TtOVJVeU79IGZg
# - Spotify ID:  eg 04au4deViCEcMwkEmyz8eg
# Any can be used with spotipy functions, except for user_follow_artists,
# which for some reason needs IDs

# TODO:  add a low_but_in_order flag because to some people (like me) its important
# that the albums line up in the order you liked them so you can trace back
# over them. This sends one request a second so it is deathly slow but you 
# are only likely to run it once. 
# TODO: Add a check when importing playlists for new_user that if the owner
# is old_user, instead of following, grab all the songs and create a new 
# playlist (maintain order too)


#%%
"""
Want a function to 'export' and again to 'import' to a different account.

What to export:
- Likes (on songs)
- Liked albums
- TODO: own created playlists
- others' playlists added to libraries
- follower artists
NOTE pls can't get the users a user currently followes
"""
#%%
# Load creds from yaml file
credentials = yaml.load(open("credentials.yml"))


# %%

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=credentials["client_id"],
        client_secret=credentials["client_secret"],
        redirect_uri="http://localhost:8080/callback/",
        username=credentials["username_old"],
        scope=("user-library-read " "playlist-read-private " "user-follow-read "),
        cache_path=".spotipyoauthcache",
    )
)

sp2 = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=credentials["client_id"],
        client_secret=credentials["client_secret"],
        redirect_uri="http://localhost:8080/callback/",
        username=credentials["username_new"],
        scope=(
            "user-library-read "
            "user-library-modify "
            "playlist-read-private "
            "playlist-modify-private "
            "playlist-modify-public "
            "user-follow-read "
            "user-follow-modify"
        ),
        cache_path=".spotipyoauthcache2",
    )
)

#%% Helper Functions


def deep_get(d, keys):
    assert type(keys) is list
    if not keys:
        return d
    # if a list, loop over the next field asked for (if last key)
    # and return as a concatenated string
    if type(d) is list and len(keys) == 1:
        return ", ".join([list_item[keys[0]] for list_item in d])
    return deep_get(d.get(keys[0]), keys[1:])


def get_full_list(function, chunksize=50, base_level=[]):
    """for a spotify request function, iterate and return the full list"""

    # request a single result to get the count of the full list
    results = function(limit=1)
    total = deep_get(results, base_level + ["total"])

    offset = 0
    return_list = []

    while offset < total:
        results = function(
            chunksize, offset
        )  # functions have diff names for the argments
        return_list += deep_get(results, base_level + ["items"])
        offset += chunksize

    return return_list


def chunker(to_chunk, chunk_size=50):
    return [to_chunk[i : i + chunk_size] for i in range(0, len(to_chunk), chunk_size)]


#%% Generic media types

Media = namedtuple(
    typename="Media",
    field_names=[
        "name",
        "fields",
        "base_level",
        "read_function",
        "write_function",
        "del_function",
    ],
    defaults=([],),
)
Field = namedtuple(typename="Field", field_names=["name", "field_path"])

# Define the media types and fields we are interested in exporting
media_types = [
    Media(
        name="albums",
        fields=[
            Field("uri", ["album", "uri"]),
            Field("name", ["album", "name"]),
            Field("artist", ["album", "artists", "name"]),
            Field("label", ["album", "label"]),
            Field("added_at", ["added_at"]),
        ],
        base_level=[],
        read_function="current_user_saved_albums",
        write_function="current_user_saved_albums_add",
        del_function="current_user_saved_albums_delete",
    ),
    Media(
        name="tracks",
        fields=[
            Field("uri", ["track", "uri"]),
            Field("name", ["track", "name"]),
            Field("artist", ["track", "artists", "name"]),
            Field("added_at", ["added_at"]),
        ],
        base_level=[],
        read_function="current_user_saved_tracks",
        write_function="current_user_saved_tracks_add",
        del_function="current_user_saved_tracks_delete",
    ),
    Media(
        name="shows",
        fields=[
            Field("uri", ["show", "uri"]),
            Field("name", ["show", "name"]),
            Field("publisher", ["show", "publisher"]),
            Field("description", ["show", "description"]),
            Field("added_at", ["added_at"]),
        ],
        base_level=[],
        read_function="current_user_saved_shows",
        write_function="current_user_saved_shows_add",
        del_function="current_user_saved_shows_delete",
    ),
    Media(
        name="playlists",
        fields=[
            Field("uri", ["uri"]),
            Field("name", ["name"]),
            Field("owner", ["owner", "display_name"]),
            Field("owner_id", ["owner", "id"]),
            Field("public", ["public"]),
            Field("tracks", ["tracks", "total"]),
        ],
        base_level=[],
        read_function="current_user_playlists",
        write_function="user_playlist_follow_playlist",
        del_function="current_user_unfollow_playlist",
    ),
    Media(
        name="followed_artists",
        fields=[
            Field("uri", ["uri"]),
            Field("name", ["name"]),
            Field("popularity", ["popularity"]),
            Field("followers", ["followers", "total"]),
        ],
        base_level=["artists"],
        read_function="current_user_followed_artists",
        write_function="user_follow_artists",
        del_function="user_unfollow_artists",
    ),
]

#%%

def get_library(media_types, spotify_creds, export_to_csv=False):
    library = {}
    for m in media_types:

        saved_media = get_full_list(
            function=getattr(
                spotify_creds, m.read_function
            ),  # follow with () if you want to run
            base_level=m.base_level,
        )

        field_lists = {}

        for field in m.fields:
            field_lists[field.name] = [
                deep_get(media, field.field_path) for media in saved_media
            ]

        df = pd.DataFrame(field_lists)
        if export_to_csv is True:
            df.to_csv(f"{m.name}.csv")
        library[m.name] = df
    return library


#%% write to the new account
old_user_library = get_library(media_types, sp, export_to_csv=True)

for m in media_types:
    print(f"About to add {m.name}")
    media_uris = list(old_user_library[m.name]["uri"])
    print(f"{len(media_uris)} to add with {m.write_function}...")

    #artists is a special case
    if m.name not in ["followed_artists", "playlists"]:
        for chunk in chunker(media_uris):
            getattr(sp2, m.write_function)(chunk)
    elif m.name == "followed_artists":
        media_ids = [uri[15:] for uri in media_uris]
        for chunk in chunker(media_ids):
            getattr(sp2, m.write_function)(chunk)
    elif m.name == "playlists":
        # playlists need to have the owner id as well, and have to be added
        # one at a time
        playlist_ids = [uri[17:] for uri in media_uris]
        owner_ids = list(old_user_library[m.name]["owner_id"])
        for (owner_id,playlist_id) in zip(owner_ids,playlist_ids):
            getattr(sp2, m.write_function)(owner_id, playlist_id)
    print(f"Done adding {m.name}")
    print()

#%% # CLEAR ALL FOR NEW USER

new_user_library = get_library(media_types, sp2)

for m in media_types:
    print(f"About to delete {m.name}")
    media_uris = list(new_user_library[m.name]["uri"])
    print(f"{len(media_uris)} to delete with {m.del_function}...")

    #artists is a special case
    if m.name != "followed_artists":
        for chunk in chunker(media_uris):
            getattr(sp2, m.del_function)(chunk)
    elif m.name == "followed_artists":
        followed_artists_ids = [uri[15:] for uri in media_uris]
        for chunk in chunker(followed_artists_ids):
            getattr(sp2, m.del_function)(chunk)
    print(f"Done deleting {m.name}")
    print()

#%%
def rebuild_playlist():
    pass

# %%
# For playlist, will need to get all tracks and make again as a new playlist

# current_user_saved_albums_add(albums=[])
# current_user_saved_shows_add(shows=[])
# current_user_saved_tracks_add(tracks=None)
# user_follow_artists(ids=[])

# #%% playlist stuff
# playlist(playlist_id, fields=None, market=None, additional_types=('track', ))
# playlist_items(playlist_id, fields=None, limit=100, offset=0, market=None, additional_types=('track', 'episode'))
# playlist_tracks(playlist_id, fields=None, limit=100, offset=0, market=None, additional_types=('track', ))

# #for other people's playlists
# user_playlist_follow_playlist(playlist_owner_id, playlist_id)

# user_playlist_create(user, name, public=True, collaborative=False, description='')
# playlist_add_items(playlist_id, items, position=None)
# user_playlist_add_tracks(user, playlist_id, tracks, position=None)


# #%% for delete
# current_user_saved_albums_delete(albums=[])
# current_user_saved_shows_delete(shows=[])
# current_user_saved_tracks_delete(tracks=None)
# current_user_unfollow_playlist(playlist_id)
# user_unfollow_artists(ids=[])
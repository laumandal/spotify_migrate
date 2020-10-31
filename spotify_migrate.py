import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
from pandas.io.json import json_normalize
from media_types import media_types
import yaml
import requests
import base64
import webbrowser
from tqdm import tqdm
import time

# For playing around and finding the structure of the returned json, the following
# is useful:
# playlists = get_full_list(function=sp.current_user_playlists)
# df = pd.json_normalize(playlists)

# There are 3 sorts of IDs:
# - Spotify URI: eg spotify:playlist:04au4deViCEcMwkEmyz8eg
# - Spotify URL: eg https://open.spotify.com/playlist/04au4deViCEcMwkEmyz8eg?si=aHux3al8TtOVJVeU79IGZg
# - Spotify ID:  eg 04au4deViCEcMwkEmyz8eg
# Most spotipy functions can use any of them, with a few (non obvious) exceptions - check the docs. 

# NOTE pls can't currently get the users a user currently followes

# Load creds from yaml file
credentials = yaml.safe_load(open("credentials.yml"))

def authenticate():

    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"],
            redirect_uri="http://localhost:8080/callback/",
            username=credentials["username_old"],
            scope=("user-library-read " "playlist-read-private " "user-follow-read "),
            # cache_path=".spotipyoauthcache",
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
                "ugc-image-upload "
                "user-follow-read "
                "user-follow-modify"
            ),
            # cache_path=".spotipyoauthcache2",
        )
    )

    logout_url = 'https://spotify.com/logout'

    # force a log out of any logged in account
    webbrowser.open_new(logout_url)

    # force a manual keypress to stop the second auth happening before
    # any signed is account 
    input("Press enter once the Spotify homepage has launched... 💻, then if prompted login with the OLD spotify id you want to copy FROM")
    # get the id using credentials which will prompt a login
    login_old_id = sp.me()['id']
    webbrowser.open_new(logout_url)

    # force a manual keypress to stop the second auth happening before
    # the first account is logged out
    input("Press enter once the Spotify homepage has launched... then if prompted login with the NEW spotify id you want to copy TO)")

    login_new_id = sp2.me()['id']

    # Confirm correct accounts have been authorised by comparing expected to actual ids
    if credentials["username_old"] == login_old_id and credentials["username_new"] == login_new_id:
        print("User logins look good 💫")
    else:
        print("User logins dont look good 🙅‍♂️")
        print(f"Expected {credentials['username_old']}, login was {login_old_id}")
        print(f"Expected {credentials['username_new']}, login was {login_new_id}")
        raise Exception('User ids and logins do not match.')

    return (sp, sp2)

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

        #reverse the order for reimporting later
        df = pd.DataFrame(field_lists)[::-1].reset_index(drop=True)
        if export_to_csv is True:
            df.to_csv(f"{m.name}.csv")
        library[m.name] = df
    return library

def recreate_playlist(playlist_id, creds_old, creds_new):
    # get uris of items in playlist
    results = creds_old.playlist(playlist_id)
    track_uris = [x['track']['uri'] for x in results['tracks']['items'] if x['track']['is_local']==False]

    # get the cover image
    img_info = creds_old.playlist_cover_image(playlist_id)

    # it appears that spotify generated mosaic images for playlists have
    # multiple sizes, whereas custom do not (and height and width are None)
    # We'll use this to only copy custom images over
    custom_img_used = True if len(img_info)==1 else False

    # create a new playlist
    ret = creds_new.user_playlist_create(
        user=credentials["username_new"], 
        name=results['name'], 
        public=results['public'], 
        description=results['description'])

    new_playlist_uri = ret['uri']

    if custom_img_used is True:
        # get the img using the url from spotify's returned info
        response = requests.get(img_info[0]['url'])
        # convert to a base64 string as required for upload
        img_string = base64.b64encode(response.content)
        # upload to new playlist
        creds_new.playlist_upload_cover_image(new_playlist_uri, img_string)

    # Add songs to new playlist
    creds_new.playlist_add_items(new_playlist_uri, track_uris)

def copy_all_to_new_account(sp, sp2):
    old_user_library = get_library(media_types, sp, export_to_csv=False)

    for m in media_types:
        
        media_ids = list(old_user_library[m.name][m.write_id])
        print(f"About to add {len(media_ids)} {m.name}")

        #playlists is a special case
        if m.name not in ["playlists"]:
            for chunk in tqdm(chunker(media_ids, chunk_size=1), leave=False):
                getattr(sp2, m.write_function)(chunk)
        elif m.name == "playlists":
            # playlists need to have the owner id as well, and have to be added one at a time
            owner_ids = list(old_user_library["playlists"]["owner_id"])
            num_own_playlists = owner_ids.count(credentials["username_old"])
            num_followed_playlists = len(media_ids)-num_own_playlists
            print(f"{num_own_playlists} personal playlists to recreate 👷‍♀️")
            print(f"and {num_followed_playlists} to follow 🚶‍♀️")

            for (owner_id,playlist_id) in tqdm(zip(owner_ids,media_ids), leave=True):
                # for playlists created by old user, recreate for new user
                if owner_id == credentials["username_old"]:
                    recreate_playlist(playlist_id, sp, sp2)
                    num_own_playlists += 1
                else:
                    getattr(sp2, m.write_function)(owner_id, playlist_id)
                    num_followed_playlists += 1
        print(f"Done adding {m.name}")
        print()
        #try to avoid hitting rate limits
        time.sleep(1)

def wipe_everything(sp2):
    new_user_library = get_library(media_types, sp2)

    for m in media_types:
        media_ids = list(new_user_library[m.name][m.write_id])
        tqdm.write(f"About to delete {len(media_ids)} {m.name}")

        # playlists is a special case
        if m.name != "playlists":
            for chunk in chunker(media_ids):
                getattr(sp2, m.del_function)(chunk)
        # playlists have to be removed one at a time so no chunker
        elif m.name == "playlists":
            for playlist_id in media_ids:
                getattr(sp2, m.del_function)(playlist_id)
        tqdm.write(f"Done deleting {m.name}")
        print()

def export_library_to_csvs(sp):
    _ = get_library(media_types, sp, export_to_csv=True)

def main():
    print("Beginning spotify migrate... 🎶💻🎤")
    print("Authenticating... 🔑")
    (sp, sp2) = authenticate()
    print("Copying over library... 🎷")
    copy_all_to_new_account(sp, sp2)
    print("All done here! Enjoy ✨")

if __name__ == "__main__":
    # execute only if run as a script
    main()

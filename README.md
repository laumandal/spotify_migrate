# spotify_migrate 🎷
`spotify_migrate` copies everything from an old Spotify account to a new one, using the `spotipy` package. My use case was I wanted to disconnect my Spotify account from Facebook (which I had originally used to sign up), but there's currently no way to do this on Spotify, so I created a new Spotify account and wrote this to move everything accross.

### What it does
* Likes the same songs, albums, and artists for the new account as the old
* Follows the same playlists created by other users that the old account was following
* For playlists created by the old account, creates new playlists for the new account with the same songs in them (so that you can continue to modify them with the new account)

### What it doesn't do
* Doesn't follow the users the old account followed (no way to do this currently with the API I think)
* Although it attempts to keep everything in the new account in the same order it was added for the old, the 'date added' field where available (eg for playlists, liked songs, etc) will reflect when the script was run rather than the original time

# Usage

You first need to fill out `credentials.yml` with the old and new Spotify accounts' usernames.

Then you need to create an app on __Spotify for Developers__ in order to get credentials to run this script. Follow these steps:
1. Visit https://developer.spotify.com/dashboard/
2. Log in (with either the old or new Spotify account, doesn't matter which)
3. Click 'create a new app', give it a name and click 'create'
4. Click 'show client secret', then copy the `Client ID` and `Client Secret` into `credentials.yml`
5. Click 'edit settings' and add `http://localhost:8080/callback/` and `http://www.spotify.com/logout` to the `Redirect URIs`

Once credentials.yml is filled out, you can simply run from the command line: `python3 spotify_migrate.py`

## Usage notes

During authentication for both accounts, the browser will pop up a few times (to ensure accounts are logged out before each authentication, and then for authentication itself if no cached credentials are available.)

### Additional functionality:
* You can wipe everything (all songs/albums/artists/playlists) from the new Spotify account only, using the function `wipe_everything` (it only works on the new account to avoid wiping your old library by mistake; only the new account requests modifier access)
* You can export everything to csvs using the function `export_library_to_csvs`
* To limit the media types imported/exported, simply change the list in `media_types.py`






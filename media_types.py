from collections import namedtuple

# namedtuple defaults:
# defaults can be None or an iterable of default values. Since fields with a default value
# must come after any fields without a default, the defaults are applied to the rightmost
# parameters. For example, if the fieldnames are ['x', 'y', 'z'] and the defaults are (1, 2),
#  then x will be a required argument, y will default to 1, and z will default to 2.

Media = namedtuple(
    typename="Media",
    field_names=[
        "name",
        "fields",
        "read_function",
        "write_function",
        "del_function",
        "base_level",
        "write_id",
    ],
    defaults=([], "uri"),
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
        read_function="current_user_saved_albums",
        write_function="current_user_saved_albums_add",
        del_function="current_user_saved_albums_delete",
    ),  # type: ignore
    Media(
        name="tracks",
        fields=[
            Field("uri", ["track", "uri"]),
            Field("name", ["track", "name"]),
            Field("artist", ["track", "artists", "name"]),
            Field("added_at", ["added_at"]),
        ],
        read_function="current_user_saved_tracks",
        write_function="current_user_saved_tracks_add",
        del_function="current_user_saved_tracks_delete",
    ),  # type: ignore
    Media(
        name="shows",
        fields=[
            Field("uri", ["show", "uri"]),
            Field("name", ["show", "name"]),
            Field("publisher", ["show", "publisher"]),
            Field("description", ["show", "description"]),
            Field("added_at", ["added_at"]),
        ],
        read_function="current_user_saved_shows",
        write_function="current_user_saved_shows_add",
        del_function="current_user_saved_shows_delete",
    ),  # type: ignore
    Media(
        name="playlists",
        fields=[
            Field("uri", ["uri"]),
            Field("id", ["id"]),
            Field("name", ["name"]),
            Field("owner", ["owner", "display_name"]),
            Field("owner_id", ["owner", "id"]),
            Field("public", ["public"]),
            Field("tracks", ["tracks", "total"]),
        ],
        read_function="current_user_playlists",
        write_function="user_playlist_follow_playlist",
        del_function="current_user_unfollow_playlist",
        write_id="id",
    ),  # type: ignore
    Media(
        name="followed_artists",
        fields=[
            Field("uri", ["uri"]),
            Field("id", ["id"]),
            Field("name", ["name"]),
            Field("popularity", ["popularity"]),
            Field("followers", ["followers", "total"]),
        ],
        read_function="current_user_followed_artists",
        write_function="user_follow_artists",
        del_function="user_unfollow_artists",
        base_level=["artists"],
        write_id="id",
    ),
]
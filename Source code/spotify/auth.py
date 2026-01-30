# spotify/auth.py

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler

from flask import session
from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SCOPE

# ---------------- OAuth setup ----------------
cache_handler = FlaskSessionCacheHandler(session)

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_handler=cache_handler,
    show_dialog=True,
)

spotify_token_info = None


def get_spotify_client():
    global spotify_token_info

    if spotify_token_info is None:
        return None

    try:
        if sp_oauth.is_token_expired(spotify_token_info):
            spotify_token_info = sp_oauth.refresh_access_token(
                spotify_token_info["refresh_token"]
            )
    except Exception as e:
        print(f"Error refreshing token: {e}")
        return None

    return Spotify(auth=spotify_token_info["access_token"])

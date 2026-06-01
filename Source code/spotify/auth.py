from flask import session
from spotipy import Spotify
from spotipy.cache_handler import FlaskSessionCacheHandler
from spotipy.oauth2 import SpotifyOAuth

from config import SETTINGS, SPOTIFY_SCOPE
from utils import state


def spotify_auth_ready():
    return all(
        [
            SETTINGS.spotify_client_id,
            SETTINGS.spotify_client_secret,
            SETTINGS.spotify_redirect_uri,
        ]
    )


cache_handler = FlaskSessionCacheHandler(session)
sp_oauth = (
    SpotifyOAuth(
        client_id=SETTINGS.spotify_client_id,
        client_secret=SETTINGS.spotify_client_secret,
        redirect_uri=SETTINGS.spotify_redirect_uri,
        scope=SPOTIFY_SCOPE,
        cache_handler=cache_handler,
        show_dialog=True,
    )
    if spotify_auth_ready()
    else None
)


def set_token_info(token_info):
    state.spotify_token_info = token_info


def get_spotify_client():
    if state.spotify_token_info is None or sp_oauth is None:
        return None
    try:
        if sp_oauth.is_token_expired(state.spotify_token_info):
            state.spotify_token_info = sp_oauth.refresh_access_token(
                state.spotify_token_info["refresh_token"]
            )
    except Exception as error:
        print(f"Error refreshing token: {error}")
        return None
    return Spotify(auth=state.spotify_token_info["access_token"])

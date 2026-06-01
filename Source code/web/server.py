import threading

from flask import Flask, redirect, render_template_string, request, url_for

from camera.driver_monitor import monitor_driver
from config import SETTINGS
from spotify.auth import get_spotify_client, set_token_info, sp_oauth, spotify_auth_ready
from utils import state


app = Flask(__name__)
app.config["SECRET_KEY"] = SETTINGS.app_secret_key


def _render_message_page(message):
    return render_template_string(
        """
        <h1>Drive Mood</h1>
        <p>{{ message }}</p>
        <p><a href="{{ url_for('home') }}">Back</a></p>
        """,
        message=message,
    )


@app.route("/")
def home():
    if not spotify_auth_ready() or sp_oauth is None:
        return _render_message_page("Spotify credentials are missing. Add them to your local .env file.")
    spotify_client = get_spotify_client()
    if spotify_client is None:
        return redirect(sp_oauth.get_authorize_url())
    return render_template_string(
        """
        <h1>Drive Mood</h1>
        <form action="{{ url_for('start') }}" method="post">
            <button type="submit">Start Monitoring</button>
        </form>
        <form action="{{ url_for('stop') }}" method="post">
            <button type="submit">Stop Monitoring and Delete Playlist</button>
        </form>
        <p>Driver state: {{ driver_state }}</p>
        {% if playlist_created %}
        <p>Playlist created and monitoring stopped.</p>
        {% endif %}
        """,
        driver_state=state.driver_state,
        playlist_created=state.playlist_created,
    )


@app.route("/callback")
def callback():
    if sp_oauth is None:
        return _render_message_page("Spotify credentials are missing.")
    token_info = sp_oauth.get_access_token(request.args.get("code"))
    set_token_info(token_info)
    return redirect(url_for("home"))


@app.route("/start", methods=["POST"])
def start():
    if not spotify_auth_ready() or sp_oauth is None:
        return _render_message_page("Spotify credentials are missing.")
    if state.monitoring_thread and state.monitoring_thread.is_alive():
        return redirect(url_for("home"))
    spotify_client = get_spotify_client()
    if spotify_client is None:
        return redirect(sp_oauth.get_authorize_url())
    state.playlist_created = False
    state.stop_event.clear()
    state.monitoring_active = True
    state.monitoring_thread = threading.Thread(target=monitor_driver, daemon=True)
    state.monitoring_thread.start()
    return redirect(url_for("home"))


@app.route("/stop", methods=["POST"])
def stop():
    spotify_client = get_spotify_client()
    if state.monitoring_active:
        state.monitoring_active = False
        state.stop_event.set()
        if state.monitoring_thread:
            state.monitoring_thread.join(timeout=5)
            state.monitoring_thread = None
    if state.created_playlist_id and spotify_client:
        try:
            spotify_client.current_user_unfollow_playlist(state.created_playlist_id)
        except Exception as error:
            print(f"Error deleting playlist: {error}")
        state.created_playlist_id = None
    state.playlist_created = False
    return redirect(url_for("home"))



import os
import threading

from flask import (
    Flask,
    session,
    redirect,
    url_for,
    request,
    render_template_string,
)

from spotify.auth import sp_oauth, spotify_token_info, get_spotify_client
from camera.driver_monitor import monitor_driver
from utils.state import (
    stop_event,
    monitoring_active,
    monitoring_thread,
    playlist_created,
    created_playlist_id,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(64)


@app.route("/")
def home():
    sp = get_spotify_client()
    if sp is None:
        return redirect(sp_oauth.get_authorize_url())
    html = """
    <h1>🚗 Drive Mood</h1>
    <form action="{{ url_for('start') }}" method="post">
        <button type="submit">▶ Start Monitoring</button>
    </form>
    <form action="{{ url_for('stop') }}" method="post">
        <button type="submit">⏹ Stop & Delete Playlist</button>
    </form>
    {% if playlist_created %}
    <p style="color: green;">✅ Playlist created and monitoring stopped.</p>
    {% endif %}
    """
    return render_template_string(html)

@app.route("/callback")
def callback():
    global spotify_token_info
    token_info = sp_oauth.get_access_token(request.args.get("code"))
    spotify_token_info = token_info
    return redirect(url_for("home"))

@app.route("/start", methods=["POST"])
def start():
    from utils.state import monitoring_active, monitoring_thread, playlist_created

    playlist_created = False
    sp = get_spotify_client()
    if sp is None:
        return redirect(sp_oauth.get_authorize_url())

    if not monitoring_active:
        monitoring_active = True
        monitoring_thread = threading.Thread(target=monitor_driver)
        monitoring_thread.start()

    return redirect(url_for("home"))



@app.route("/stop", methods=["POST"])
def stop():
    from utils.state import (
        monitoring_active,
        monitoring_thread,
        playlist_created,
        created_playlist_id,
        stop_event,
    )

    sp = get_spotify_client()

    if monitoring_active:
        monitoring_active = False
        if monitoring_thread:
            stop_event.set()
            monitoring_thread.join(timeout=2)
            print("🛑 Monitoring thread stopped.")

    if created_playlist_id and sp:
        try:
            sp.current_user_unfollow_playlist(created_playlist_id)
            print(f"🗑️ Deleted playlist {created_playlist_id}")
        except Exception as e:
            print(f"Error deleting playlist: {e}")
        created_playlist_id = None

    playlist_created = False
    return redirect(url_for("home"))

import threading


stop_event = threading.Event()
monitoring_thread = None
monitoring_active = False
playlist_created = False
created_playlist_id = None
spotify_token_info = None
driver_state = "Calm"
picam2 = None


def reset_playlist_state() -> None:
    global playlist_created, created_playlist_id
    playlist_created = False
    created_playlist_id = None


def reset_monitoring_state() -> None:
    global monitoring_thread, monitoring_active, picam2
    monitoring_thread = None
    monitoring_active = False
    picam2 = None

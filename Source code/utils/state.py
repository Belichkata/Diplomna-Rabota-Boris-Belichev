# utils/state.py

import threading

# Thread control
stop_event = threading.Event()
monitoring_thread = None
monitoring_active = False

# Spotify / app state
playlist_created = False
created_playlist_id = None

# Driver state
driver_state = "Calm"

import time


def start_spotify_playback(sp, playlist_id):
    """
    Start playback of the specified playlist on your best available Spotify device.
    Forces playback transfer if Spotify is idle.
    """
    try:
        devices_info = sp.devices()
        devices = devices_info.get("devices", [])

        if not devices:
            print("⚠️ No available Spotify devices. Open Spotify on your computer or phone and play a song once.")
            return

        # --- Prefer computer or active device ---
        device_id = None
        computer_devices = [d for d in devices if d.get("type", "").lower() == "computer"]
        active_devices = [d for d in devices if d.get("is_active")]
        fallback_device = devices[0]["id"]

        if computer_devices:
            device_id = computer_devices[0]["id"]
            print(f"💻 Selected computer device: {computer_devices[0]['name']}")
        elif active_devices:
            device_id = active_devices[0]["id"]
            print(f"📱 Selected active device: {active_devices[0]['name']}")
        else:
            device_id = fallback_device
            print(f"ℹ️ Using fallback device: {devices[0]['name']}")

        # --- Transfer playback first (this wakes idle Spotify) ---
        sp.transfer_playback(device_id=device_id, force_play=False)
        time.sleep(1)

        # --- Start playback ---
        print(f"🎧 Attempting to play playlist on device ID: {device_id}")
        sp.start_playback(device_id=device_id, context_uri=f"spotify:playlist:{playlist_id}")
        time.sleep(2)

        # --- Verify playback started ---
        playback = sp.current_playback()
        if playback and playback.get("is_playing"):
            print("✅ Playback successfully started!")
        else:
            print("⚠️ Playback command sent but Spotify is idle. Try pressing play once manually in the app.")

    except Exception as e:
        print(f"❌ Could not start playback: {e}")
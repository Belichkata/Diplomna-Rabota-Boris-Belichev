import time


def start_spotify_playback(sp, playlist_id):
    try:
        devices = sp.devices().get("devices", [])
        if not devices:
            print("No available Spotify devices.")
            return
        computer_devices = [device for device in devices if device.get("type", "").lower() == "computer"]
        active_devices = [device for device in devices if device.get("is_active")]
        selected_device = computer_devices[0] if computer_devices else active_devices[0] if active_devices else devices[0]
        device_id = selected_device["id"]
        sp.transfer_playback(device_id=device_id, force_play=False)
        time.sleep(1)
        sp.start_playback(device_id=device_id, context_uri=f"spotify:playlist:{playlist_id}")
        time.sleep(2)
        playback = sp.current_playback()
        if not playback or not playback.get("is_playing"):
            print("Playback command sent but Spotify is still idle.")
    except Exception as error:
        print(f"Could not start playback: {error}")

import datetime as dt
import json
import random
import time

from config import SETTINGS
from environment.location import get_surroundings_from_coords
from environment.traffic import get_traffic_status
from environment.weather import get_weather_data
from sensors.light_sensor import read_ambient_lux
from spotify.playback import start_spotify_playback
from utils import state

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


MOOD_PARAMS = {
    "Wakefulness": "Relaxed and steady tracks for stable driving.",
    "Hypovigilance": "Focused and energetic tracks for alert driving.",
    "Drowsiness": "Upbeat music to reduce drowsiness.",
    "Microsleep": "High-energy music for immediate stimulation.",
    "Calm": "Relaxed and steady tracks for stable driving.",
}

SEARCH_KEYWORDS = {
    "Wakefulness": ["chill k-pop", "melodic rap chill", "soft k-rap", "relaxing k-pop", "ambient noise"],
    "Hypovigilance": ["k-pop hype", "k-rap energy", "rap workout", "fast k-pop"],
    "Drowsiness": ["upbeat k-pop", "dance k-pop", "catchy melodic rap", "rap bangers"],
    "Microsleep": ["high energy rap", "rage workout", "driving edm"],
    "Calm": ["chill drive", "steady focus", "lo-fi driving"],
}

_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is not None:
        return _openai_client
    if OpenAI is None or not SETTINGS.openai_api_key:
        return None
    _openai_client = OpenAI(api_key=SETTINGS.openai_api_key)
    return _openai_client


def get_environment_conditions(lux=None, now=None, speed_kmh=None):
    if now is None:
        now = dt.datetime.now()
    hour = now.hour
    if 5 <= hour < 12:
        time_of_day = "morning"
    elif 12 <= hour < 17:
        time_of_day = "afternoon"
    elif 17 <= hour < 21:
        time_of_day = "evening"
    else:
        time_of_day = "night"

    if lux is None:
        lux_value = SETTINGS.default_lux
    else:
        try:
            lux_value = float(lux)
        except Exception:
            lux_value = SETTINGS.default_lux

    if lux_value >= 200:
        light_condition = "bright"
    elif lux_value >= 80:
        light_condition = "dim"
    else:
        light_condition = "dark"

    if speed_kmh is None:
        speed_value = 0.0
    else:
        try:
            speed_value = float(speed_kmh)
        except Exception:
            speed_value = 0.0

    if speed_value >= 100:
        speed_condition = "fast"
    elif speed_value >= 40:
        speed_condition = "moderate"
    else:
        speed_condition = "slow"

    mood_keywords = []
    if light_condition == "bright":
        mood_keywords.extend(["energetic", "upbeat", "bright"])
    elif light_condition == "dim":
        mood_keywords.extend(["focus", "groove", "midtempo"])
    else:
        mood_keywords.extend(["warm", "cozy", "soft"])

    if speed_condition == "fast":
        mood_keywords.extend(["driving", "intense"])
    elif speed_condition == "moderate":
        mood_keywords.extend(["steady", "balanced"])
    else:
        mood_keywords.extend(["relaxed", "mellow"])

    if time_of_day == "night":
        mood_keywords.extend(["chill", "ambient"])

    return {
        "time_of_day": time_of_day,
        "light_condition": light_condition,
        "speed_condition": speed_condition,
        "mood_keywords": list(dict.fromkeys(mood_keywords)),
    }


def _fallback_music_decision(context, user_genres):
    driver_state = context["driver_state"]
    queries = list(SEARCH_KEYWORDS.get(driver_state, ["drive music"]))
    if context["traffic"] == "heavy":
        queries.insert(0, "calm driving music")
    elif driver_state in {"Drowsiness", "Microsleep"}:
        queries.insert(0, "upbeat driving music")
    if context["light_condition"] == "dark":
        queries.append("night drive")
    genres = list(dict.fromkeys(user_genres[:5] or ["k-pop", "rap", "electronic"]))
    if driver_state == "Wakefulness":
        energy = 0.45
        tempo_range = [85, 120]
    elif driver_state == "Hypovigilance":
        energy = 0.65
        tempo_range = [100, 135]
    elif driver_state == "Drowsiness":
        energy = 0.8
        tempo_range = [115, 150]
    else:
        energy = 0.9
        tempo_range = [125, 165]
    return {
        "energy": energy,
        "valence": 0.6,
        "tempo_range_bpm": tempo_range,
        "preferred_genres": genres,
        "avoid_genres": [],
        "spotify_search_queries": queries,
        "familiarity_bias": "balanced",
        "vocal_preference": "mixed",
    }


def get_openai_music_decision(context, user_genres):
    client = _get_openai_client()
    if client is None:
        return _fallback_music_decision(context, user_genres)

    system_prompt = (
        "You are an expert AI music curator for driving. "
        "Adapt music to driver alertness, traffic, environment, and personal taste. "
        "Return strict JSON only."
    )
    user_prompt = (
        f"Context:\n{json.dumps(context, indent=2)}\n\n"
        "Return JSON with keys energy, valence, tempo_range_bpm, preferred_genres, "
        "avoid_genres, spotify_search_queries, familiarity_bias, vocal_preference."
    )
    try:
        response = client.chat.completions.create(
            model=SETTINGS.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as error:
        print(f"OpenAI request failed: {error}")
        return _fallback_music_decision(context, user_genres)


def get_discovery_tracks(sp, mood, user_genres, search_queries=None, max_tracks=400):
    keywords = search_queries or SEARCH_KEYWORDS.get(mood, ["drive music"])
    candidates = []
    for keyword in keywords:
        try:
            results = sp.search(q=f"{keyword} playlist", type="playlist", limit=10)
            playlists = results.get("playlists", {}).get("items", [])
        except Exception as error:
            print(f"Playlist search failed for '{keyword}': {error}")
            playlists = []
        for playlist in playlists:
            try:
                items = sp.playlist_items(playlist["id"], limit=80).get("items", [])
            except Exception:
                items = []
            for item in items:
                track = item.get("track")
                if track and track.get("uri"):
                    candidates.append(track)
                if len(candidates) >= max_tracks * 2:
                    break
            if len(candidates) >= max_tracks * 2:
                break
        if len(candidates) >= max_tracks * 2:
            break

    if not candidates:
        return []

    artist_cache = {}
    artist_ids = list(
        {
            track["artists"][0]["id"]
            for track in candidates
            if track.get("artists") and track["artists"][0].get("id")
        }
    )
    for index in range(0, len(artist_ids), 50):
        try:
            response = sp.artists(artist_ids[index : index + 50]).get("artists", [])
        except Exception as error:
            print(f"Artist genre lookup failed: {error}")
            response = []
        for artist in response:
            artist_cache[artist["id"]] = [genre.lower() for genre in artist.get("genres", [])]

    def genre_match(artist_genres):
        if not user_genres or not artist_genres:
            return False
        for artist_genre in artist_genres:
            for user_genre in user_genres:
                if user_genre in artist_genre or artist_genre in user_genre:
                    return True
        return False

    matches = []
    for track in candidates:
        try:
            artist_id = track["artists"][0]["id"]
            if genre_match(artist_cache.get(artist_id, [])):
                matches.append(track)
            if len(matches) >= max_tracks:
                break
        except Exception:
            continue

    if matches:
        return matches

    return random.sample(candidates, min(len(candidates), max_tracks))


def _collect_runtime_inputs():
    lux_input = read_ambient_lux()
    if lux_input is None:
        lux_input = SETTINGS.default_lux
    return (
        lux_input,
        SETTINGS.simulated_speed_kmh,
        SETTINGS.default_latitude,
        SETTINGS.default_longitude,
    )


def _current_user_profile(sp):
    try:
        top_tracks_full = sp.current_user_top_tracks(limit=50, time_range="medium_term")["items"]
        top_artists_full = sp.current_user_top_artists(limit=20, time_range="medium_term")["items"]
    except Exception:
        return [], [], [], [], []

    top_tracks = [track for track in top_tracks_full if track.get("uri")]
    top_artist_ids = [artist["id"] for artist in top_artists_full if artist.get("id")]
    user_genres = []
    for artist in top_artists_full:
        user_genres.extend([genre.lower() for genre in artist.get("genres", [])])
    user_genres = list(dict.fromkeys(user_genres))
    return top_tracks_full, top_artists_full, top_tracks, top_artist_ids, user_genres


def create_smart_playlist(sp, total_tracks=None):
    total_tracks = total_tracks or SETTINGS.total_tracks
    lux_input, speed_input, lat, lon = _collect_runtime_inputs()
    traffic_status = get_traffic_status(lat, lon, speed_input)
    environment_data = get_environment_conditions(lux_input, speed_kmh=speed_input)
    surroundings = get_surroundings_from_coords(lat, lon)
    weather = get_weather_data() or {}

    if state.created_playlist_id:
        try:
            sp.current_user_unfollow_playlist(state.created_playlist_id)
        except Exception as error:
            print(f"Could not delete old playlist: {error}")
        state.created_playlist_id = None

    mood_description = MOOD_PARAMS.get(state.driver_state, MOOD_PARAMS["Wakefulness"])
    playlist_name = f"Drive Mood - {state.driver_state} - {int(time.time())}"

    try:
        user_id = sp.current_user()["id"]
        playlist = sp.user_playlist_create(
            user=user_id,
            name=playlist_name,
            public=False,
            description=mood_description,
        )
        state.created_playlist_id = playlist["id"]
    except Exception as error:
        print(f"Error creating playlist: {error}")
        return None

    top_tracks_full, top_artists_full, top_tracks, top_artist_ids, user_genres = _current_user_profile(sp)
    context = {
        "driver_state": state.driver_state,
        "time_of_day": environment_data["time_of_day"],
        "light_condition": environment_data["light_condition"],
        "lux": lux_input,
        "speed_kmh": speed_input,
        "speed_condition": environment_data["speed_condition"],
        "traffic": traffic_status,
        "weather": weather,
        "location": {
            "city": surroundings["city"],
            "country": surroundings["country"],
            "features": surroundings["features"],
        },
        "user_profile": {
            "top_genres": user_genres[:10],
            "top_artists": [artist["name"] for artist in top_artists_full[:5]],
            "top_tracks": [track["name"] for track in top_tracks_full[:5]],
        },
    }
    decision = get_openai_music_decision(context, user_genres)
    search_queries = decision.get("spotify_search_queries") or SEARCH_KEYWORDS.get(state.driver_state, ["drive music"])
    preferred_genres = decision.get("preferred_genres") or user_genres[:3]
    tempo_range = decision.get("tempo_range_bpm") or [90, 130]
    energy_target = decision.get("energy", 0.6)

    discovery_tracks = get_discovery_tracks(
        sp,
        state.driver_state,
        user_genres,
        search_queries=search_queries,
        max_tracks=int(total_tracks * 1.5),
    )
    recommendation_tracks = []
    try:
        seed_tracks = [track.get("id") for track in top_tracks_full[:5] if track.get("id")]
        seed_artists = list(dict.fromkeys(top_artist_ids))[:5]
        recommendation_tracks = sp.recommendations(
            seed_tracks=seed_tracks[:2],
            seed_artists=seed_artists[:2],
            seed_genres=preferred_genres[:3],
            target_energy=energy_target,
            min_tempo=tempo_range[0],
            max_tempo=tempo_range[1],
            limit=25,
        ).get("tracks", [])
    except Exception as error:
        print(f"Spotify recommendations failed: {error}")

    random.shuffle(discovery_tracks)
    random.shuffle(top_tracks)
    random.shuffle(recommendation_tracks)
    combined_tracks = (
        discovery_tracks[: int(total_tracks * 0.7)]
        + top_tracks[: int(total_tracks * 0.15)]
        + recommendation_tracks[: int(total_tracks * 0.15)]
    )
    random.shuffle(combined_tracks)

    seen = set()
    uris = []
    for track in combined_tracks:
        if not track or not track.get("uri"):
            continue
        artist_name = track["artists"][0]["name"] if track.get("artists") else ""
        track_key = f"{(track.get('name') or '').lower().strip()}-{artist_name.lower().strip()}"
        if track_key in seen:
            continue
        seen.add(track_key)
        uris.append(track["uri"])
        if len(uris) >= total_tracks:
            break

    if not uris:
        print("No playlist tracks were collected.")
        return None

    try:
        for index in range(0, len(uris), 100):
            sp.playlist_add_items(state.created_playlist_id, uris[index : index + 100])
            time.sleep(0.2)
        start_spotify_playback(sp, state.created_playlist_id)
    except Exception as error:
        print(f"Error adding tracks: {error}")
        return None

    state.playlist_created = True
    return state.created_playlist_id

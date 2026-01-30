from spotify.playback import start_spotify_playback
from environment.weather import get_weather_data
from environment.traffic import get_traffic_status
from environment.location import get_surroundings_from_coords
from sensors.light_sensor import read_ambient_lux
from config import *
import json
import random
import time
import datetime as dt

MOOD_PARAMS = {
    "Calm": {"description": "Relaxing and peaceful tracks for calm driving"},
    "Alert": {"description": "High-energy music to keep you awake and focused"},
    "Drowsy": {"description": "Upbeat and positive music to combat drowsiness"},
}

MOOD_GENRES = {
    "Calm": ["chill", "lo-fi", "acoustic", "indie", "r&b", "ballad"],
    "Alert": ["hip-hop", "rap", "trap", "edm", "rock", "dance"],
    "Drowsy": ["pop", "k-pop", "dance", "funk", "synthpop", "electronic"],
}

SEARCH_KEYWORDS = {
    "Wakefulness": ["chill k-pop", "melodic rap chill", "soft k-rap", "relaxing k-pop", "ambient noise", "mellow melodic rap"],
    "Hypovigilance": ["k-pop hype", "k-rap energy", "rap workout", "fast k-pop"],
    "Drowsiness": ["upbeat k-pop", "dance k-pop", "catchy melodic rap", "rap bangers", "noise music upbeat"],
    "Microsleep": ["rage"]
}


def get_environment_conditions(lux=None, now=None, speed_kmh=None):
    """
    Determine environment descriptors based on:
    - lux (lighting)
    - time of day
    - speed (km/h)
    Returns a dict with time_of_day, light_condition, speed_condition, and mood_keywords
    """
    if now is None:
        now = dt.datetime.now()
    hour = now.hour

    # Time of day
    if 5 <= hour < 12:
        time_of_day = "morning"
    elif 12 <= hour < 17:
        time_of_day = "afternoon"
    elif 17 <= hour < 21:
        time_of_day = "evening"
    else:
        time_of_day = "night"

    # Lighting
    if lux is None:
        lux_val = 300.0
    else:
        try:
            lux_val = float(lux)
        except Exception:
            lux_val = 300.0

    if lux_val >= 800:
        light_condition = "bright"
    elif lux_val >= 200:
        light_condition = "dim"
    else:
        light_condition = "dark"

    # Speed
    if speed_kmh is None:
        speed_val = 0
    else:
        try:
            speed_val = float(speed_kmh)
        except Exception:
            speed_val = 0

    if speed_val >= 100:
        speed_condition = "fast"
    elif speed_val >= 40:
        speed_condition = "moderate"
    else:
        speed_condition = "slow"

    # Mood keywords based on light and speed
    mood_keywords = []
    if light_condition == "bright":
        mood_keywords += ["energetic", "upbeat", "bright"]
    elif light_condition == "dim":
        mood_keywords += ["focus", "groove", "midtempo"]
    else:
        mood_keywords += ["warm", "cozy", "soft"]

    if speed_condition == "fast":
        mood_keywords += ["driving", "intense"]
    elif speed_condition == "moderate":
        mood_keywords += ["steady", "balanced"]
    else:
        mood_keywords += ["relaxed", "mellow"]

    if time_of_day == "night":
        mood_keywords += ["chill", "ambient"]

    return {
        "time_of_day": time_of_day,
        "light_condition": light_condition,
        "speed_condition": speed_condition,
        "mood_keywords": list(dict.fromkeys(mood_keywords))
    }

def get_discovery_tracks(sp, mood, user_genres, max_tracks=400):
    """
    Collect many candidates from playlists matching keywords, batch-fetch artist genres,
    fuzzy-match against user_genres, and fallback to random selection so we never return empty.
    """
    discovery_tracks = []
    keywords = SEARCH_KEYWORDS.get(mood, ["chill"])
    all_tracks = []

    # gather candidate tracks from playlists matching keywords
    for keyword in keywords:
        try:
            results = sp.search(q=f"{keyword} playlist", type="playlist", limit=10)
            playlists = results.get("playlists", {}).get("items", [])
        except Exception as e:
            print(f"Search failed for '{keyword}': {e}")
            playlists = []
        for pl in playlists:
            try:
                items = sp.playlist_items(pl["id"], limit=80)["items"]
                for i in items:
                    track = i.get("track")
                    if track and track.get("uri"):
                        all_tracks.append(track)
                    if len(all_tracks) >= max_tracks * 2:
                        break
                if len(all_tracks) >= max_tracks * 2:
                    break
            except Exception as e:
                continue
        if len(all_tracks) >= max_tracks * 2:
            break

    print(f"🎧 Gathered {len(all_tracks)} discovery candidates for {mood}")

    if not all_tracks:
        return []

    # Batch-fetch unique artist genres
    artist_cache = {}
    unique_artist_ids = list({t["artists"][0]["id"] for t in all_tracks if t.get("artists") and t["artists"][0].get("id")})
    for i in range(0, len(unique_artist_ids), 50):
        batch = unique_artist_ids[i:i+50]
        try:
            res = sp.artists(batch).get("artists", [])
            for artist in res:
                artist_cache[artist["id"]] = [g.lower() for g in artist.get("genres", [])]
        except Exception as e:
            print(f"⚠️ Genre batch fetch failed ({i // 50}): {e}")

    # fuzzy match helper
    def fuzzy_genre_match(artist_genres, user_genres):
        if not artist_genres or not user_genres:
            return False
        for ag in artist_genres:
            for ug in user_genres:
                if ug in ag or ag in ug:
                    return True
        return False

    # apply filter — but keep track of candidates
    for track in all_tracks:
        try:
            aid = track["artists"][0]["id"]
            ag = artist_cache.get(aid, [])
            if fuzzy_genre_match(ag, user_genres):
                discovery_tracks.append(track)
            if len(discovery_tracks) >= max_tracks:
                break
        except Exception:
            continue

    # fallback: if nothing matched, pick random from candidates
    if not discovery_tracks:
        take = min(len(all_tracks), max_tracks)
        discovery_tracks = random.sample(all_tracks, take)

    print(f"✅ Using {len(discovery_tracks)} discovery tracks after filtering for {mood}")
    return discovery_tracks

def get_openai_music_decision(context):
    """
    Sends full driving + user context to OpenAI.
    Returns structured music selection intent.
    """

    SYSTEM_PROMPT = """
You are an expert AI music curator for driving.
Adapt music to driver alertness, traffic, environment, and personal taste.
Your output MUST be strict JSON only.
No explanations.
"""

    USER_PROMPT = f"""
Context:
{json.dumps(context, indent=2)}

Return JSON with:
- energy (0.0–1.0)
- valence (0.0–1.0)
- tempo_range_bpm [min, max]
- preferred_genres (array)
- avoid_genres (array)
- spotify_search_queries (array)
- familiarity_bias ("familiar" | "balanced" | "discovery")
- vocal_preference ("instrumental" | "vocal" | "mixed")
"""

    response = openai_client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT}
        ],
        temperature=0.3
    )

    return json.loads(response.choices[0].message.content)


def create_smart_playlist_fixed(sp, total_tracks=40, env_lux=None):
    """
    Creates a playlist based on driver mood, weather, lighting, speed, and surroundings.
    Automatically plays the playlist and deletes the old one if it exists.
    """
    global created_playlist_id, playlist_created, driver_state
    state = driver_state  

    # ---------------- Ask for user inputs ----------------


# Simulate ambient light for testing
    # try:
    #     lux_input = float(input("Enter simulated ambient light in lux (e.g., 300): "))
    # except Exception:
    #     lux_input = 300.0  # default fallback
    lux_input = read_ambient_lux()

# Fallback if sensor fails
    if lux_input is None:
        lux_input = 300.0
        print("⚠️ Using fallback lux value (300)")


    print(f"💡 Average ambient lux: {lux_input:.1f}")
# ------------------------------------------------------------------


    try:
        speed_input = float(input("🚗 Enter simulated driving speed (km/h): "))
    except Exception:
        speed_input = 0

    try:
        lat = float(input("🌍 Enter your latitude: "))
        lon = float(input("🌍 Enter your longitude: "))
    except Exception:
        lat, lon = 42.6977, 23.3219  # default: Sofia


    # --- Get live traffic condition ---
    TOMTOM_KEY = "9M7YdaLFAFD06NgSt1Vxwp5ROzZt0dBS"  # <-- Replace with your key
    traffic_status = get_traffic_status(lat, lon, speed_input, TOMTOM_KEY)

# Adjust mood weighting if in traffic
    if traffic_status == "heavy":
        print("🧘 Heavy traffic → shifting toward relaxing and calm tracks.")
        state = "calm"
    elif traffic_status == "moderate" and state == "alert":
        print("🚦 Moderate traffic → blending alert with calm tracks.")
        state = "neutral"

    # ---------------- Get environment and surroundings ----------------
    env = get_environment_conditions(lux_input, speed_kmh=speed_input)
    surroundings = get_surroundings_from_coords(lat, lon)
    print(f"🌤️ Environment: {env['time_of_day']} | {env['light_condition']} | {env['speed_condition']}")
    print(f"📍 Surroundings: {surroundings['city']}, {surroundings['country']}")

    # ---------------- Handle existing playlist ----------------
    if created_playlist_id:
        try:
            sp.current_user_unfollow_playlist(created_playlist_id)
            print(f"🗑️ Deleted old playlist {created_playlist_id}")
        except Exception as e:
            print(f"⚠️ Could not delete old playlist: {e}")
        created_playlist_id = None

    # ---------------- Create new playlist ----------------
    state = driver_state
    mood_params = MOOD_PARAMS.get(state, {"description": ""})
    playlist_name = f"Drive Mood – {state} Mode – {int(time.time())}"

    try:
        user_id = sp.current_user()["id"]
        playlist = sp.user_playlist_create(
            user=user_id, name=playlist_name, public=False, description=mood_params["description"]
        )
        created_playlist_id = playlist["id"]
        print(f"🎶 Created playlist: {playlist_name}")
    except Exception as e:
        print(f"❌ Error creating playlist: {e}")
        return None

    # ---------------- Get user’s top data ----------------
    try:
        top_tracks_full = sp.current_user_top_tracks(limit=50, time_range="medium_term")["items"]
        top_artists_full = sp.current_user_top_artists(limit=20, time_range="medium_term")["items"]
    except Exception:
        top_tracks_full, top_artists_full = [], []

    top_tracks = [t for t in top_tracks_full if t.get("uri")]
    top_artists = [a["id"] for a in top_artists_full if a.get("id")]

    user_genres = []
    for artist in top_artists_full:
        user_genres += [g.lower() for g in artist.get("genres", [])]
    user_genres = list(set(user_genres))

    # ---------------- Weather + Environment Influence ----------------
    weather = get_weather_data() or {}
    weather_keywords = []
    if weather:
        t = weather.get("temp")
        c = weather.get("condition", "")
        if "rain" in c or (t is not None and t < 10):
            weather_keywords = ["rainy day", "cozy", "soft"]
        elif "clear" in c and (t is not None and t > 20):
            weather_keywords = ["sunny", "bright", "energetic"]
        else:
            weather_keywords = ["upbeat", "positive", "chill"]

    surroundings_keywords = []
    if surroundings["country"].lower() in ["greece", "spain", "italy"]:
        surroundings_keywords = ["mediterranean", "sunny", "vibrant"]
    elif surroundings["country"].lower() in ["norway", "sweden", "finland"]:
        surroundings_keywords = ["nordic", "ambient", "chill"]
    elif surroundings["city"].lower() in ["sofia", "paris", "berlin"]:
        surroundings_keywords = ["urban", "modern", "city vibe"]

    # ---------------- Build keyword blend ----------------
  # --- use your own mapping instead of a default one ---
      # ---------------- Build keyword blend ----------------
# ---------------- OpenAI Context Assembly ----------------
    openai_context = {
        "driver_state": driver_state,
        "time_of_day": env["time_of_day"],
        "light_condition": env["light_condition"],
        "lux": lux_input,
        "speed_kmh": speed_input,
        "speed_condition": env["speed_condition"],
        "traffic": traffic_status,
        "weather": weather,
        "location": {
            "city": surroundings["city"],
            "country": surroundings["country"],
            "features": surroundings["features"]
        },
        "user_profile": {
            "top_genres": user_genres[:10],
            "top_artists": [a["name"] for a in top_artists_full[:5]],
            "top_tracks": [t["name"] for t in top_tracks_full[:5]]
        }
    }

    print("🧠 Sending context to OpenAI...")
    ai_decision = get_openai_music_decision(openai_context)

    print("🤖 OpenAI decision:", ai_decision)

    final_keywords = ai_decision["spotify_search_queries"]
    preferred_genres = ai_decision["preferred_genres"]
    avoid_genres = ai_decision["avoid_genres"]
    energy_target = ai_decision["energy"]
    tempo_range = ai_decision["tempo_range_bpm"]


    
    if not final_keywords:
        final_keywords = ["k-pop", "k-rap"]

    print(f"🔎 Using keywords: {final_keywords[:12]}")



    # ---------------- Fetch discovery & recommendations ----------------
    discovery_tracks_full = get_discovery_tracks(sp, state, user_genres, max_tracks=int(total_tracks * 1.5))
    rec_tracks_full = []
    try:
        seed_tracks = [t.get("id") for t in top_tracks_full[:5] if t.get("id")]
        seed_artists = list(dict.fromkeys(top_artists))[:5]
        rec_resp = sp.recommendations(
            seed_tracks=seed_tracks[:2],
            seed_artists=seed_artists[:2],
            seed_genres=preferred_genres[:3],
            target_energy=energy_target,
            min_tempo=tempo_range[0],
            max_tempo=tempo_range[1],
            limit=25
        )
        rec_tracks_full = rec_resp.get("tracks", []) if rec_resp else []
    except Exception:
        pass

    # ---------------- Combine & Deduplicate ----------------
    random.shuffle(discovery_tracks_full)
    random.shuffle(top_tracks)
    random.shuffle(rec_tracks_full)

    combined = discovery_tracks_full[:int(total_tracks * 0.7)] + \
               top_tracks[:int(total_tracks * 0.15)] + \
               rec_tracks_full[:int(total_tracks * 0.15)]
    random.shuffle(combined)

    seen, uris = set(), []
    for t in combined:
        if not t: continue
        name = (t.get("name") or "").lower().strip()
        artist = (t["artists"][0]["name"] if t.get("artists") else "").lower().strip()
        key = f"{name}-{artist}"
        if key not in seen and t.get("uri"):
            seen.add(key)
            uris.append(t["uri"])
        if len(uris) >= total_tracks: break

    # ---------------- Add tracks & start playback ----------------
    try:
        for i in range(0, len(uris), 100):
            sp.playlist_add_items(created_playlist_id, uris[i:i+100])
            time.sleep(0.2)
        print(f"✅ Added {len(uris)} tracks to '{playlist_name}'")
        start_spotify_playback(sp, created_playlist_id)
    except Exception as e:
        print(f"❌ Error adding tracks: {e}")

    playlist_created = True
    return created_playlist_id
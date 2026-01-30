import requests

def get_traffic_status(lat, lon, current_speed, tomtom_key):
    """
    Compare driver speed to TomTom traffic data and infer traffic condition.
    Returns: 'heavy', 'moderate', or 'free'.
    """

    # Recommended zoom: 10–22 (higher zoom = smaller area)
    url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    params = {
        "point": f"{lat},{lon}",
        "unit": "KMPH",
        "key": tomtom_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ TomTom API error {response.status_code}: {response.text}")
            return "unknown"

        data = response.json()
        segment = data.get("flowSegmentData")
        if not segment:
            print("❌ No flowSegmentData returned.")
            return "unknown"

        free_flow = segment.get("freeFlowSpeed", 0)
        current_flow = segment.get("currentSpeed", 0)
        print(f"TomTom free flow speed: {free_flow} km/h | Current traffic speed: {current_flow} km/h | Your speed: {current_speed} km/h")

        # Compare current driving speed with free-flow
        if current_speed < free_flow * 0.4:
            print("🚗 Heavy traffic detected.")
            return "heavy"
        elif current_speed < free_flow * 0.8:
            print("🚙 Moderate traffic.")
            return "moderate"
        else:
            print("🏎️ Free-flowing traffic.")
            return "free"
    except Exception as e:
        print(f"❌ Error checking TomTom traffic: {e}")
        return "unknown"

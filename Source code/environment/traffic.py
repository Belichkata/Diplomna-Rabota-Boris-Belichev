import requests

from config import SETTINGS


def get_traffic_status(lat, lon, current_speed):
    if not SETTINGS.tomtom_api_key:
        return "unknown"
    try:
        response = requests.get(
            "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json",
            params={
                "point": f"{lat},{lon}",
                "unit": "KMPH",
                "key": SETTINGS.tomtom_api_key,
            },
            timeout=10,
        )
        if response.status_code != 200:
            print(f"TomTom API error {response.status_code}: {response.text}")
            return "unknown"
        segment = response.json().get("flowSegmentData")
        if not segment:
            return "unknown"
        free_flow = segment.get("freeFlowSpeed", 0)
        if free_flow <= 0:
            return "unknown"
        if current_speed < free_flow * 0.4:
            return "heavy"
        if current_speed < free_flow * 0.8:
            return "moderate"
        return "free"
    except Exception as error:
        print(f"Error checking TomTom traffic: {error}")
        return "unknown"

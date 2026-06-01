import requests

from config import SETTINGS


def get_surroundings_from_coords(lat, lon):
    surroundings = {"city": "Unknown", "state": "Unknown", "country": "Unknown", "features": []}
    if not SETTINGS.geoapify_api_key:
        return surroundings
    try:
        reverse_response = requests.get(
            "https://api.geoapify.com/v1/geocode/reverse",
            params={"lat": lat, "lon": lon, "apiKey": SETTINGS.geoapify_api_key},
            timeout=6,
        )
        reverse_data = reverse_response.json()
        if reverse_data.get("features"):
            props = reverse_data["features"][0]["properties"]
            surroundings["city"] = props.get("city") or props.get("town") or props.get("village") or "Unknown"
            surroundings["state"] = props.get("state") or "Unknown"
            surroundings["country"] = props.get("country") or "Unknown"
            surroundings["road"] = props.get("road") or props.get("street")
            surroundings["natural"] = props.get("natural")
            surroundings["water"] = props.get("water")

        places_response = requests.get(
            "https://api.geoapify.com/v2/places",
            params={
                "categories": "natural.beach,natural.water,poi.park,natural.mountain",
                "filter": f"circle:{lon},{lat},1000",
                "limit": 5,
                "apiKey": SETTINGS.geoapify_api_key,
            },
            timeout=6,
        )
        places_data = places_response.json()
        for feature in places_data.get("features", []):
            properties = feature.get("properties", {})
            categories = properties.get("categories", [])
            if categories:
                surroundings["features"].append(
                    {
                        "name": properties.get("name") or properties.get("formatted", ""),
                        "category": categories,
                    }
                )
        return surroundings
    except Exception as error:
        print(f"Error fetching surroundings: {error}")
        return surroundings

import requests

def get_surroundings_from_coords(lat, lon):
    """
    Get detailed surroundings (city, country, landscape, nearby water, etc.)
    using Geoapify reverse geocoding + places API.
    """
    api_key = "96996f00c3bd49f8a1b5b85195480367"
    base_url = "https://api.geoapify.com/v1/geocode/reverse"
    places_url = "https://api.geoapify.com/v2/places"

    surroundings = {"city": "Unknown", "state": "Unknown", "country": "Unknown", "features": []}

    try:
        # --- Reverse geocode for admin info
        url = f"{base_url}?lat={lat}&lon={lon}&apiKey={api_key}"
        r = requests.get(url, timeout=6)
        data = r.json()

        if "features" in data and data["features"]:
            props = data["features"][0]["properties"]
            surroundings["city"] = props.get("city") or props.get("town") or props.get("village") or "Unknown"
            surroundings["state"] = props.get("state") or "Unknown"
            surroundings["country"] = props.get("country") or "Unknown"
            surroundings["road"] = props.get("road") or props.get("street") or None
            surroundings["natural"] = props.get("natural")
            surroundings["water"] = props.get("water")

        # --- Search nearby for landscape features (within ~1km)
        radius_m = 1000
        categories = "natural.beach,natural.water,poi.park,natural.mountain"
        places_params = {
            "categories": categories,
            "filter": f"circle:{lon},{lat},{radius_m}",
            "limit": 5,
            "apiKey": api_key,
        }
        rp = requests.get(places_url, params=places_params, timeout=6)
        pd = rp.json()

        if "features" in pd:
            for f in pd["features"]:
                cat = f["properties"].get("categories", [])
                name = f["properties"].get("name") or f["properties"].get("formatted", "")
                if cat:
                    surroundings["features"].append({"name": name, "category": cat})

        print(f"📍 Detected: {surroundings}")
        return surroundings

    except Exception as e:
        print(f"❌ Error fetching surroundings: {e}")
        return surroundings
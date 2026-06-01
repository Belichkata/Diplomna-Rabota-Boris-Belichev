import requests

from config import SETTINGS


def get_weather_data():
    if not SETTINGS.openweather_api_key:
        return None
    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": f"{SETTINGS.default_city},{SETTINGS.default_country_code}",
                "appid": SETTINGS.openweather_api_key,
                "units": "metric",
            },
            timeout=6,
        )
        data = response.json()
        if data.get("cod") != 200:
            return None
        return {
            "temp": data["main"]["temp"],
            "condition": data["weather"][0]["main"].lower(),
        }
    except Exception as error:
        print(f"Weather fetch error: {error}")
        return None

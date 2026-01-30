import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_weather_data():

    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        print("OPENWEATHER_API_KEY not set")
        return None
    
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q=Sofia,BG&appid={api_key}&units=metric"
        r = requests.get(url, timeout=6)
        d = r.json()
        if d.get("cod") != 200:
            return None
        return {"temp": d["main"]["temp"], "condition": d["weather"][0]["main"].lower()}
    except Exception as e:
        print(f"Weather fetch error: {e}")
        return None
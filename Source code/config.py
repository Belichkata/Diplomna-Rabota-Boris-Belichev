from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return BASE_DIR / path


_load_env_file(REPO_DIR / ".env")


SPOTIFY_SCOPE = (
    "playlist-read-private playlist-modify-private playlist-modify-public "
    "user-read-playback-state user-read-currently-playing user-top-read "
    "user-library-read user-follow-read user-modify-playback-state"
)

LEFT_EYE = list(range(42, 48))
RIGHT_EYE = list(range(36, 42))
EYE_AR_THRESH = 0.3


@dataclass(frozen=True)
class Settings:
    app_secret_key: str
    flask_debug: bool
    openai_api_key: str
    openai_model: str
    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str
    openweather_api_key: str
    geoapify_api_key: str
    tomtom_api_key: str
    default_city: str
    default_country_code: str
    default_latitude: float
    default_longitude: float
    simulated_speed_kmh: float
    default_lux: float
    total_tracks: int
    monitoring_duration_seconds: int
    combined_data_file: Path
    shape_predictor_path: Path


SETTINGS = Settings(
    app_secret_key=os.getenv("APP_SECRET_KEY", "change-me"),
    flask_debug=_env_bool("FLASK_DEBUG", False),
    openai_api_key=os.getenv("OPENAI_API_KEY", ""),
    openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
    spotify_client_id=os.getenv("SPOTIFY_CLIENT_ID", ""),
    spotify_client_secret=os.getenv("SPOTIFY_CLIENT_SECRET", ""),
    spotify_redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:5000/callback"),
    openweather_api_key=os.getenv("OPENWEATHER_API_KEY", ""),
    geoapify_api_key=os.getenv("GEOAPIFY_API_KEY", ""),
    tomtom_api_key=os.getenv("TOMTOM_API_KEY", ""),
    default_city=os.getenv("DEFAULT_CITY", "Sofia"),
    default_country_code=os.getenv("DEFAULT_COUNTRY_CODE", "BG"),
    default_latitude=_env_float("DEFAULT_LATITUDE", 42.6977),
    default_longitude=_env_float("DEFAULT_LONGITUDE", 23.3219),
    simulated_speed_kmh=_env_float("SIMULATED_SPEED_KMH", 0.0),
    default_lux=_env_float("DEFAULT_LUX", 300.0),
    total_tracks=_env_int("TOTAL_TRACKS", 40),
    monitoring_duration_seconds=_env_int("MONITORING_DURATION_SECONDS", 30),
    combined_data_file=_resolve_path(os.getenv("COMBINED_DATA_FILE", "combined_data.json")),
    shape_predictor_path=_resolve_path(
        os.getenv("SHAPE_PREDICTOR_PATH", "models/shape_predictor_68_face_landmarks.dat")
    ),
)

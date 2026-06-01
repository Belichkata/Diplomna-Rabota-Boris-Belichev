import json

from config import SETTINGS
from utils import state


def update_json() -> None:
    data = {"driver": {"state": state.driver_state}}
    existing = {}
    if SETTINGS.combined_data_file.exists():
        try:
            existing = json.loads(SETTINGS.combined_data_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
    existing.update(data)
    SETTINGS.combined_data_file.write_text(
        json.dumps(existing, indent=4),
        encoding="utf-8",
    )

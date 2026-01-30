import json, os
from config import combined_file

def update_json(driver_state):
    data = {"driver": {"state": driver_state}}
    try:
        if os.path.exists(combined_file):
            with open(combined_file, "r") as f:
                old = json.load(f)
        else:
            old = {}
        old.update(data)
        with open(combined_file, "w") as f:
            json.dump(old, f, indent=4)
    except Exception as e:
        print(f"Error writing json: {e}")

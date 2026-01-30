import os
from openai import OpenAI

openai_client = OpenAI(api_key="")

CLIENT_ID = "edb8e43341cd46eb8c240d3bfd01e590"
CLIENT_SECRET = "49dba5129cdd414187ac758a53c2b7f4"
REDIRECT_URI = "http://127.0.0.1:5000/callback"

SCOPE = (
    "playlist-read-private playlist-modify-private playlist-modify-public "
    "user-read-playback-state user-read-currently-playing user-top-read "
    "user-library-read user-follow-read user-modify-playback-state"
)


EAR_THRESHOLD = 0.21
EYE_AR_THRESH = 0.3
MOUTH_OPEN_THRESH = 0.65


combined_file = "combined_data.json"

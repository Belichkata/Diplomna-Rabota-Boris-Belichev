from web.server import app
from config import SETTINGS


if __name__ == "__main__":
    app.run(debug=SETTINGS.flask_debug, use_reloader=False)

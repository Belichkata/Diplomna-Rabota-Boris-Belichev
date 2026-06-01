import time

from utils import state

try:
    from picamera2 import Picamera2
except ImportError:
    Picamera2 = None


def close_picam2():
    if state.picam2 is None:
        return
    try:
        state.picam2.stop()
    except Exception:
        pass
    try:
        state.picam2.close()
    except Exception:
        pass
    state.picam2 = None


def start_picam2():
    if Picamera2 is None:
        return None
    close_picam2()
    camera = Picamera2()
    config = camera.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
    camera.configure(config)
    camera.start()
    time.sleep(1)
    state.picam2 = camera
    return camera

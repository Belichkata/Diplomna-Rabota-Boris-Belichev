import time

from camera.face_detection import LEFT_EYE, RIGHT_EYE, eye_aspect_ratio, shape_to_points
from camera.pycam import close_picam2, start_picam2
from config import EYE_AR_THRESH, SETTINGS
from spotify.auth import get_spotify_client
from spotify.playlist import create_smart_playlist
from utils import state
from utils.json_utils import update_json

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import dlib
except ImportError:
    dlib = None


def _evaluate_driver_state(blink_timestamps, blink_durations, monitoring_duration):
    blink_frequency = (len(blink_timestamps) / monitoring_duration) * 60
    average_blink_duration = sum(blink_durations) / len(blink_durations) if blink_durations else 0.0
    if blink_frequency <= 5:
        return "Wakefulness"
    if 6 <= blink_frequency <= 10:
        return "Hypovigilance"
    if average_blink_duration >= 0.5 or blink_frequency > 20:
        return "Microsleep"
    return "Drowsiness"


def monitor_driver():
    if cv2 is None or dlib is None:
        print("OpenCV and dlib are required for driver monitoring.")
        state.monitoring_active = False
        return
    if not SETTINGS.shape_predictor_path.exists():
        print(f"Missing shape predictor model: {SETTINGS.shape_predictor_path}")
        state.monitoring_active = False
        return

    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor(str(SETTINGS.shape_predictor_path))
    camera = start_picam2()
    if camera is None:
        print("Picamera2 is unavailable.")
        state.monitoring_active = False
        return

    state.driver_state = "Wakefulness"
    start_time = time.time()
    blink_timestamps = []
    blink_durations = []
    blink_start_time = None

    cv2.destroyAllWindows()
    cv2.namedWindow("Driver Monitor", cv2.WINDOW_NORMAL)

    try:
        while state.monitoring_active and not state.stop_event.is_set():
            frame = camera.capture_array()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rects = detector(gray, 0)
            now = time.time()
            ear = 0.0

            if rects:
                shape = predictor(gray, rects[0])
                points = shape_to_points(shape)
                left_ear = eye_aspect_ratio([points[index] for index in LEFT_EYE])
                right_ear = eye_aspect_ratio([points[index] for index in RIGHT_EYE])
                ear = (left_ear + right_ear) / 2.0
                if ear < EYE_AR_THRESH:
                    if blink_start_time is None:
                        blink_start_time = now
                elif blink_start_time is not None:
                    duration = now - blink_start_time
                    if 0.05 < duration < 2.0:
                        blink_timestamps.append(now)
                        blink_durations.append(duration)
                    blink_start_time = None

            blink_timestamps = [timestamp for timestamp in blink_timestamps if now - timestamp <= 60]

            if now - start_time >= SETTINGS.monitoring_duration_seconds:
                blink_count = len(blink_timestamps)
                recent_blink_durations = blink_durations[-blink_count:] if blink_count else []
                state.driver_state = _evaluate_driver_state(
                    blink_timestamps,
                    recent_blink_durations,
                    SETTINGS.monitoring_duration_seconds,
                )
                update_json()
                if not state.playlist_created:
                    spotify_client = get_spotify_client()
                    if spotify_client:
                        create_smart_playlist(spotify_client, total_tracks=SETTINGS.total_tracks)
                        state.monitoring_active = False
                        break
                start_time = now

            cv2.putText(frame, f"State: {state.driver_state}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imshow("Driver Monitor", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                state.monitoring_active = False
                break
    finally:
        close_picam2()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        state.monitoring_thread = None

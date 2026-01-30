# camera/driver_monitor.py

import cv2
import time
import threading

from config import EAR_THRESHOLD, MOUTH_OPEN_THRESH
from camera.face_detection import (
    mp_face_mesh,
    LEFT_EYE,
    RIGHT_EYE,
    eye_aspect_ratio,
    mouth_open_ratio,
)

from utils.json_utils import update_json
from spotify.auth import get_spotify_client
from spotify.playlist import create_smart_playlist_fixed

def monitor_driver():
    global driver_state, playlist_created, monitoring_active, created_playlist_id
    global stop_event

    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)



    driver_state = "Wakefulness"
    monitoring_duration = 30  # evaluate every 30 sec
    start_time = time.time()

    blink_timestamps = []
    yawn_timestamps = []
    blink_start_time = None
    blink_durations = []

    with mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as face_mesh:

        while monitoring_active and cap.isOpened() and not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                break

            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)
            now = time.time()

            ear = 0.0
            mouth_ratio = 0.0

            if results.multi_face_landmarks:
                lm = results.multi_face_landmarks[0]

                left_ear = eye_aspect_ratio(lm.landmark, LEFT_EYE, w, h)
                right_ear = eye_aspect_ratio(lm.landmark, RIGHT_EYE, w, h)
                ear = (left_ear + right_ear) / 2

                # -------------------------------
                # BLINK DETECTION
                # -------------------------------
                if ear < EAR_THRESHOLD:
                    if blink_start_time is None:
                        blink_start_time = now
                else:
                    if blink_start_time is not None:
                        duration = now - blink_start_time

                        # FILTER OUT FALSE BLINKS
                        if 0.05 < duration < 2.0:
                            blink_durations.append(duration)
                            blink_timestamps.append(now)

                        blink_start_time = None

                # -------------------------------
                # YAWN DETECTION
                # -------------------------------
                mouth_ratio = mouth_open_ratio(lm.landmark, w, h)
                if mouth_ratio > MOUTH_OPEN_THRESH:
                    yawn_timestamps.append(now)

            # -------------------------------
            # CLEAN OLD DATA (last 60 sec)
            # -------------------------------
            blink_timestamps = [t for t in blink_timestamps if now - t <= 60]
            yawn_timestamps = [t for t in yawn_timestamps if now - t <= 60]

            # -------------------------------
            # EVALUATE DRIVER EVERY 30 SEC
            # -------------------------------
            if now - start_time >= monitoring_duration:
                window_start = now - monitoring_duration
                window_blinks = [t for t in blink_timestamps if t >= window_start]

                # Align durations with blink count
                window_durations = blink_durations[-len(window_blinks):] if window_blinks else []

                blink_freq = (len(window_blinks) / monitoring_duration) * 60
                avg_bd = sum(window_durations) / len(window_durations) if window_durations else 0.0

                print(f"🧠 Blinks (30s): {len(window_blinks)}")
                print(f"🧮 Blink freq: {blink_freq:.1f}/min")
                print(f"⏱️ Avg blink duration: {avg_bd:.3f}s")

                # ------------------------------------------------
                # NEW STATE MODEL (Stable + Realistic)
                # ------------------------------------------------

                if blink_freq < 15 and avg_bd < 0.25:
                    driver_state = "Wakefulness"

                elif 15 <= blink_freq <= 28 and avg_bd < 0.30:
                    driver_state = "Hypovigilance(Calm)"

                elif blink_freq > 28 and 0.30 <= avg_bd < 0.50:
                    driver_state = "Drowsiness"

                elif blink_freq > 28 and avg_bd >= 0.50:
                    driver_state = "Microsleep"

                else:
                    driver_state = "Wakefulness"

                update_json()
                print(f"🟢 State: {driver_state}")

                # Create playlist only once
                if not playlist_created:
                    sp = get_spotify_client()
                    if sp:
                        create_smart_playlist_fixed(sp, total_tracks=40)
                        playlist_created = True
                        monitoring_active = False
                        print("✅ Playlist created — monitoring stops.")
                        break

                start_time = now  # reset evaluation timer

            # -------------------------------
            # UI
            # -------------------------------
            cv2.putText(frame, f"State: {driver_state}", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
            cv2.putText(frame, f"EAR: {ear:.3f}", (30, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            timer = max(0, monitoring_duration - (now - start_time))
            cv2.putText(frame, f"Next eval: {timer:.1f}s", (30, 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            cv2.imshow("Driver Monitor", frame)
            if cv2.waitKey(5) & 0xFF == 27:
                monitoring_active = False
                break

    cap.release()
    cv2.destroyAllWindows()
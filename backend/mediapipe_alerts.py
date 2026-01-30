import cv2
import mediapipe as mp
import base64
import numpy as np
import time
import math

mp_face = mp.solutions.face_mesh

face_mesh = mp_face.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

LAST_FACE_SEEN = {}
LAST_HEAD_POS = {}

COOLDOWN = 3  # seconds

def process_frame(base64_image: str, student_id: str):
    events = []

    # -------- decode image --------
    try:
        img_bytes = base64.b64decode(base64_image)
        frame = cv2.imdecode(
            np.frombuffer(img_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )
    except Exception as e:
        print("❌ decode error:", e)
        return []

    if frame is None:
        print("❌ frame is None")
        return []

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)
    now = time.time()

    # -------- FACE NOT DETECTED --------
    if not results.multi_face_landmarks:
        last = LAST_FACE_SEEN.get(student_id, 0)
        if now - last > COOLDOWN:
            events.append({
                "type": "face_not_detected",
                "confidence": None
            })
            LAST_FACE_SEEN[student_id] = now

        print("📢 mediapipe events:", events)
        return events

    LAST_FACE_SEEN[student_id] = now
    landmarks = results.multi_face_landmarks[0].landmark

    # -------- LOOKING AWAY --------
    nose = landmarks[1]
    left_eye = landmarks[33]
    right_eye = landmarks[263]

    eye_center_x = (left_eye.x + right_eye.x) / 2
    gaze_diff = abs(nose.x - eye_center_x)

    if gaze_diff > 0.02:
        events.append({
            "type": "looking_away",
            "confidence": round(gaze_diff, 3)
        })

    # -------- HEAD MOVEMENT --------
    curr_pos = (nose.x, nose.y)
    last_pos = LAST_HEAD_POS.get(student_id)

    if last_pos:
        dist = math.dist(last_pos, curr_pos)
        if dist > 0.08:
            events.append({
                "type": "unusual_head_movement",
                "confidence": round(dist, 3)
            })

    LAST_HEAD_POS[student_id] = curr_pos

    print("📢 mediapipe events:", events)
    return events

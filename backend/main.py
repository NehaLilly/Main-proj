print("🔥🔥🔥 THIS MAIN.PY IS RUNNING 🔥🔥🔥")

from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time

from storage import add_event, get_events, get_all_students
from yolo import detect_objects
from mediapipe_alerts import process_frame

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= MODELS =================
class ProctorEvent(BaseModel):
    studentId: str
    timestamp: int
    type: str
    severity: str
    confidence: float | None = None

# ================= BASIC EVENT =================
@app.post("/log_event")
def log_event(event: ProctorEvent):
    add_event(event.studentId, event.dict())
    return {"status": "ok"}

# ================= ADMIN =================
@app.get("/admin/students")
def list_students():
    return get_all_students()

@app.get("/admin/students/{student_id}/events")
def student_events(student_id: str):
    return get_events(student_id)

# ================= YOLO =================
@app.post("/detect_objects")
def detect_objects_api(payload: dict = Body(...)):
    student_id = payload["studentId"]
    image = payload["image"]

    detections = detect_objects(image, student_id)
    now = int(time.time() * 1000)

    for d in detections:
        add_event(student_id, {
            "studentId": student_id,
            "timestamp": now,
            "type": d["type"],
            "severity": "high",
            "confidence": d.get("confidence", 0),
        })

    return {"detections": detections}

# ================= MEDIAPIPE =================
@app.post("/mediapipe_detect")
def mediapipe_detect(payload: dict = Body(...)):
    student_id = payload["studentId"]
    image = payload["image"]

    events = process_frame(image, student_id)

    # 🔥🔥🔥 ADD THIS LINE (VERY IMPORTANT)
    print("🚨 MEDIAPIPE EVENTS:", events)

    now = int(time.time() * 1000)

    for e in events:
        add_event(student_id, {
            "studentId": student_id,
            "timestamp": now,
            "type": e["type"],
            "severity": "medium",
            "confidence": e.get("confidence"),
        })

    return {"events": events}
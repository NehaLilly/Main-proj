from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from storage import add_event, get_events, get_all_students
from yolo import detect_objects
import time
import subprocess
import tempfile
import os

app = FastAPI()

# =========================
# CORS CONFIG
# =========================
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

# =========================
# MODELS
# =========================
class ProctorEvent(BaseModel):
    studentId: str
    timestamp: int
    type: str
    severity: str
    confidence: float | None = None

class RunCodeRequest(BaseModel):
    language: str
    code: str

# =========================
# BASIC PROCTOR EVENTS
# =========================
@app.post("/log_event")
def log_event(event: ProctorEvent):
    add_event(event.studentId, event.dict())
    return {"status": "ok"}

# =========================
# ADMIN APIs
# =========================
@app.get("/admin/students")
def list_students():
    return get_all_students()

@app.get("/admin/students/{student_id}/events")
def student_events(student_id: str):
    return get_events(student_id)

# =========================
# YOLO OBJECT DETECTION
# =========================
@app.post("/detect_objects")
def detect_objects_api(payload: dict = Body(...)):
    """
    payload = {
        studentId: str,
        image: base64_string
    }
    """
    student_id = payload["studentId"]
    image = payload["image"]

    detections = detect_objects(image, student_id)

    now = int(time.time() * 1000)

    # 🔥 IMPORTANT: save every detection as ADMIN EVENT
    for d in detections:
        add_event(student_id, {
            "studentId": student_id,
            "timestamp": now,
            "type": d["type"],               # phone_detected, book_detected, etc
            "severity": "high",
            "confidence": d.get("confidence", 0),
        })

    return {
        "detections": detections
    }

# =========================
# MULTI-LANGUAGE CODE RUNNER
# =========================
@app.post("/run")
def run_code(req: RunCodeRequest):
    with tempfile.TemporaryDirectory() as tmp:
        try:
            if req.language == "python":
                path = os.path.join(tmp, "main.py")
                open(path, "w").write(req.code)
                cmd = ["python", path]

            elif req.language == "javascript":
                path = os.path.join(tmp, "main.js")
                open(path, "w").write(req.code)
                cmd = ["node", path]

            elif req.language == "c":
                src = os.path.join(tmp, "main.c")
                exe = os.path.join(tmp, "a.out")
                open(src, "w").write(req.code)
                subprocess.run(["gcc", src, "-o", exe], check=True)
                cmd = [exe]

            elif req.language == "cpp":
                src = os.path.join(tmp, "main.cpp")
                exe = os.path.join(tmp, "a.out")
                open(src, "w").write(req.code)
                subprocess.run(["g++", src, "-o", exe], check=True)
                cmd = [exe]

            elif req.language == "java":
                src = os.path.join(tmp, "Main.java")
                open(src, "w").write(req.code)
                subprocess.run(["javac", src], check=True)
                cmd = ["java", "-cp", tmp, "Main"]

            else:
                return {"stderr": "Unsupported language"}

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exitCode": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {"stderr": "Execution timed out"}
        except Exception as e:
            return {"stderr": str(e)}

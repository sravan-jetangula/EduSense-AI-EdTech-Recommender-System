"""
main.py
=======
FastAPI application entry point for the EdTech AI Recommender System.

Run with:
    uvicorn backend.main:app --reload --port 8000

Improvements over original:
  - Structured logging configured at startup.
  - Data loading errors surfaced as startup exceptions with clear messages.
  - GET /analyze and GET /recommend added alongside POST variants for
    easier browser/curl testing (both methods work).
  - /health endpoint added for liveness checks.
  - Student and question counts included in the root response.
"""

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.utils.data_processor import (
    load_students,
    load_questions,
    load_dost_config,
    strip_html,
)
from backend.services.analytics_service import analyze_student, compute_leaderboard
from backend.services.recommender_service import generate_recommendations

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "sample_data"

# ---------------------------------------------------------------------------
# Load data at startup
# ---------------------------------------------------------------------------
try:
    students_raw = load_students(str(DATA_DIR / "student_performance.json"))
    questions_raw = load_questions(str(DATA_DIR / "question_bank.json"))
    dost_config = load_dost_config(str(DATA_DIR / "dost_config.json"))
except FileNotFoundError as exc:
    logger.error("Required data file not found: %s", exc)
    raise SystemExit(f"Data file missing: {exc}") from exc

# Fast-lookup indices
students_index: dict = {s["student_id"]: s for s in students_raw}

questions_index: dict = {}
for _q in questions_raw:
    _qid = _q.get("qid")
    _oid = _q.get("_id")
    if _qid:
        questions_index[_qid] = _q
    if _oid:
        questions_index[_oid] = _q

logger.info(
    "Startup complete — %d students, %d questions, %d DOST types",
    len(students_raw),
    len(questions_raw),
    len(dost_config.get("dost_types", {})),
)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="EdTech AI Recommender",
    description="AI-powered JEE/NEET student learning recommender system",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Root + health
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "EdTech AI Recommender API is running",
        "version": "1.1.0",
        "students": len(students_raw),
        "questions": len(questions_raw),
        "dost_types": len(dost_config.get("dost_types", {})),
        "endpoints": [
            "GET  /health",
            "GET  /students",
            "GET  /analyze/{student_id}",
            "POST /analyze/{student_id}",
            "GET  /recommend/{student_id}",
            "POST /recommend/{student_id}",
            "GET  /question/{question_id}",
            "GET  /leaderboard",
            "GET  /dost_config",
        ],
    }


@app.get("/health")
def health():
    """Liveness check."""
    return {"status": "ok", "students": len(students_raw), "questions": len(questions_raw)}


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------

@app.get("/students")
def list_students():
    return [
        {"student_id": s["student_id"], "name": s.get("name", s["student_id"])}
        for s in students_raw
    ]


# ---------------------------------------------------------------------------
# Analyze  (GET + POST)
# ---------------------------------------------------------------------------

def _do_analyze(student_id: str) -> dict:
    student = students_index.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")
    return analyze_student(student)


@app.get("/analyze/{student_id}")
def analyze_get(student_id: str):
    return _do_analyze(student_id)


@app.post("/analyze/{student_id}")
def analyze_post(student_id: str):
    return _do_analyze(student_id)


# ---------------------------------------------------------------------------
# Recommend  (GET + POST)
# ---------------------------------------------------------------------------

def _do_recommend(student_id: str) -> dict:
    student = students_index.get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")
    return generate_recommendations(student, students_raw, questions_raw, dost_config)


@app.get("/recommend/{student_id}")
def recommend_get(student_id: str):
    return _do_recommend(student_id)


@app.post("/recommend/{student_id}")
def recommend_post(student_id: str):
    return _do_recommend(student_id)


# ---------------------------------------------------------------------------
# Question viewer
# ---------------------------------------------------------------------------

@app.get("/question/{question_id}")
def get_question(question_id: str):
    q = questions_index.get(question_id)
    if not q:
        # Case-insensitive fallback
        for k, v in questions_index.items():
            if str(k).lower() == question_id.lower():
                q = v
                break
    if not q:
        raise HTTPException(status_code=404, detail=f"Question '{question_id}' not found")

    clean = dict(q)
    clean["question"] = strip_html(clean.get("question", ""))
    return clean


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

@app.get("/leaderboard")
def leaderboard():
    return compute_leaderboard(students_raw)


# ---------------------------------------------------------------------------
# DOST config
# ---------------------------------------------------------------------------

@app.get("/dost_config")
def get_dost_config():
    return dost_config

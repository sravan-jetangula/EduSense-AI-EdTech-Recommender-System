"""
data_processor.py
=================
Handles all messy, inconsistent real-world data normalisation for the
EdTech recommender system. Converts heterogeneous formats into clean,
analysis-ready structures.

Improvements over original:
  - TOPIC_SUBJECT_MAP added: every canonical topic is explicitly bound to its
    parent subject (Physics / Chemistry / Mathematics / Biology).  This
    prevents subject misclassification in recommendations.
  - normalize_marks: the "+48 -8" branch now uses a more meaningful
    normalisation — net score as a fraction of total marks, not an
    arbitrary "+10" denominator estimate.
  - normalize_question: preserves the explicit subject field and adds a
    subject_from_topic fallback so downstream code can trust it.
  - load_questions: dedup considers both qid and _id independently,
    avoiding false duplicates when one field is absent.
"""

import re
import json
import logging
from typing import Union, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Marks Normalisation
# ---------------------------------------------------------------------------

def normalize_marks(marks_raw: Union[str, int, float, None]) -> Optional[float]:
    """
    Convert any marks format to a 0-100 percentage float.

    Supported formats:
        - "39/100"          -> 39.0
        - "+48 -8"          -> net score as % of total marks attempted
        - "49/120 (40.8%)"  -> 40.8  (explicit percentage wins)
        - 49                -> 49.0  (assumed already out of 100)
        - "22"              -> 22.0
        - None              -> None
    """
    if marks_raw is None:
        logger.debug("Received None marks; returning None")
        return None

    if isinstance(marks_raw, (int, float)):
        return round(min(float(marks_raw), 100.0), 2)

    marks_str = str(marks_raw).strip()

    # Pattern 1: "49/120 (40.8%)" - prefer explicit percentage
    pct_match = re.search(r"\((\d+\.?\d*)%\)", marks_str)
    if pct_match:
        return round(float(pct_match.group(1)), 2)

    # Pattern 2: "39/100" or "82/120"
    fraction_match = re.match(r"^(\d+\.?\d*)\s*/\s*(\d+\.?\d*)$", marks_str)
    if fraction_match:
        numerator = float(fraction_match.group(1))
        denominator = float(fraction_match.group(2))
        if denominator > 0:
            return round((numerator / denominator) * 100, 2)

    # Pattern 3: "+48 -8" (correct marks, wrong penalty)
    # Net = correct - wrong_penalty; total possible = correct + wrong_penalty
    # This gives sensible score with negative marking schemes
    plus_minus_match = re.match(r"^\+(\d+)\s+-(\d+)$", marks_str)
    if plus_minus_match:
        correct = int(plus_minus_match.group(1))
        wrong_penalty = int(plus_minus_match.group(2))
        total_possible = correct + wrong_penalty
        if total_possible > 0:
            net = correct - wrong_penalty
            return round(max(0.0, (net / total_possible) * 100), 2)
        return 0.0

    # Pattern 4: plain numeric string "22"
    plain_match = re.match(r"^(\d+\.?\d*)$", marks_str)
    if plain_match:
        return round(min(float(plain_match.group(1)), 100.0), 2)

    logger.warning("Unrecognised marks format: '%s'; returning None", marks_raw)
    return None


# ---------------------------------------------------------------------------
# _id Normalisation
# ---------------------------------------------------------------------------

def normalize_id(raw_id: Union[dict, str, None]) -> Optional[str]:
    """
    Return a plain string ID regardless of input format.

    Handles:
        - {"$oid": "507f1f77bcf86cd799439011"} -> "507f1f77bcf86cd799439011"
        - "507f1f77bcf86cd799439011"            -> "507f1f77bcf86cd799439011"
        - None                                  -> None
    """
    if raw_id is None:
        return None
    if isinstance(raw_id, dict):
        return raw_id.get("$oid", str(raw_id))
    return str(raw_id).strip()


# ---------------------------------------------------------------------------
# Difficulty Mapping
# ---------------------------------------------------------------------------

DIFFICULTY_MAP: dict = {
    1: "easy",
    2: "easy",
    3: "medium",
    4: "hard",
    5: "hard",
}


def normalize_difficulty(raw_difficulty) -> str:
    """
    Convert numeric or string difficulty to categorical label.

    Rules:
        1-2   -> easy
        3     -> medium
        4+    -> hard
        None  -> medium  (safe default)
    """
    if raw_difficulty is None:
        return "medium"

    if isinstance(raw_difficulty, str):
        lower = raw_difficulty.lower().strip()
        if lower in {"easy", "medium", "hard"}:
            return lower
        try:
            raw_difficulty = float(raw_difficulty)
        except ValueError:
            logger.warning("Cannot parse difficulty '%s'; defaulting to medium", raw_difficulty)
            return "medium"

    val = int(round(float(raw_difficulty)))
    if val < 1:
        return "easy"
    return DIFFICULTY_MAP.get(val, "hard")


# ---------------------------------------------------------------------------
# HTML -> plain-text
# ---------------------------------------------------------------------------

def strip_html(text) -> str:
    """Remove HTML tags and return plain text."""
    if not text:
        return ""
    soup = BeautifulSoup(str(text), "html.parser")
    return soup.get_text(separator=" ").strip()


# ---------------------------------------------------------------------------
# Topic / Subject Mapping
# ---------------------------------------------------------------------------

TOPIC_MAP: dict = {
    # Physics
    "kinematics": "Kinematics",
    "laws of motion": "Laws of Motion",
    "work energy power": "Work Energy Power",
    "work, energy and power": "Work Energy Power",
    "gravitation": "Gravitation",
    "thermodynamics": "Thermodynamics",
    "electrostatics": "Electrostatics",
    "magnetism": "Magnetism",
    "optics": "Optics",
    "modern physics": "Modern Physics",
    "waves": "Waves",
    "rotational motion": "Rotational Motion",
    "fluid mechanics": "Fluid Mechanics",
    # Chemistry
    "atomic structure": "Atomic Structure",
    "chemical bonding": "Chemical Bonding",
    "organic chemistry": "Organic Chemistry",
    "thermodynamics (chem)": "Thermodynamics",
    "electrochemistry": "Electrochemistry",
    "p-block elements": "p-Block Elements",
    "d-block elements": "d-Block Elements",
    "coordination compounds": "Coordination Compounds",
    "chemical equilibrium": "Chemical Equilibrium",
    "solutions": "Solutions",
    # Mathematics
    "quadratic equations": "Quadratic Equations",
    "sequences and series": "Sequences and Series",
    "trigonometry": "Trigonometry",
    "calculus": "Calculus",
    "probability": "Probability",
    "matrices": "Matrices",
    "vectors": "Vectors",
    "complex numbers": "Complex Numbers",
    "permutation combination": "Permutation Combination",
    "binomial theorem": "Binomial Theorem",
    "3d geometry": "3D Geometry",
    "limits": "Limits",
    "differential equations": "Differential Equations",
    # Biology
    "cell biology": "Cell Biology",
    "genetics": "Genetics",
    "ecology": "Ecology",
    "human physiology": "Human Physiology",
    "plant kingdom": "Plant Kingdom",
    "animal kingdom": "Animal Kingdom",
    "reproduction": "Reproduction",
    "evolution": "Evolution",
    "biotechnology": "Biotechnology",
}

# Canonical topic -> parent subject (prevents cross-subject recommendation errors)
TOPIC_SUBJECT_MAP: dict = {
    # Physics
    "Kinematics": "Physics",
    "Laws of Motion": "Physics",
    "Work Energy Power": "Physics",
    "Gravitation": "Physics",
    "Thermodynamics": "Physics",
    "Electrostatics": "Physics",
    "Magnetism": "Physics",
    "Optics": "Physics",
    "Modern Physics": "Physics",
    "Waves": "Physics",
    "Rotational Motion": "Physics",
    "Fluid Mechanics": "Physics",
    # Chemistry
    "Atomic Structure": "Chemistry",
    "Chemical Bonding": "Chemistry",
    "Organic Chemistry": "Chemistry",
    "Electrochemistry": "Chemistry",
    "p-Block Elements": "Chemistry",
    "d-Block Elements": "Chemistry",
    "Coordination Compounds": "Chemistry",
    "Chemical Equilibrium": "Chemistry",
    "Solutions": "Chemistry",
    # Mathematics
    "Quadratic Equations": "Mathematics",
    "Sequences and Series": "Mathematics",
    "Trigonometry": "Mathematics",
    "Calculus": "Mathematics",
    "Probability": "Mathematics",
    "Matrices": "Mathematics",
    "Vectors": "Mathematics",
    "Complex Numbers": "Mathematics",
    "Permutation Combination": "Mathematics",
    "Binomial Theorem": "Mathematics",
    "3D Geometry": "Mathematics",
    "Limits": "Mathematics",
    "Differential Equations": "Mathematics",
    # Biology
    "Cell Biology": "Biology",
    "Genetics": "Biology",
    "Ecology": "Biology",
    "Human Physiology": "Biology",
    "Plant Kingdom": "Biology",
    "Animal Kingdom": "Biology",
    "Reproduction": "Biology",
    "Evolution": "Biology",
    "Biotechnology": "Biology",
}


def normalize_topic(topic) -> str:
    """Map raw topic strings to canonical names."""
    if not topic:
        return "General"
    key = str(topic).lower().strip()
    return TOPIC_MAP.get(key, str(topic).strip().title())


def subject_from_topic(topic: str):
    """
    Return the parent subject for a canonical topic name, or None if unknown.
    Allows callers to fall back to the question's own subject field.
    """
    return TOPIC_SUBJECT_MAP.get(topic)


# ---------------------------------------------------------------------------
# Full Question Normalisation
# ---------------------------------------------------------------------------

def normalize_question(raw_q: dict) -> dict:
    """
    Return a fully cleaned question dict ready for use.

    Subject resolution priority:
      1. Explicit 'subject' field in the raw question (most reliable)
      2. Subject derived from the canonical topic via TOPIC_SUBJECT_MAP
      3. Fallback to 'Unknown'
    """
    clean = dict(raw_q)

    # _id normalisation
    clean["_id"] = normalize_id(raw_q.get("_id"))

    # difficulty
    clean["difficulty"] = normalize_difficulty(raw_q.get("difficulty"))

    # answer
    answer = raw_q.get("answer")
    clean["answer"] = answer if answer is not None else "N/A"

    # question text - strip HTML
    clean["question"] = strip_html(raw_q.get("question", ""))

    # topic
    canonical_topic = normalize_topic(raw_q.get("topic"))
    clean["topic"] = canonical_topic

    # subtopic
    clean["subtopic"] = raw_q.get("subtopic", "General")

    # subject: explicit > topic-derived > Unknown
    explicit_subject = raw_q.get("subject")
    if explicit_subject:
        clean["subject"] = str(explicit_subject).strip().title()
    else:
        derived = subject_from_topic(canonical_topic)
        clean["subject"] = derived or "Unknown"

    return clean


# ---------------------------------------------------------------------------
# Full Session Normalisation
# ---------------------------------------------------------------------------

def normalize_session(session: dict) -> dict:
    """
    Return a cleaned session dict with numeric marks percentage and
    safe defaults for missing fields.
    """
    clean = dict(session)

    clean["marks_pct"] = normalize_marks(session.get("marks"))

    attempted = session.get("attempted", 0) or 0
    skipped = session.get("skipped", 0) or 0
    total = attempted + skipped
    clean["skip_rate"] = round(skipped / total, 3) if total > 0 else 0.0

    time_taken = session.get("time_taken", 0) or 0
    clean["time_per_question"] = round(time_taken / attempted, 1) if attempted > 0 else 0

    clean["completed"] = bool(session.get("completed", False))

    return clean


# ---------------------------------------------------------------------------
# Load and clean full datasets
# ---------------------------------------------------------------------------

def load_students(path: str) -> list:
    """Load student_performance.json and clean every session."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    students = []
    for student in raw:
        s = dict(student)
        s["attempts"] = [normalize_session(a) for a in student.get("attempts", [])]
        students.append(s)
    logger.info("Loaded %d students from %s", len(students), path)
    return students


def load_questions(path: str) -> list:
    """
    Load question_bank.json, normalise every question, and deduplicate.

    Dedup: qid and _id are tracked separately — a question is skipped only
    if its specific ID has appeared before, not if either ID mismatches.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    seen_qids: set = set()
    seen_oids: set = set()
    questions = []
    for q in raw:
        clean = normalize_question(q)
        qid = clean.get("qid")
        oid = clean.get("_id")

        if qid and qid in seen_qids:
            logger.warning("Duplicate qid '%s'; skipping", qid)
            continue
        if oid and oid in seen_oids:
            logger.warning("Duplicate _id '%s'; skipping", oid)
            continue

        if qid:
            seen_qids.add(qid)
        if oid:
            seen_oids.add(oid)
        questions.append(clean)

    logger.info("Loaded %d questions from %s", len(questions), path)
    return questions


def load_dost_config(path: str) -> dict:
    """Load dost_config.json."""
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)
    logger.info(
        "Loaded DOST config from %s (%d types)",
        path,
        len(config.get("dost_types", {})),
    )
    return config

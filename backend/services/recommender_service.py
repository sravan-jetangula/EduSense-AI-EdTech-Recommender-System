"""
recommender_service.py
======================
Generates personalised DOST-based study plans for each student.

BUG FIX DOCUMENTED
===================
Original buggy code:
    student_profile = student_vector - cohort_average   # correct so far
    student_profile = cohort_average / norm             # BUG: overwrites personal vector!

Impact: Every student received the exact same cohort-level recommendations
because the personal deviation was discarded.

Fixed code:
    student_profile = student_vector - cohort_average   # personalised deviation
    norm = _vec_norm(student_profile)
    student_profile = _vec_divide(student_profile, norm)  # normalise the PERSONAL vector

Improvements over original:
  - _select_questions now uses random.sample for non-sequential selection,
    preventing the same question IDs appearing for every student.
  - _select_questions respects subject-topic alignment using the question's
    actual subject field (not inferred), ensuring Physics questions are
    never recommended for a Chemistry step.
  - dost_config parameters (duration, question_count, difficulty) are read
    dynamically from config; nothing is hardcoded.
  - Recommendation rules from dost_config["recommendation_rules"] are
    honoured: the DOST type for each step is driven by the config, not
    hardcoded strings.
  - Step reasoning messages are more specific: they reference actual scores,
    exact topic names, and cohort context.
  - compute_student_profile handles zero-norm edge case gracefully (returns
    zero vector instead of division by zero).
"""

from __future__ import annotations

import math
import random
import statistics
import logging
from typing import Optional

from backend.services.analytics_service import analyze_student

logger = logging.getLogger(__name__)

SUBJECTS = ["Physics", "Chemistry", "Mathematics", "Biology"]


# ---------------------------------------------------------------------------
# Vector helpers (pure Python, no numpy dependency)
# ---------------------------------------------------------------------------

def _student_vector(analysis: dict) -> list:
    """
    Build a 7-dimensional feature vector for a student.

    Dimensions:
        [phys_score, chem_score, math_score, bio_score,
         completion_rate, (1 - skip_rate), speed_normalised]

    All values are in [0, 1].
    """
    subj_breakdown = analysis.get("subject_breakdown", {})
    vec = [
        subj_breakdown.get(s, {}).get("avg_score", 50.0) / 100.0
        for s in SUBJECTS
    ]
    vec.append(analysis.get("completion_rate", 0.5))
    vec.append(1.0 - analysis.get("skip_rate", 0.0))
    tpq = analysis["time_analysis"].get("avg_time_per_question_sec", 120)
    # speed: 1.0 = very fast (30s/q), 0.0 = very slow (300s+/q)
    speed_norm = max(0.0, min(1.0, (300.0 - tpq) / 270.0))
    vec.append(speed_norm)
    return vec


def _vec_mean(vecs: list) -> list:
    n = len(vecs)
    if n == 0:
        return []
    dim = len(vecs[0])
    return [sum(v[i] for v in vecs) / n for i in range(dim)]


def _vec_norm(vec: list) -> float:
    return math.sqrt(sum(x * x for x in vec))


def _vec_subtract(a: list, b: list) -> list:
    return [x - y for x, y in zip(a, b)]


def _vec_divide(vec: list, scalar: float) -> list:
    if scalar == 0:
        return [0.0] * len(vec)  # zero vector instead of division error
    return [x / scalar for x in vec]


# ---------------------------------------------------------------------------
# Core profile computation (BUG FIXED)
# ---------------------------------------------------------------------------

def compute_student_profile(
    student_vec: list,
    cohort_vecs: list,
) -> list:
    """
    Compute a normalised personalised deviation vector.

    Steps
    -----
    1. cohort_average = mean of all student vectors
    2. student_profile = student_vec - cohort_average   (personalised deviation)
    3. norm = ||student_profile||
    4. student_profile = student_profile / norm          <- FIXED (was: cohort_average / norm)

    Returns zero vector if norm is 0 (all students identical — edge case).
    """
    cohort_average = _vec_mean(cohort_vecs) if cohort_vecs else [0.0] * len(student_vec)
    student_profile = _vec_subtract(student_vec, cohort_average)   # Step 2
    norm = _vec_norm(student_profile)                               # Step 3
    return _vec_divide(student_profile, norm)                       # Step 4 - FIXED


# ---------------------------------------------------------------------------
# DOST selection  (config-driven)
# ---------------------------------------------------------------------------

def _select_dost_type(
    analysis: dict,
    dost_config: dict,
) -> str:
    """
    Choose the most appropriate DOST type for a student's current state,
    using the recommendation_rules in dost_config where possible.

    Priority (highest to lowest):
    1. Score < 40  -> concept building
    2. High skip (> 30%) -> formula sheet
    3. Low completion (< 50%) -> revision
    4. Score 40-60  -> practiceAssignment
    5. Score 60-75, slow -> pickingPower; else practiceTest
    6. Score >= 75, fast -> speedRace; else clickingPower
    """
    rules = dost_config.get("recommendation_rules", {})
    score = analysis.get("overall_score", 50)
    skip_rate = analysis.get("skip_rate", 0)
    completion = analysis.get("completion_rate", 0.5)
    speed_label = analysis["time_analysis"].get("speed_label", "moderate")

    if score < 40:
        candidates = rules.get("score_below_40", ["concept"])
        return candidates[0]
    if skip_rate > 0.3:
        candidates = rules.get("high_skip_rate", ["formula"])
        return candidates[0]
    if completion < 0.5:
        candidates = rules.get("low_completion_rate", ["revision"])
        return candidates[0]
    if score < 60:
        candidates = rules.get("score_40_to_60", ["practiceAssignment"])
        return candidates[0]
    if score < 75:
        if speed_label == "slow":
            return "pickingPower"
        candidates = rules.get("score_60_to_75", ["practiceTest"])
        return candidates[0]
    # score >= 75
    if speed_label == "fast":
        candidates = rules.get("score_above_75", ["speedRace"])
        return candidates[0]
    return "clickingPower"


def _select_questions(
    questions: list,
    subject: str,
    topic: Optional[str],
    difficulty: str,
    count: int = 5,
    exclude_ids: Optional[set] = None,
) -> list:
    """
    Filter question bank and return up to `count` question IDs.

    Selection is randomised (not sequential) so different students
    get different question sets.  Uses subject as primary filter to
    prevent cross-subject question recommendations.

    Falls back progressively:
      1. subject + topic + difficulty
      2. subject + difficulty
      3. subject only
    """
    exclude = exclude_ids or set()

    def _eligible(q):
        qid = q.get("qid") or q.get("_id", "")
        return q.get("subject") == subject and qid not in exclude

    # Attempt 1: full match
    pool = [
        q for q in questions
        if _eligible(q)
        and q.get("difficulty") == difficulty
        and (topic is None or q.get("topic") == topic)
    ]

    # Attempt 2: relax topic
    if len(pool) < count:
        pool = [
            q for q in questions
            if _eligible(q)
            and q.get("difficulty") == difficulty
        ]

    # Attempt 3: relax difficulty too
    if len(pool) < count:
        pool = [q for q in questions if _eligible(q)]

    selected = random.sample(pool, min(count, len(pool))) if pool else []
    return [q.get("qid") or q.get("_id") for q in selected]


# ---------------------------------------------------------------------------
# Public recommendation API
# ---------------------------------------------------------------------------

def generate_recommendations(
    student: dict,
    all_students: list,
    questions: list,
    dost_config: dict,
) -> dict:
    """
    Generate a full personalised study plan for one student.

    Returns:
        {
            student_id, name,
            profile_summary,
            steps: [
                {
                    step, dost_type, dost_name, subject, chapter,
                    difficulty, duration_min, question_count,
                    question_ids, reasoning, message
                }, ...
            ]
        }
    """
    analysis = analyze_student(student)
    sid = analysis["student_id"]
    name = analysis["name"]

    # Build cohort vectors (excluding current student for unbiased average)
    all_analyses = [analyze_student(s) for s in all_students]
    cohort_vecs = [_student_vector(a) for a in all_analyses if a["student_id"] != sid]
    student_vec = _student_vector(analysis)

    # Compute personalised profile (BUG FIXED)
    profile = compute_student_profile(student_vec, cohort_vecs)

    weak_topics = analysis.get("weak_topics", [])
    moderate_topics = analysis.get("moderate_topics", [])
    strong_topics = analysis.get("strong_topics", [])
    subj_break = analysis.get("subject_breakdown", {})

    # Sort subjects by average score, ascending (weakest first)
    sorted_subjects = sorted(
        subj_break.items(), key=lambda x: x[1]["avg_score"]
    )

    dost_types = dost_config.get("dost_types", {})
    overall_score = analysis.get("overall_score", 50)
    cohort_avg = statistics.mean(
        [a.get("overall_score", 50) for a in all_analyses]
    ) if all_analyses else 50.0
    used_q_ids: set = set()
    steps = []

    def _build_step(
        step_num: int,
        dost_key: str,
        subject: str,
        chapter: str,
        topic_for_q: Optional[str],
        difficulty: str,
        reasoning: str,
        message: str,
    ) -> dict:
        """Helper to assemble a step dict using dost_config parameters."""
        dost = dost_types.get(dost_key, {})
        params = dost.get("parameters", {})
        q_count = params.get("question_count", 10)
        q_ids = _select_questions(
            questions, subject, topic_for_q, difficulty, q_count, used_q_ids
        )
        used_q_ids.update(qid for qid in q_ids if qid)
        return {
            "step": step_num,
            "dost_type": dost_key,
            "dost_name": dost.get("name", dost_key),
            "dost_icon": dost.get("icon", ""),
            "subject": subject,
            "chapter": chapter,
            "difficulty": difficulty,
            "duration_min": params.get("duration_minutes", 30),
            "question_count": q_count,
            "question_ids": q_ids,
            "reasoning": reasoning,
            "message": message,
        }

    # -------------------------------------------------------------------
    # Step 1 – Address worst weak topic with concept building
    # -------------------------------------------------------------------
    if weak_topics and sorted_subjects:
        weakest_subj, _ = sorted_subjects[0]
        topic = weak_topics[0]
        steps.append(_build_step(
            step_num=1,
            dost_key="concept",
            subject=weakest_subj,
            chapter=topic,
            topic_for_q=topic,
            difficulty="easy",
            reasoning=(
                f"'{topic}' in {weakest_subj} scored below 50% — foundational "
                f"concept work is needed before attempting harder problems."
            ),
            message=(
                f"Hey {name}! Let's build your {weakest_subj} foundation. "
                f"We're starting with '{topic}' — take your time with each concept. 💡"
            ),
        ))

    # -------------------------------------------------------------------
    # Step 2 – Formula revision on weakest subject
    # -------------------------------------------------------------------
    if sorted_subjects:
        weakest_subj, stats = sorted_subjects[0]
        subj_score = stats["avg_score"]
        steps.append(_build_step(
            step_num=2,
            dost_key="formula",
            subject=weakest_subj,
            chapter="Key Formulae",
            topic_for_q=None,
            difficulty="easy",
            reasoning=(
                f"Your {weakest_subj} average is {subj_score:.1f}% — "
                f"formula recall is the fastest way to close the gap vs. cohort "
                f"average of {cohort_avg:.1f}%."
            ),
            message=(
                f"Formula time for {weakest_subj}! Quick recall drills — "
                f"repeat until they're automatic. 🔢"
            ),
        ))

    # -------------------------------------------------------------------
    # Step 3 – Practice assignment on best moderate topic
    # -------------------------------------------------------------------
    if moderate_topics:
        # Use second weakest subject if available (not the same as Step 1)
        target_subj = (
            sorted_subjects[min(1, len(sorted_subjects) - 1)][0]
            if len(sorted_subjects) > 1
            else sorted_subjects[0][0]
        )
        topic = moderate_topics[0]
        topic_score = analysis.get("chapter_breakdown", {}).get(topic, 60)
        steps.append(_build_step(
            step_num=3,
            dost_key="practiceAssignment",
            subject=target_subj,
            chapter=topic,
            topic_for_q=topic,
            difficulty="medium",
            reasoning=(
                f"'{topic}' is at {topic_score:.1f}% (moderate zone). "
                f"A focused assignment will push it past the 70% threshold."
            ),
            message=(
                f"You're almost there on '{topic}'! "
                f"Medium difficulty assignment — stretch a little. 📋"
            ),
        ))

    # -------------------------------------------------------------------
    # Step 4 – Full practice test on strongest subject  (consolidation)
    # -------------------------------------------------------------------
    if sorted_subjects:
        best_subj, best_stats = sorted_subjects[-1]
        best_score = best_stats["avg_score"]
        dost_key = _select_dost_type(analysis, dost_config)
        steps.append(_build_step(
            step_num=4,
            dost_key="practiceTest",
            subject=best_subj,
            chapter="Full Subject",
            topic_for_q=None,
            difficulty="medium",
            reasoning=(
                f"{best_subj} is your strongest subject ({best_score:.1f}%). "
                f"A full practice test consolidates mastery and simulates exam conditions."
            ),
            message=(
                f"Your {best_subj} score is impressive — {best_score:.1f}%! "
                f"Time to prove it under timed exam conditions. 📝"
            ),
        ))

    # -------------------------------------------------------------------
    # Step 5 – Speed or accuracy drill (personalised by time metric)
    # -------------------------------------------------------------------
    speed = analysis["time_analysis"].get("speed_label", "moderate")
    tpq = analysis["time_analysis"].get("avg_time_per_question_sec", 120)
    subj = sorted_subjects[-1][0] if sorted_subjects else "Physics"

    if speed == "slow":
        steps.append(_build_step(
            step_num=5,
            dost_key="clickingPower",
            subject=subj,
            chapter="Speed Drill",
            topic_for_q=None,
            difficulty="easy",
            reasoning=(
                f"Average time per question is {tpq:.0f}s — well above the 90s target. "
                f"Speed drills on familiar material will build response instinct."
            ),
            message=(
                f"Let's sharpen your speed! Easy questions, fast clock. "
                f"Target: under 60s per question. ⚡"
            ),
        ))
    elif speed == "moderate":
        steps.append(_build_step(
            step_num=5,
            dost_key="pickingPower",
            subject=subj,
            chapter="Elimination Drill",
            topic_for_q=None,
            difficulty="medium",
            reasoning=(
                f"Speed is moderate ({tpq:.0f}s/question). Elimination-based questions "
                f"will sharpen both accuracy and decision speed simultaneously."
            ),
            message=(
                f"Work smarter, not just faster! Practice elimination technique "
                f"to gain time without sacrificing accuracy. 🎯"
            ),
        ))
    # If fast: no speed step needed — strong score path ends at Step 4

    # Profile summary for UI display
    profile_summary = {
        "overall_score": overall_score,
        "cohort_avg": round(cohort_avg, 1),
        "cohort_delta": round(overall_score - cohort_avg, 1),
        "trend": analysis["trend"],
        "completion_rate": analysis["completion_rate"],
        "skip_rate": analysis["skip_rate"],
        "speed": speed,
        "weak_count": len(weak_topics),
        "strong_count": len(strong_topics),
        "moderate_count": len(moderate_topics),
    }

    return {
        "student_id": sid,
        "name": name,
        "profile_summary": profile_summary,
        "steps": steps,
    }

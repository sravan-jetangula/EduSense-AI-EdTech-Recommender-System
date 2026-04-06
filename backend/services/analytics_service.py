"""
analytics_service.py
====================
Computes student performance metrics: trends, topic strengths/weaknesses,
time analysis, chapter breakdown, and a leaderboard scoring formula.
"""

from __future__ import annotations

import statistics
from typing import Optional
from collections import defaultdict


# ---------------------------------------------------------------------------
# Individual Student Analysis
# ---------------------------------------------------------------------------

def analyze_student(student: dict) -> dict:
    """
    Return a comprehensive analysis dict for one student.

    Keys returned:
        student_id, name,
        overall_score, trend, trend_slope,
        weak_topics, strong_topics,
        subject_breakdown, chapter_breakdown,
        time_analysis,
        completion_rate, skip_rate,
        total_sessions
    """
    sid = student["student_id"]
    name = student.get("name", sid)
    attempts = student.get("attempts", [])

    if not attempts:
        return _empty_analysis(sid, name)

    # ------------------------------------------------------------------
    # 1. Score series (chronological)
    # ------------------------------------------------------------------
    scores = [a["marks_pct"] for a in attempts if a.get("marks_pct") is not None]
    overall_score = round(statistics.mean(scores), 2) if scores else 0.0
    trend, trend_slope = _compute_trend(scores)

    # ------------------------------------------------------------------
    # 2. Subject-wise performance
    # ------------------------------------------------------------------
    subject_data: dict[str, list[float]] = defaultdict(list)
    for a in attempts:
        subj = a.get("subject", "Unknown")
        pct = a.get("marks_pct")
        if pct is not None:
            subject_data[subj].append(pct)

    subject_breakdown = {
        subj: {
            "avg_score": round(statistics.mean(vals), 2),
            "sessions": len(vals),
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
        }
        for subj, vals in subject_data.items()
    }

    # ------------------------------------------------------------------
    # 3. Chapter-wise breakdown
    # ------------------------------------------------------------------
    chapter_data: dict[str, list[float]] = defaultdict(list)
    for a in attempts:
        pct = a.get("marks_pct")
        if pct is None:
            continue
        chapters = a.get("chapters", [])
        for ch in chapters:
            chapter_data[ch].append(pct)

    chapter_breakdown = {
        ch: round(statistics.mean(v), 2) for ch, v in chapter_data.items()
    }

    # ------------------------------------------------------------------
    # 4. Weak / strong topics (threshold: 50 / 70)
    # ------------------------------------------------------------------
    weak_topics = [ch for ch, avg in chapter_breakdown.items() if avg < 50]
    strong_topics = [ch for ch, avg in chapter_breakdown.items() if avg >= 70]
    moderate_topics = [
        ch for ch, avg in chapter_breakdown.items() if 50 <= avg < 70
    ]

    # ------------------------------------------------------------------
    # 5. Time analysis
    # ------------------------------------------------------------------
    time_per_q_vals = [
        a["time_per_question"]
        for a in attempts
        if a.get("time_per_question", 0) > 0
    ]
    avg_time_per_q = round(statistics.mean(time_per_q_vals), 1) if time_per_q_vals else 0
    speed_label = _speed_label(avg_time_per_q)

    time_analysis = {
        "avg_time_per_question_sec": avg_time_per_q,
        "speed_label": speed_label,
        "total_study_time_hrs": round(
            sum(a.get("time_taken", 0) for a in attempts) / 3600, 2
        ),
    }

    # ------------------------------------------------------------------
    # 6. Completion & skip metrics
    # ------------------------------------------------------------------
    completion_rate = round(
        sum(1 for a in attempts if a.get("completed")) / len(attempts), 3
    )
    skip_rate = round(
        statistics.mean([a.get("skip_rate", 0) for a in attempts]), 3
    )

    return {
        "student_id": sid,
        "name": name,
        "overall_score": overall_score,
        "trend": trend,
        "trend_slope": trend_slope,
        "scores_series": scores,
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
        "moderate_topics": moderate_topics,
        "subject_breakdown": subject_breakdown,
        "chapter_breakdown": chapter_breakdown,
        "time_analysis": time_analysis,
        "completion_rate": completion_rate,
        "skip_rate": skip_rate,
        "total_sessions": len(attempts),
    }


def _empty_analysis(sid: str, name: str) -> dict:
    return {
        "student_id": sid,
        "name": name,
        "overall_score": 0.0,
        "trend": "no_data",
        "trend_slope": 0.0,
        "scores_series": [],
        "weak_topics": [],
        "strong_topics": [],
        "moderate_topics": [],
        "subject_breakdown": {},
        "chapter_breakdown": {},
        "time_analysis": {"avg_time_per_question_sec": 0, "speed_label": "unknown", "total_study_time_hrs": 0},
        "completion_rate": 0.0,
        "skip_rate": 0.0,
        "total_sessions": 0,
    }


def _compute_trend(scores: list[float]) -> tuple[str, float]:
    """
    Linear trend via least-squares slope.
    Returns (label, slope).
    """
    n = len(scores)
    if n < 2:
        return ("stable", 0.0)

    x_mean = (n - 1) / 2
    y_mean = statistics.mean(scores)
    numerator = sum((i - x_mean) * (scores[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    slope = numerator / denominator if denominator != 0 else 0.0

    if slope > 1.5:
        label = "improving"
    elif slope < -1.5:
        label = "declining"
    else:
        label = "stable"
    return (label, round(slope, 3))


def _speed_label(sec_per_q: float) -> str:
    if sec_per_q == 0:
        return "unknown"
    if sec_per_q < 60:
        return "fast"
    if sec_per_q < 150:
        return "moderate"
    return "slow"


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

def compute_leaderboard(students: list[dict]) -> list[dict]:
    """
    Rank all students by composite score.

    Formula (weights):
        score      → 50%
        consistency → 20%   (1 - coefficient_of_variation)
        completion  → 20%
        speed       → 10%   (inverse of avg_time_per_question)
    """
    ranked = []
    for student in students:
        analysis = analyze_student(student)
        scores = analysis["scores_series"]
        if not scores:
            composite = 0.0
        else:
            avg = analysis["overall_score"]
            # consistency: low CV = consistent
            std = statistics.stdev(scores) if len(scores) > 1 else 0
            cv = std / avg if avg > 0 else 1.0
            consistency = max(0.0, 1 - cv)

            completion = analysis["completion_rate"]

            tpq = analysis["time_analysis"]["avg_time_per_question_sec"]
            # speed score: 100 at 30s, 0 at 300s+
            speed_score = max(0.0, min(1.0, (300 - tpq) / 270)) if tpq > 0 else 0.5

            composite = (
                0.50 * (avg / 100)
                + 0.20 * consistency
                + 0.20 * completion
                + 0.10 * speed_score
            ) * 100

        ranked.append(
            {
                "student_id": analysis["student_id"],
                "name": analysis["name"],
                "composite_score": round(composite, 2),
                "avg_score": analysis["overall_score"],
                "completion_rate": analysis["completion_rate"],
                "trend": analysis["trend"],
                "sessions": analysis["total_sessions"],
            }
        )

    ranked.sort(key=lambda x: x["composite_score"], reverse=True)
    for i, entry in enumerate(ranked, start=1):
        entry["rank"] = i
    return ranked

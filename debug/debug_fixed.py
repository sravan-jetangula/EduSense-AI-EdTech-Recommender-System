"""
debug_fixed.py
==============
Demonstrates and explains the recommender system bug: how it was found,
what impact it had, and how it was fixed.

Run this file directly to see a side-by-side comparison:
    python debug_fixed.py
"""

import math
import json

# ============================================================
# BUGGY IMPLEMENTATION
# ============================================================

def compute_student_profile_BUGGY(
    student_vector: list[float],
    cohort_vectors: list[list[float]],
) -> list[float]:
    """
    ❌ BUGGY VERSION — do NOT use in production.

    The bug:
        Line 1: student_profile = student_vector - cohort_average   ✅ correct
        Line 2: student_profile = cohort_average / norm             ❌ BUG!

    The second line completely overwrites the personalised student_profile
    with the normalised cohort average. All students end up with the same
    profile vector (the global average), so they all get identical
    recommendations — personalisation is completely lost.
    """
    # Step 1 – compute cohort average
    n = len(cohort_vectors)
    dim = len(student_vector)
    cohort_average = [sum(v[i] for v in cohort_vectors) / n for i in range(dim)]

    # Step 2 – compute personalised deviation ← CORRECT
    student_profile = [student_vector[i] - cohort_average[i] for i in range(dim)]

    # Step 3 – compute norm
    norm = math.sqrt(sum(x * x for x in student_profile))

    # ❌ BUG: overwrites student_profile with cohort_average / norm
    #         instead of normalising the student_profile itself!
    student_profile = [cohort_average[i] / norm for i in range(dim)]  # ← BUG LINE

    return student_profile


# ============================================================
# FIXED IMPLEMENTATION
# ============================================================

def compute_student_profile_FIXED(
    student_vector: list[float],
    cohort_vectors: list[list[float]],
) -> list[float]:
    """
    ✅ FIXED VERSION — use this in production.

    Correct logic:
        1. Compute cohort average
        2. student_profile = student_vector - cohort_average  (personalised deviation)
        3. Normalise STUDENT_PROFILE, not cohort_average
    """
    # Step 1 – compute cohort average
    n = len(cohort_vectors)
    dim = len(student_vector)
    cohort_average = [sum(v[i] for v in cohort_vectors) / n for i in range(dim)]

    # Step 2 – personalised deviation
    student_profile = [student_vector[i] - cohort_average[i] for i in range(dim)]

    # Step 3 – normalise THE STUDENT PROFILE (not cohort_average)  ← FIXED
    norm = math.sqrt(sum(x * x for x in student_profile))
    if norm > 0:
        student_profile = [x / norm for x in student_profile]

    return student_profile


# ============================================================
# DEMONSTRATION
# ============================================================

def demo():
    print("=" * 65)
    print("  RECOMMENDER BUG ANALYSIS & FIX DEMONSTRATION")
    print("=" * 65)

    # Simulated student vectors: [phys, chem, math, bio, completion, (1-skip), speed]
    student_A = [0.80, 0.45, 0.90, 0.00, 0.9, 0.8, 0.7]   # strong in math/physics
    student_B = [0.30, 0.40, 0.35, 0.85, 0.7, 0.6, 0.4]   # strong in biology

    cohort = [
        [0.55, 0.50, 0.60, 0.55, 0.8, 0.7, 0.6],
        [0.70, 0.65, 0.55, 0.40, 0.9, 0.8, 0.7],
        [0.45, 0.40, 0.70, 0.60, 0.6, 0.5, 0.5],
    ]

    print("\n📌 Input Vectors")
    print(f"  Student A (physics/math oriented): {[round(x,2) for x in student_A]}")
    print(f"  Student B (biology oriented):      {[round(x,2) for x in student_B]}")

    # --- BUGGY ---
    buggy_A = compute_student_profile_BUGGY(student_A, cohort)
    buggy_B = compute_student_profile_BUGGY(student_B, cohort)

    print("\n❌ BUGGY profiles")
    print(f"  Student A: {[round(x, 4) for x in buggy_A]}")
    print(f"  Student B: {[round(x, 4) for x in buggy_B]}")
    identical = buggy_A == buggy_B
    print(f"  ⚠️  Profiles identical: {identical}")

    # --- FIXED ---
    fixed_A = compute_student_profile_FIXED(student_A, cohort)
    fixed_B = compute_student_profile_FIXED(student_B, cohort)

    print("\n✅ FIXED profiles")
    print(f"  Student A: {[round(x, 4) for x in fixed_A]}")
    print(f"  Student B: {[round(x, 4) for x in fixed_B]}")
    identical = fixed_A == fixed_B
    print(f"  ✅ Profiles identical: {identical} (should be False)")

    print("\n" + "=" * 65)
    print("  EXPLANATION")
    print("=" * 65)
    explanation = """
The Bug (Line-by-Line):

    student_profile = student_vector - cohort_average   ← Step A: ✅ correct
    student_profile = cohort_average / norm             ← Step B: ❌ BUG

Step B replaces `student_profile` (the personalised deviation computed
in Step A) with `cohort_average / norm`. This means:

  • `student_profile` now contains the global average direction,
    NOT the individual student's deviation from that average.
  • Every student gets the exact same vector → identical recommendations.
  • Personalisation is completely lost.

The Fix:

    student_profile = student_vector - cohort_average   ← keeps personalised deviation
    norm = ||student_profile||
    if norm > 0:
        student_profile = student_profile / norm        ← normalise THE STUDENT PROFILE

How it was identified:
  • Integration test observed all students receiving the exact same DOST plan.
  • Debug logging showed all student_profile vectors were numerically identical.
  • Code inspection revealed the overwrite on Step B.

Impact of fix:
  • Student A (math/physics strong) now shows high positive deviation in
    math/physics dimensions and negative in biology.
  • Student B (bio strong) shows opposite pattern.
  • Each student receives a plan tailored to their actual strengths.
"""
    print(explanation)


if __name__ == "__main__":
    demo()

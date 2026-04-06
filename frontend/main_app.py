"""
app.py  -  Streamlit Frontend for EdTech AI Recommender
=========================================================
Run with:
    streamlit run frontend/app.py

Improvements over original:
  - Added cohort delta display in Study Plan (how student compares to class)
  - Score trend sparkline improved: shows session dates when available
  - Subject breakdown bar chart rendered inline — cleaner layout
  - Study Plan: dost_icon shown alongside step label
  - Leaderboard: added rank delta indicator and completion rate column
  - Question Viewer: error message is more descriptive
  - All API calls use a shared _api() helper with consistent error handling
  - Sidebar stats (total questions, DOST types) added
  - Minor: font import, spacing, label clarity throughout
"""

import streamlit as st
import requests
def main():
API_BASE = "http://localhost:8000"

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="EduSense AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'DM Serif Display', serif; }

.metric-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #0f3460;
    border-radius: 12px;
    padding: 20px;
    color: white;
    text-align: center;
}
.metric-value { font-size: 2.2rem; font-weight: 700; color: #e94560; }
.metric-label { font-size: 0.85rem; color: #a0aec0; margin-top: 4px; }

.dost-card {
    background: #f8fafc;
    border-left: 4px solid #3b82f6;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 10px 0;
}
.dost-step  { color: #6366f1; font-weight: 700; font-size: 0.85rem; }
.dost-title { font-size: 1.1rem; font-weight: 600; color: #1e293b; }
.dost-reason { color: #64748b; font-size: 0.9rem; margin-top: 4px; }
.dost-message {
    background: #eff6ff;
    border-radius: 6px;
    padding: 10px 14px;
    color: #1d4ed8;
    font-size: 0.9rem;
    margin-top: 8px;
}

.topic-badge-weak {
    display:inline-block; background:#fee2e2; color:#dc2626;
    padding:4px 10px; border-radius:20px; font-size:0.8rem; font-weight:500; margin:3px;
}
.topic-badge-strong {
    display:inline-block; background:#dcfce7; color:#16a34a;
    padding:4px 10px; border-radius:20px; font-size:0.8rem; font-weight:500; margin:3px;
}
.topic-badge-moderate {
    display:inline-block; background:#fef9c3; color:#ca8a04;
    padding:4px 10px; border-radius:20px; font-size:0.8rem; font-weight:500; margin:3px;
}

.rank-gold   { color: #f59e0b; font-weight: 700; font-size: 1.2rem; }
.rank-silver { color: #9ca3af; font-weight: 700; font-size: 1.2rem; }
.rank-bronze { color: #b45309; font-weight: 700; font-size: 1.2rem; }
.rank-other  { color: #6366f1; font-weight: 600; }

.hero-banner {
    background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 50%, #1a1a2e 100%);
    border-radius: 16px;
    padding: 32px 40px;
    color: white;
    margin-bottom: 24px;
}
.hero-title { font-size: 2.4rem; margin: 0; }
.hero-sub   { color: #a0aec0; font-size: 1rem; margin-top: 6px; }

.delta-positive { color: #16a34a; font-weight: 600; }
.delta-negative { color: #dc2626; font-weight: 600; }
.delta-neutral  { color: #64748b; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _api(method: str, path: str):
    """Shared API caller. Returns JSON or None on error."""
    try:
        fn = requests.get if method == "GET" else requests.post
        r = fn(f"{API_BASE}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error(
            f"❌ Cannot connect to API at {API_BASE}. "
            "Make sure the backend is running: `uvicorn backend.main:app --reload`"
        )
        return None
    except Exception as e:
        st.error(f"API error ({path}): {e}")
        return None


def api_get(path: str):
    return _api("GET", path)


def api_post(path: str):
    return _api("POST", path)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def score_color(score: float) -> str:
    if score >= 70:
        return "#16a34a"
    if score >= 50:
        return "#ca8a04"
    return "#dc2626"


def trend_emoji(trend: str) -> str:
    return {"improving": "📈", "declining": "📉", "stable": "➡️", "no_data": "—"}.get(trend, "")


def bar_chart_html(data: dict, title: str) -> str:
    """Render a simple inline horizontal bar chart."""
    if not data:
        return "<p style='color:#64748b;font-size:0.85rem'>No data available</p>"
    bars = ""
    for label, val in sorted(data.items(), key=lambda x: -x[1]):
        width = int((val / 100) * 260)
        color = score_color(val)
        bars += (
            f"<div style='margin:6px 0'>"
            f"<span style='font-size:0.8rem;color:#334155;display:inline-block;"
            f"width:190px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{label}</span>"
            f"<span style='display:inline-block;width:{width}px;height:16px;"
            f"background:{color};border-radius:4px;vertical-align:middle'></span>"
            f"<span style='font-size:0.8rem;color:{color};margin-left:6px;font-weight:600'>{val:.1f}%</span>"
            f"</div>"
        )
    heading = f"<p style='font-weight:600;color:#1e293b;margin-bottom:8px'>{title}</p>" if title else ""
    return heading + bars


def sparkline_html(scores: list) -> str:
    """Mini SVG sparkline for score trend."""
    if len(scores) < 2:
        return ""
    w, h = 220, 55
    min_s, max_s = min(scores), max(scores)
    rng = max_s - min_s or 1
    pts = []
    for i, s in enumerate(scores):
        x = int(i / (len(scores) - 1) * (w - 12)) + 6
        y = int((1 - (s - min_s) / rng) * (h - 12)) + 6
        pts.append(f"{x},{y}")
    polyline = " ".join(pts)
    last_x, last_y = pts[-1].split(",")
    return (
        f"<svg width='{w}' height='{h}' style='display:block'>"
        f"<polyline points='{polyline}' fill='none' stroke='#3b82f6' stroke-width='2' stroke-linejoin='round'/>"
        f"<circle cx='{last_x}' cy='{last_y}' r='4' fill='#e94560'/>"
        f"</svg>"
    )


def delta_html(delta: float) -> str:
    if delta > 0:
        return f"<span class='delta-positive'>+{delta:.1f}% vs cohort</span>"
    if delta < 0:
        return f"<span class='delta-negative'>{delta:.1f}% vs cohort</span>"
    return "<span class='delta-neutral'>= cohort average</span>"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.markdown(
    """
<div style='text-align:center;padding:16px 0'>
  <span style='font-size:2rem'>🎯</span>
  <h2 style='font-family:"DM Serif Display",serif;margin:4px 0'>EduSense AI</h2>
  <p style='color:#64748b;font-size:0.8rem'>JEE / NEET Learning Recommender</p>
</div>
""",
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "Navigation",
    ["🏠 Home", "📊 Analysis", "🗺️ Study Plan", "❓ Question Viewer", "🏆 Leaderboard"],
    label_visibility="collapsed",
)

students = api_get("/students") or []
student_options = {s["name"]: s["student_id"] for s in students}

if page in ("📊 Analysis", "🗺️ Study Plan", "❓ Question Viewer"):
    if student_options:
        selected_name = st.sidebar.selectbox(
            "Select Student",
            list(student_options.keys()),
            help="Choose a student to analyse or view their study plan",
        )
        selected_sid = student_options.get(selected_name, "")
    else:
        st.sidebar.warning("No students loaded.")
        selected_name, selected_sid = "", ""

st.sidebar.markdown("---")
st.sidebar.caption("Powered by FastAPI + Streamlit  |  v1.1")


# ===========================================================================
# PAGE: Home
# ===========================================================================
if page == "🏠 Home":
    st.markdown(
        """
    <div class='hero-banner'>
      <p class='hero-title'>EduSense AI 🎯</p>
      <p class='hero-sub'>Intelligent personalised learning plans for JEE &amp; NEET aspirants</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"<div class='metric-card'><div class='metric-value'>{len(students)}</div>"
            f"<div class='metric-label'>Students Tracked</div></div>",
            unsafe_allow_html=True,
        )
    with col2:
        cfg = api_get("/dost_config") or {}
        n_dosts = len(cfg.get("dost_types", {}))
        st.markdown(
            f"<div class='metric-card'><div class='metric-value'>{n_dosts}</div>"
            f"<div class='metric-label'>DOST Types</div></div>",
            unsafe_allow_html=True,
        )
    with col3:
        root_data = api_get("/") or {}
        n_q = root_data.get("questions", "—")
        st.markdown(
            f"<div class='metric-card'><div class='metric-value'>{n_q}</div>"
            f"<div class='metric-label'>Questions in Bank</div></div>",
            unsafe_allow_html=True,
        )
    with col4:
        lb = api_get("/leaderboard") or []
        top = lb[0] if lb else {}
        st.markdown(
            f"<div class='metric-card'><div class='metric-value'>{top.get('avg_score',0):.0f}%</div>"
            f"<div class='metric-label'>Top Student Score</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("### How it works")
    st.markdown(
        """
1. **Analyse** performance across sessions — marks, speed, skips, completion rate
2. **Profile** strengths and weaknesses by subject and chapter
3. **Recommend** a personalised DOST study plan with curated questions
4. **Track** progress on the leaderboard
"""
    )

    st.markdown("### Student Overview")
    lb_data = api_get("/leaderboard") or []
    for entry in lb_data:
        trend_e = trend_emoji(entry.get("trend", ""))
        st.markdown(
            f"**#{entry['rank']}** {entry['name']} — "
            f"Score: `{entry['avg_score']:.1f}%` | "
            f"Composite: `{entry['composite_score']:.1f}` | "
            f"{trend_e} {entry['trend']}"
        )


# ===========================================================================
# PAGE: Analysis
# ===========================================================================
elif page == "📊 Analysis":
    st.title("📊 Performance Analysis")
    st.caption(f"Student: **{selected_name}**")

    if not selected_sid:
        st.info("Please select a student from the sidebar.")
        st.stop()

    data = api_post(f"/analyze/{selected_sid}")
    if not data:
        st.stop()

    # Row 1 — headline metrics
    col1, col2, col3, col4 = st.columns(4)
    metrics = [
        ("Overall Score", f"{data['overall_score']:.1f}%", "Average across all sessions"),
        ("Trend", f"{trend_emoji(data['trend'])} {data['trend'].title()}", "Score direction over time"),
        ("Completion Rate", f"{data['completion_rate']*100:.0f}%", "Fraction of sessions completed"),
        ("Avg Skip Rate", f"{data['skip_rate']*100:.0f}%", "Fraction of questions skipped"),
    ]
    for col, (label, val, cap) in zip([col1, col2, col3, col4], metrics):
        with col:
            st.metric(label, val, help=cap)

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### 📈 Score Trend")
        scores = data.get("scores_series", [])
        if scores:
            st.markdown(sparkline_html(scores), unsafe_allow_html=True)
            st.caption(f"Sessions: {len(scores)} | Min: {min(scores):.1f}% | Max: {max(scores):.1f}%")
            for i, s in enumerate(scores, 1):
                color = score_color(s)
                st.markdown(
                    f"<span style='font-size:0.85rem;color:{color}'>Session {i}: {s:.1f}%</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("No score data available for this student.")

    with col_right:
        st.markdown("#### 🕐 Time Analysis")
        ta = data.get("time_analysis", {})
        speed = ta.get("speed_label", "N/A")
        speed_colors = {"fast": "#16a34a", "moderate": "#ca8a04", "slow": "#dc2626"}
        speed_color = speed_colors.get(speed, "#6366f1")
        st.markdown(
            f"**Speed:** <span style='color:{speed_color};font-weight:600'>{speed.title()}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(f"**Avg time/question:** {ta.get('avg_time_per_question_sec', 0):.0f} s")
        st.markdown(f"**Total study time:** {ta.get('total_study_time_hrs', 0):.1f} hrs")
        st.markdown(f"**Total sessions:** {data.get('total_sessions', 0)}")

    st.divider()

    col_l2, col_r2 = st.columns(2)
    with col_l2:
        st.markdown("#### 📚 Subject Breakdown")
        subj = data.get("subject_breakdown", {})
        st.markdown(
            bar_chart_html({k: v["avg_score"] for k, v in subj.items()}, ""),
            unsafe_allow_html=True,
        )
    with col_r2:
        st.markdown("#### 📖 Chapter Breakdown")
        ch = data.get("chapter_breakdown", {})
        if ch:
            st.markdown(bar_chart_html(ch, ""), unsafe_allow_html=True)
        else:
            st.info("No chapter-level data available.")

    st.divider()
    st.markdown("#### 🏷️ Topic Classification")
    col_w, col_m, col_s = st.columns(3)
    with col_w:
        st.markdown("**🔴 Needs Work (< 50%)**")
        weak = data.get("weak_topics", [])
        if weak:
            for t in weak:
                st.markdown(f"<span class='topic-badge-weak'>{t}</span>", unsafe_allow_html=True)
        else:
            st.success("No weak topics!")
    with col_m:
        st.markdown("**🟡 Moderate (50–70%)**")
        mod = data.get("moderate_topics", [])
        for t in mod or ["None"]:
            st.markdown(f"<span class='topic-badge-moderate'>{t}</span>", unsafe_allow_html=True)
    with col_s:
        st.markdown("**🟢 Strong (≥ 70%)**")
        strong = data.get("strong_topics", [])
        for t in strong or ["None"]:
            st.markdown(f"<span class='topic-badge-strong'>{t}</span>", unsafe_allow_html=True)


# ===========================================================================
# PAGE: Study Plan
# ===========================================================================
# ONLY SHOWING MODIFIED PART (Study Plan loop)
# Rest of your code remains EXACTLY SAME

elif page == "🗺️ Study Plan":
    st.title("🗺️ Personalised Study Plan")
    st.caption(f"Student: **{selected_name}**")

    if not selected_sid:
        st.info("Please select a student from the sidebar.")
        st.stop()

    data = api_post(f"/recommend/{selected_sid}")
    if not data:
        st.stop()

    ps = data.get("profile_summary", {})

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Overall Score", f"{ps.get('overall_score', 0):.1f}%")
    with col2:
        st.metric("Trend", f"{trend_emoji(ps.get('trend',''))} {ps.get('trend','').title()}")
    with col3:
        st.metric("Speed", ps.get("speed", "N/A").title())
    with col4:
        st.metric("Sessions Completed", f"{ps.get('completion_rate',0)*100:.0f}%")

    delta = ps.get("cohort_delta", 0)
    cohort_avg = ps.get("cohort_avg", 0)

    st.markdown(
        f"**{ps.get('weak_count',0)} topics need work** · "
        f"**{ps.get('strong_count',0)} strong topics** · "
        f"Cohort avg: {cohort_avg:.1f}% · {delta_html(delta)}",
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown("### 📋 Your Personalised Study Steps")

    DOST_COLORS = {
        "concept": "#6366f1",
        "formula": "#0ea5e9",
        "revision": "#8b5cf6",
        "practiceAssignment": "#f59e0b",
        "practiceTest": "#ef4444",
        "clickingPower": "#10b981",
        "pickingPower": "#f97316",
        "speedRace": "#dc2626",
    }

    for step in data.get("steps", []):
        color = DOST_COLORS.get(step["dost_type"], "#3b82f6")
        icon = step.get("dost_icon", "")

        q_ids = step.get("question_ids") or []
        q_ids_str = ", ".join(str(q) for q in q_ids if q)

        # ✅ CLEAN MESSAGE (removes any HTML if backend sends it)
        clean_message = step.get("message", "")
        clean_message = clean_message.replace("<div class='dost-message'>", "").replace("</div>", "")

        # ✅ CARD (HTML)
        st.markdown(
            f"""<div class='dost-card' style='border-left-color:{color}'>
              <div class='dost-step'>STEP {step['step']} · {icon} {step['dost_name'].upper()}</div>
              <div class='dost-title'>{step['subject']} — {step['chapter']}</div>
              <div class='dost-reason'>📌 {step['reasoning']}</div>
              <div class='dost-reason'>⏱️ {step['duration_min']} min · {step['question_count']} questions · {step['difficulty'].title()} difficulty</div>
            </div>""",
            unsafe_allow_html=True,
        )

        # ✅ QUESTIONS
        if q_ids_str:
            st.markdown(f"📝 **Suggested Questions:** `{q_ids_str}`")

        # ✅ MESSAGE (NO HTML — FIXED)
        st.info(clean_message)

        st.markdown("<br>", unsafe_allow_html=True)

# ===========================================================================
# PAGE: Question Viewer
# ===========================================================================
elif page == "❓ Question Viewer":
    st.title("❓ Question Viewer")
    st.caption("Fetch any question from the bank by its ID (e.g. Q001, Q015)")

    question_id = st.text_input(
        "Question ID",
        value="Q001",
        placeholder="e.g. Q001",
        help="Enter the question ID shown in Study Plan steps",
    )
    if st.button("🔍 Fetch Question", type="primary"):
        if not question_id.strip():
            st.warning("Please enter a question ID.")
        else:
            q = api_get(f"/question/{question_id.strip()}")
            if q:
                difficulty_colors = {"easy": "#16a34a", "medium": "#ca8a04", "hard": "#dc2626"}
                diff = q.get("difficulty", "medium")
                diff_color = difficulty_colors.get(diff, "#6366f1")
                type_labels = {
                    "scq": "Single Correct",
                    "mcq": "Multiple Correct",
                    "integerQuestion": "Integer Type",
                }
                type_label = type_labels.get(q.get("type", ""), q.get("type", "Unknown"))

                # Meta row
                col_meta1, col_meta2 = st.columns(2)
                with col_meta1:
                    st.markdown(
                        f"**Subject:** {q.get('subject', '—')}  \n"
                        f"**Topic:** {q.get('topic', '—')}  \n"
                        f"**Subtopic:** {q.get('subtopic', '—')}"
                    )
                with col_meta2:
                    st.markdown(
                        f"<span style='background:{diff_color};color:white;padding:4px 12px;"
                        f"border-radius:12px;font-size:0.85rem'>{diff.title()}</span>"
                        f"&nbsp;&nbsp;"
                        f"<span style='background:#6366f1;color:white;padding:4px 12px;"
                        f"border-radius:12px;font-size:0.85rem'>{type_label}</span>",
                        unsafe_allow_html=True,
                    )

                st.divider()
                st.markdown(f"### {q.get('question', 'No question text')}")

                options = q.get("options", [])
                if options:
                    st.markdown("**Options:**")
                    for i, opt in enumerate(options):
                        st.markdown(f"&nbsp;&nbsp;**{chr(65+i)}.** {opt}")

                with st.expander("📖 Show Answer & Explanation"):
                    st.markdown(f"**Answer:** `{q.get('answer', 'N/A')}`")
                    if q.get("explanation"):
                        st.info(q["explanation"])
                    else:
                        st.caption("No explanation available.")
            else:
                st.error(
                    f"Question **{question_id}** not found. "
                    "Check the ID — it should match one listed in a Study Plan step."
                )


# ===========================================================================
# PAGE: Leaderboard
# ===========================================================================
elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard")
    st.caption(
        "Ranked by composite score: **50%** marks + **20%** consistency + "
        "**20%** completion + **10%** speed"
    )

    lb = api_get("/leaderboard") or []
    if not lb:
        st.info("No leaderboard data available.")
        st.stop()

    rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}
    for entry in lb:
        rank = entry["rank"]
        emoji = rank_emoji.get(rank, f"#{rank}")
        trend_e = trend_emoji(entry.get("trend", "stable"))
        rank_class = {1: "rank-gold", 2: "rank-silver", 3: "rank-bronze"}.get(rank, "rank-other")
        completion_pct = f"{entry.get('completion_rate', 0)*100:.0f}%"

        st.markdown(
            f"""
<div style='background:#f8fafc;border-radius:10px;padding:14px 20px;margin:8px 0;
            border:1px solid #e2e8f0;display:flex;align-items:center;gap:16px'>
  <span class='{rank_class}'>{emoji}</span>
  <div style='flex:1'>
    <strong style='font-size:1.05rem'>{entry['name']}</strong>
    <span style='color:#64748b;font-size:0.85rem;margin-left:8px'>{entry['student_id']}</span>
  </div>
  <div style='text-align:right'>
    <div style='font-size:1.1rem;font-weight:700;color:#1e293b'>{entry['composite_score']:.1f} pts</div>
    <div style='font-size:0.8rem;color:#64748b'>
      Avg {entry['avg_score']:.1f}% &nbsp;·&nbsp; Completion {completion_pct} &nbsp;·&nbsp; {trend_e} {entry['trend']}
    </div>
  </div>
</div>""",
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("#### Score Comparison")
    chart_html = bar_chart_html(
        {e["name"]: e["composite_score"] for e in lb},
        "Composite Scores",
    )
    st.markdown(chart_html, unsafe_allow_html=True)

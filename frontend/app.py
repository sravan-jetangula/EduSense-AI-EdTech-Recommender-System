"""
EduSense AI - Streamlit Frontend (FIXED VERSION)
"""

import streamlit as st
import requests
import os

# ✅ GLOBAL API BASE (FIXED)
API_BASE = os.getenv(
    "API_BASE_URL",
    "https://edusense-ai-edtech-recommender-system-1.onrender.com"
)

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
# API helpers
# ---------------------------------------------------------------------------
def _api(method: str, path: str):
    try:
        fn = requests.get if method == "GET" else requests.post
        r = fn(f"{API_BASE}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Cannot connect to API at {API_BASE}")
        return None
    except Exception as e:
        st.error(f"API error ({path}): {e}")
        return None


def api_get(path: str):
    return _api("GET", path)


def api_post(path: str):
    return _api("POST", path)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("🎯 EduSense AI")

page = st.sidebar.radio(
    "Navigation",
    ["🏠 Home", "📊 Analysis", "🗺️ Study Plan", "❓ Question Viewer", "🏆 Leaderboard"]
)

students = api_get("/students") or []
student_options = {s["name"]: s["student_id"] for s in students}

selected_sid = ""
selected_name = ""

if page in ["📊 Analysis", "🗺️ Study Plan", "❓ Question Viewer"]:
    if student_options:
        selected_name = st.sidebar.selectbox("Select Student", list(student_options.keys()))
        selected_sid = student_options[selected_name]
    else:
        st.sidebar.warning("No students available")

# ---------------------------------------------------------------------------
# HOME
# ---------------------------------------------------------------------------
if page == "🏠 Home":
    st.title("EduSense AI 🎯")
    st.caption("AI-powered learning recommender")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Students", len(students))

    with col2:
        cfg = api_get("/dost_config") or {}
        st.metric("DOST Types", len(cfg.get("dost_types", {})))

    with col3:
        root = api_get("/") or {}
        st.metric("Questions", root.get("questions", 0))

    with col4:
        lb = api_get("/leaderboard") or []
        top = lb[0] if lb else {}
        st.metric("Top Score", f"{top.get('avg_score',0):.0f}%")

# ---------------------------------------------------------------------------
# ANALYSIS
# ---------------------------------------------------------------------------
elif page == "📊 Analysis":
    st.title("📊 Analysis")

    if not selected_sid:
        st.stop()

    data = api_post(f"/analyze/{selected_sid}")
    if not data:
        st.stop()

    st.metric("Score", f"{data['overall_score']:.1f}%")
    st.metric("Trend", data["trend"])
    st.metric("Completion", f"{data['completion_rate']*100:.0f}%")

# ---------------------------------------------------------------------------
# STUDY PLAN
# ---------------------------------------------------------------------------
elif page == "🗺️ Study Plan":
    st.title("🗺️ Study Plan")

    if not selected_sid:
        st.stop()

    data = api_post(f"/recommend/{selected_sid}")
    if not data:
        st.stop()

    for step in data.get("steps", []):
        st.subheader(f"Step {step['step']} - {step['dost_name']}")
        st.write(step["reasoning"])
        st.write(f"⏱ {step['duration_min']} min")

# ---------------------------------------------------------------------------
# QUESTION VIEWER
# ---------------------------------------------------------------------------
elif page == "❓ Question Viewer":
    st.title("❓ Question Viewer")

    qid = st.text_input("Enter Question ID")

    if st.button("Fetch"):
        q = api_get(f"/question/{qid}")
        if q:
            st.write(q["question"])
            for opt in q.get("options", []):
                st.write(opt)
            st.success(f"Answer: {q['answer']}")

# ---------------------------------------------------------------------------
# LEADERBOARD
# ---------------------------------------------------------------------------
elif page == "🏆 Leaderboard":
    st.title("🏆 Leaderboard")

    lb = api_get("/leaderboard") or []

    for e in lb:
        st.write(f"{e['rank']}. {e['name']} - {e['composite_score']}")

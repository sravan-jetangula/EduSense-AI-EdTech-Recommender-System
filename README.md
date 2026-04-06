# 🎯 EduSense AI — EdTech Recommender System

A production-ready, AI-powered personalised learning recommender system for JEE / NEET aspirants.  
The system analyses student performance data and generates **step-by-step study plans with targeted questions**, along with a debugging case study.

---

## 🌐 Live Demo
https://edusense-ai-edtech-recommender-system.onrender.com/

---

## 📁 Project Structure

edtech_recommender/

├── backend/  
│   ├── main.py                        # FastAPI app + API endpoints  
│   ├── services/  
│   │   ├── analytics_service.py       # Performance analysis & leaderboard  
│   │   └── recommender_service.py     # Study plan generator  
│   └── utils/  
│       └── data_processor.py          # Data normalization utilities  

├── frontend/  
│   └── app.py                         # Streamlit UI  

├── data/  
│   ├── sample_data/  
│   │   ├── student_performance.json  
│   │   ├── question_bank.json  
│   │   └── dost_config.json  
│   └── sample_outputs/  

├── debug/  
│   └── debug_fixed.py                 # Bug explanation and fix  

├── Dockerfile.backend  
├── Dockerfile.frontend  
├── requirements.txt  
└── README.md  

---

## 🚀 Quick Start

### 1. Install Dependencies
pip install -r requirements.txt

### 2. Start Backend
uvicorn backend.main:app --reload --port 8000

### 3. Start Frontend
streamlit run frontend/app.py

### 4. Run Debug Module
python debug/debug_fixed.py

Access:
- UI → http://localhost:8501  
- API Docs → http://localhost:8000/docs  

---

## 🧠 Recommender System Approach

The system uses a **cohort-relative profiling + rule-based recommendation engine**.

---

### 1. Feature Vectorisation

Each student is represented as:

[physics_avg, chemistry_avg, math_avg, biology_avg, completion_rate, (1 - skip_rate), speed_normalised]

All values are scaled between 0 and 1.

---

### 2. Cohort-Relative Profiling

Instead of raw scores:

student_profile = student_vector - cohort_average  
student_profile = student_profile / ||student_profile||

This helps identify **relative strengths and weaknesses**.

---

### 3. DOST-Based Recommendation Rules

Rules are dynamically read from configuration:

| Condition | Recommendation |
|----------|--------------|
| Score < 40% | Concept Building |
| High skip rate | Formula Revision |
| Low completion | Revision |
| 40–60% | Practice Assignment |
| 60–75% | Practice/Test |
| ≥75% | Speed / Accuracy |

---

### 4. Step-by-Step Study Plan

Each student receives a structured plan:

Step 1 → Concept building (weak topic)  
Step 2 → Formula revision  
Step 3 → Practice questions  
Step 4 → Mock test  
Step 5 → Speed / accuracy improvement  

Each step includes:
- Target topic  
- Objective  
- **Specific practice questions**

---

## 🔧 Data Preprocessing

### Marks Normalisation
Handles multiple formats:
- "39/100"
- "+48 -8"
- "49/120 (40.8%)"
- Raw numbers

---

### ID Normalisation
Supports:
- MongoDB ObjectId format  
- Plain string IDs  

---

### Difficulty Mapping
- 1–2 → Easy  
- 3 → Medium  
- 4+ → Hard  

---

### Deduplication
- Removes duplicate questions  
- Ensures clean dataset  

---

## 🐞 Debugging Case Study

### Problem
All students were receiving identical recommendations.

### Root Cause
A variable overwrite bug replaced the personalised profile with the cohort average.

### Fix
Correct normalization applied to the student's deviation vector.

### Result
Each student now receives **unique and personalised recommendations**.

---

## 📊 Leaderboard Formula

composite =  
0.50 × performance  
+ 0.20 × consistency  
+ 0.20 × completion rate  
+ 0.10 × speed  

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|--------|------------|
| GET | / | Health check |
| GET | /students | List students |
| GET/POST | /analyze/{id} | Performance analysis |
| GET/POST | /recommend/{id} | Study plan |
| GET | /leaderboard | Rankings |
| GET | /question/{id} | Question details |

---

## 🔮 Future Improvements

- Spaced repetition system  
- Collaborative filtering  
- LLM-based explanations  
- Real-time adaptive learning  
- Database integration (PostgreSQL)  
- Authentication & dashboards  

---

## 📄 License
MIT License

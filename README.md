🎯 EduSense AI — Student Performance Recommender System

🚀 Live Demo: https://edusense-ai-edtech-recommender-system.onrender.com/

EduSense AI is a production-ready, AI-powered personalized learning recommender system designed for JEE/NEET aspirants. It analyzes student performance data and generates step-by-step study plans with targeted questions, along with debugging insights.

Built using FastAPI, Streamlit, and robust data processing pipelines, the system focuses on actionable learning recommendations rather than just analytics.

📌 Key Features
✅ Personalized Study Recommendations
Analyzes student performance across subjects
Identifies weak, moderate, and strong areas
Generates prioritized learning paths
✅ Step-by-Step Study Plan (Core Requirement)

Each student receives a structured plan:

Concept building
Practice assignments
Revision strategies
Mock tests
Speed improvement drills

Each step includes:

🎯 Clear objective
📘 Target topic
❓ Specific practice questions
✅ Cohort-Based Intelligence
Compares student performance against peers
Uses relative deviation instead of raw scores
Ensures smarter and fair recommendations
✅ Debugging Module (Assignment Requirement)
Identifies a critical recommender bug
Explains root cause clearly
Demonstrates fixed behavior with comparison
✅ Interactive UI (Streamlit)
Multi-page dashboard
Real-time recommendation generation
Visual analytics & leaderboard
🧠 System Architecture
1. Feature Engineering

Each student is represented as a normalized vector:

Subject scores (Physics, Chemistry, Math, Biology)
Completion rate
Skip rate
Speed (time per question)
2. Cohort-Relative Profiling

Instead of raw scores:

Computes student deviation from cohort average
Applies L2 normalization
Captures true strengths and weaknesses
3. Rule-Based Recommendation Engine

Uses configurable DOST (Dynamic Optimization Study Types):

Condition	Recommendation
Score < 40%	Concept Building
High Skip Rate	Formula Revision
Low Completion	Revision
40–60%	Practice Assignment
60–75%	Practice/Test Strategy
≥75%	Speed / Accuracy Optimization
4. Multi-Step Study Plan Generation

Each plan includes 4–5 steps:

Weak topic → Concept building
Formula reinforcement
Targeted practice
Full mock test
Speed or accuracy improvement

👉 Questions are dynamically selected from the question bank.

📁 Project Structure


edtech_recommender/
├── backend/
│   ├── main.py
│   ├── services/
│   │   ├── analytics_service.py
│   │   └── recommender_service.py
│   └── utils/
│       └── data_processor.py
│
├── frontend/
│   └── app.py
│
├── data/
│   ├── sample_data/
│   └── sample_outputs/
│
├── debug/
│   └── debug_fixed.py
│
├── Dockerfile.backend
├── Dockerfile.frontend
├── requirements.txt
└── README.md


🚀 Deployment
🌐 Live Application

👉 https://edusense-ai-edtech-recommender-system.onrender.com/

⚙️ Local Setup
1. Install Dependencies
pip install -r requirements.txt
2. Start Backend
uvicorn backend.main:app --reload --port 8000
3. Start Frontend
streamlit run frontend/app.py
4. Run Debug Module
python debug/debug_fixed.py
🔌 API Endpoints
Method	Endpoint	Description
GET	/	Health check
GET	/students	List students
GET/POST	/analyze/{student_id}	Performance analysis
GET/POST	/recommend/{student_id}	Study plan
GET	/leaderboard	Rankings
GET	/question/{id}	Question details
🔧 Data Processing Highlights
✔ Marks Normalization

Handles inconsistent formats:

39/100
+48 -8
49/120 (40.8%)
Raw numeric values
✔ ID Normalization

Supports:

MongoDB ObjectID format
Plain string IDs
✔ Difficulty Mapping
Easy / Medium / Hard classification
Default fallback handling
✔ Deduplication
Removes duplicate questions by ID
Ensures clean dataset
🐞 Debugging Case Study
Problem

All students were receiving identical recommendations.

Root Cause

A variable overwrite bug:

Personalized vector was replaced by cohort average
Fix
Correct normalization applied to student deviation
Result
Fully personalized recommendations restored
📊 Leaderboard Logic

Composite score based on:

Performance (50%)
Consistency (20%)
Completion rate (20%)
Speed (10%)
🔮 Future Enhancements
Spaced repetition (SM-2 algorithm)
Collaborative filtering
LLM-generated explanations
Real-time adaptive learning
Database integration (PostgreSQL)
Authentication & dashboards
 Assignment Alignment
Requirement	Status
Performance Analysis	✅
Study Recommendation	✅
Step-by-Step Plan	✅
Questions per Step	✅
Debug Task	✅
Deployment	✅
📄 License

MIT License
 Author

Jetangula Sravan Kumar

 Final Note

This project focuses on clarity, personalization, and real-world applicability, demonstrating how AI can move beyond analytics to deliver actionable learning intelligence.


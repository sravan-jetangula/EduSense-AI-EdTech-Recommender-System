# 🎯 EduSense AI — EdTech Recommender System

> A production-quality, AI-powered personalised learning recommender for JEE / NEET aspirants,
> built with \*\*FastAPI\*\*, \*\*Streamlit\*\*, and pure Python analytics.

\---

## 📁 Project Structure

```
edtech\_recommender/
├── backend/
│   ├── main.py                        # FastAPI app + all endpoints
│   ├── services/
│   │   ├── analytics\_service.py       # Performance analysis \& leaderboard
│   │   └── recommender\_service.py     # DOST-based study plan generator
│   └── utils/
│       └── data\_processor.py          # All data normalisation helpers
├── frontend/
│   └── app.py                         # Streamlit UI (5 pages)
├── data/
│   ├── sample\_data/
│   │   ├── student\_performance.json   # 5 students, messy real-world data
│   │   ├── question\_bank.json         # 40 questions, mixed formats
│   │   └── dost\_config.json           # 8 DOST type configurations
│   └── sample\_outputs/                # Pre-generated analysis \& recs (JSON)
├── debug/
│   └── debug\_fixed.py                 # Documented bug + fix + demo
├── requirements.txt
└── README.md
```

\---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the API (from project root)
uvicorn backend.main:app --reload --port 8000

# 3. Start the UI (new terminal)
streamlit run frontend/app.py

# 4. Run the debug demonstration
python debug/debug\_fixed.py
```

Open **http://localhost:8501** for the Streamlit UI.
Open **http://localhost:8000/docs** for the interactive API docs.

\---

## 🧠 Recommender System Approach

The recommender follows a **profile deviation + DOST mapping** architecture across four stages:

### 1\. Feature Vectorisation

Each student is represented as a 7-dimensional vector:

```
\[physics\_avg, chemistry\_avg, math\_avg, biology\_avg,
 completion\_rate, (1 - skip\_rate), speed\_normalised]
```

All values are scaled to \[0, 1].  Subject scores are divided by 100;
speed is mapped so 1.0 = 30s/question (fast) and 0.0 = 300s+ (slow).

### 2\. Cohort-Relative Profiling

Instead of recommending on raw scores, we compute how much each student
**deviates from the cohort average** and L2-normalise that deviation:

```python
student\_profile = student\_vector - cohort\_average     # personalised deviation
norm = ||student\_profile||
student\_profile = student\_profile / norm              # L2 normalised
```

This identifies *relative* strengths/weaknesses independent of overall exam
difficulty.  A student at 60% in a 70%-average cohort has a negative deviation
and receives remedial recommendations — even though 60% is objectively decent.
The normalisation step ensures no single dimension dominates the profile.

### 3\. DOST Selection Rules

The student profile feeds a rule engine that selects from 8 DOST types.
**Rules are read directly from `dost\_config.json`** — no hardcoded logic:

|Condition|DOST Recommended|
|-|-|
|Score < 40%|Concept Building|
|High skip rate (> 30%)|Formula Sheet|
|Low completion (< 50%)|Revision|
|Score 40–60%|Practice Assignment|
|Score 60–75%, slow|Picking Power|
|Score 60–75%, normal|Practice Test|
|Score ≥ 75%, fast|Speed Race|
|Score ≥ 75%, normal|Clicking Power|

### 4\. Multi-Step Plan Generation

Each student receives 4–5 ordered steps.  Parameters (duration, question count,
difficulty) are pulled from `dost\_config.json` — nothing is hardcoded in code:

|Step|Purpose|DOST Type|
|-|-|-|
|1|Address weakest topic|concept|
|2|Formula revision on weakest subject|formula|
|3|Targeted practice on moderate topic|practiceAssignment|
|4|Full mock on strongest subject|practiceTest|
|5|Speed drill (if slow/moderate) or picking power|clickingPower / pickingPower|

Question selection is **randomised** per student — different students receive
different question IDs even when targeting the same topic.  Questions are also
filtered by subject so Physics questions never appear in a Chemistry step.

\---

## 🔧 Data Preprocessing

### Marks Normalisation (`normalize\_marks`)

Real-world data arrives in wildly inconsistent formats.  All are handled via
sequential regex matching:

|Raw Format|Strategy|Example Output|
|-|-|-|
|`"39/100"`|Fraction → percentage|39.0|
|`"+48 -8"`|Net / total possible marks|77.8%|
|`"49/120 (40.8%)"`|Extract explicit percentage (priority)|40.8|
|`49`|Treat as percentage directly|49.0|
|`"22"`|Parse numeric string|22.0|

For `"+48 -8"` format: `net = 48 - 8 = 40`; `total\_possible = 48 + 8 = 56`;
`score = 40/56 × 100 = 71.4%`.  This reflects the actual scoring intent
rather than using an arbitrary denominator.

### `\_id` Normalisation (`normalize\_id`)

MongoDB exports `\_id` in two incompatible formats:

* `{"$oid": "507f1f77bcf86cd799439011"}` — MongoDB Extended JSON
* `"507f1f77bcf86cd799439011"` — plain string

Both are unified to plain strings:

```python
def normalize\_id(raw\_id):
    if isinstance(raw\_id, dict):
        return raw\_id.get("$oid", str(raw\_id))
    return str(raw\_id).strip()
```

### Difficulty Mapping (`normalize\_difficulty`)

Numeric difficulty → categorical label:

* 1–2 → `easy`
* 3 → `medium`
* 4+ → `hard`
* `null` → `medium` (prevents downstream KeyErrors)

### Topic → Subject Mapping (`TOPIC\_SUBJECT\_MAP`)

Every canonical topic is explicitly mapped to its parent subject.  This prevents
cross-subject contamination — e.g. "Thermodynamics" exists in both Physics and
Chemistry; the mapping resolves this based on the full topic name stored in the
question's `topic` field.

### Deduplication

The question bank is de-duplicated by both `qid` and `\_id` independently on
load.  Any duplicate emits a warning and is skipped.

\---

## 🐞 Critical Bug — Root Cause \& Fix

### What Was Wrong

The recommender contained a one-line variable overwrite bug:

```python
# Line 1: compute personalised deviation — CORRECT
student\_profile = student\_vector - cohort\_average

# Line 2: BUG — overwrites the personalised vector with the global average!
student\_profile = cohort\_average / norm   # should be: student\_profile / norm
```

### Impact

Every student received **identical recommendations** regardless of their actual
performance.  The personal deviation was computed correctly on line 1, then
immediately discarded and replaced by the normalised cohort average on line 2.

### How It Was Identified

* **Symptom**: All 5 students received the same 5-step DOST plan with
identical reasoning text and question IDs.
* **Debug step 1**: Logged `student\_profile` vectors for each student.
All were numerically identical.
* **Debug step 2**: Traced the divergence to the second assignment.
Line 1 was correct; line 2 reassigned the name to a different value.
* **Root cause**: Python variable re-assignment.  The name `student\_profile`
was reused on the second line, silently replacing the personal deviation
with the cohort average divided by norm.

### The Fix

```python
# Step 1: personalised deviation (unchanged)
student\_profile = student\_vector - cohort\_average

# Step 2: compute norm OF THE PERSONAL DEVIATION
norm = math.sqrt(sum(x \* x for x in student\_profile))

# Step 3: normalise THE PERSONAL DEVIATION (not cohort\_average!)
if norm > 0:
    student\_profile = \[x / norm for x in student\_profile]   # FIXED
```

### Verification

Run `python debug/debug\_fixed.py` to see the side-by-side comparison:

```
BUGGY profiles (all identical direction):
  Arjun:  \[0.843, 0.769, 0.918, ...]
  Priya:  \[0.843, 0.769, 0.918, ...]   <- same!

FIXED profiles (personalised):
  Arjun:  \[ 0.347, -0.099,  0.422, ...]   <- strong Physics/Math, weak Bio
  Priya:  \[-0.475, -0.208, -0.475, ...]   <- different profile entirely
```

\---

## 📊 Leaderboard Formula

```
composite = 0.50 × (avg\_score / 100)
          + 0.20 × (1 - coefficient\_of\_variation)   # consistency
          + 0.20 × completion\_rate
          + 0.10 × speed\_score                       # 100% at 30s/q, 0% at 300s/q
```

This rewards students who perform **consistently** and **efficiently**, not just
those with high peak scores.  A student with a lower average but consistent
performance can outrank an inconsistent high-scorer.

\---

## 🔌 API Reference

|Method|Endpoint|Description|
|-|-|-|
|GET|`/`|Health check + system stats|
|GET|`/health`|Liveness check|
|GET|`/students`|List all students|
|GET/POST|`/analyze/{student\_id}`|Full performance analysis|
|GET/POST|`/recommend/{student\_id}`|Personalised DOST study plan|
|GET|`/question/{question\_id}`|Clean question with HTML stripped|
|GET|`/leaderboard`|Ranked student leaderboard|
|GET|`/dost\_config`|All DOST type configurations|

Both GET and POST are supported on `/analyze` and `/recommend` for convenience
(GET is easier to test in the browser / curl).

\---

## 🔮 Future Improvements

1. **Spaced Repetition Engine** — Track question history per student and use
the SM-2 algorithm to schedule revisits at optimal intervals.
2. **Collaborative Filtering** — Students with similar subject profiles but
different weak topics could borrow recommendations from peers who recently
improved in those areas.
3. **LLM-Generated Explanations** — Use an LLM to write dynamic, empathetic
study messages personalised to each student's emotional state and history.
4. **Real-Time Adaptation** — After each session, re-run the recommender and
surface updated priorities immediately in the UI.
5. **Difficulty Calibration** — Use Item Response Theory (IRT) to model true
difficulty per student, not just static labels from the question bank.
6. **Database Integration** — Migrate from JSON files to PostgreSQL with
SQLAlchemy for multi-user, concurrent access and audit trails.
7. **Auth \& Roles** — Add JWT authentication, student/teacher role separation,
and teacher dashboards for class-level trend monitoring.

\---

## 📄 License

MIT — free to use, modify, and deploy.


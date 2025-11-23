# 🏗️ Reaper Sentinel — Architecture Overview (v0.6.2)

```
            ┌──────────────────┐
            │  Streamlit UI    │
            │ dashboard/app.py │
            └───────┬──────────┘
                    │ REST API
                    ▼
         ┌────────────────────────┐
         │     FastAPI Backend    │
         │        /api            │
         └──────┬────────┬────────┘
                │        │
        ┌───────▼───┐  ┌─▼────────────┐
        │ analyzer   │  │  memory      │
        │ .py        │  │ .py          │
        └────────────┘  └──────────────┘
                │ writes             ▲
                ▼                    │ reads
          ┌──────────┐       ┌────────────┐
          │ feedback  │       │ storage    │
          │ .py       │       │ .py        │
          └──────────┘       └────────────┘
```

---

# 🧠 Core Components

### 1. **Analyzer**
- Sends prompt to LLM
- Normalizes severity
- Produces structured SIEM output

### 2. **Memory System**
- Stores each log entry permanently
- Allows recalling similar historic events

### 3. **Feedback System**
- Writes user responses to `feedback.json`
- Associates feedback to log records

### 4. **Dashboard**
- Web UI built with Streamlit
- Real-time visualization + feedback

### 5. **Storage**
- Saves full analysis reports in `/data/reports/`

---

# 🔥 Data Flow

```
UPLOAD LOG → Dashboard → /analyze → Analyzer → Memory → Dashboard → Feedback
```

Everything is **append-only**, ensuring auditability.

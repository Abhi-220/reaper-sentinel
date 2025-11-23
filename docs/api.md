# ⚔️ Reaper Sentinel API Documentation (v0.6.2)

FastAPI backend providing core SIEM intelligence to Reaper Sentinel.

---

# 📑 Base URL

```
http://localhost:8000
```

---

# 🔍 1. `GET /`
Health check message.

**Example Response**
```json
{ "message": "⚔️ Reaper Sentinel API is alive." }
```

---

# 🧠 2. `POST /analyze`

Analyze an array of logs and return global `log_id` + AI output.

### Request Body
```json
{
  "logs": [
    { "timestamp": "...", "event": "...", "ip": "..." }
  ]
}
```

### Successful Response
```json
{
  "results": [
    {
      "log_id": 16,
      "result": "SEVERITY: Medium\nCATEGORY: Authentication\n...",
      "recalled": []
    }
  ]
}
```

---

# 💬 3. `POST /feedback`

Stores user accuracy feedback for a log.

### Request Body
```json
{
  "log_id": 16,
  "feedback": "Accurate",
  "reason": "Matches SOC policy"
}
```

### Response
```json
{
  "status": "success",
  "message": "Feedback recorded.",
  "feedback": { ... }
}
```

---

# 🧠 4. `GET /memory`

Returns Reaper Brain Memory.

### Example Output
```json
{
  "records": [
    {
      "timestamp": "...",
      "log": { ... },
      "result": "SEVERITY: High\n...",
      "feedback": { ... }
    }
  ]
}
```

---

# ❤️ 5. `GET /healthz`

Returns status of:
- Ollama
- Memory system
- API

```json
{
  "status": "healthy",
  "ollama_connected": true,
  "memory_ok": true
}
```

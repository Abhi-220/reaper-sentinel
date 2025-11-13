import json
import os
from datetime import datetime
import sys

# ─────────────────────────────
# ⚙️ UTF-8 Standardization
# ─────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MEMORY_PATH = "data/reaper_memory.json"
FEEDBACK_PATH = "data/feedback.json"

# ─────────────────────────────
# 🧱 File Setup Utilities
# ─────────────────────────────
def _ensure_file():
    """Ensure reaper_memory.json exists and is initialized."""
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    if not os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump({"records": []}, f, ensure_ascii=False, indent=2)


def _ensure_feedback_file():
    """Ensure feedback.json exists and is initialized."""
    os.makedirs(os.path.dirname(FEEDBACK_PATH), exist_ok=True)
    if not os.path.exists(FEEDBACK_PATH):
        with open(FEEDBACK_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def ensure_feedback_field(records):
    """Ensure each record has a feedback key (used on load)."""
    for rec in records:
        rec.setdefault("feedback", None)
    return records

# ─────────────────────────────
# 🧠 Memory Core Functions
# ─────────────────────────────
def load_memory():
    """Load Reaper memory safely, even if the file is empty or invalid."""
    _ensure_file()

    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {"records": []}
            data = json.loads(content)
    except json.JSONDecodeError:
        print("[⚠️ Reaper Memory] Invalid JSON detected — reinitializing memory file.")
        data = {"records": []}
        save_memory(data)
    except Exception as e:
        print(f"[⚠️ Reaper Memory] Unexpected error while reading memory: {e}")
        data = {"records": []}

    data["records"] = ensure_feedback_field(data.get("records", []))
    return data


def save_memory(memory_data):
    """Persist Reaper memory to disk in UTF-8 format."""
    try:
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Reaper Memory] Failed to save memory: {e}")


def store_analysis(log_entry, ai_result):
    """Save each AI analysis result to Reaper memory."""
    memory = load_memory()
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "log": log_entry,
        "result": ai_result
    }
    memory["records"].append(record)
    save_memory(memory)
    return record


def recall_similar(log_entry):
    """Recall recent analyses with similar event patterns."""
    memory = load_memory()
    results = []
    for rec in memory["records"]:
        if log_entry.get("event") and log_entry["event"].lower() in str(rec["log"]).lower():
            results.append(rec)
    return results[-3:]  # return last 3 similar records


def add_feedback(data):
    """Attach feedback to memory record and persist globally."""
    _ensure_file()
    _ensure_feedback_file()

    memory = load_memory()
    log_id = data.get("log_id")

    feedback = {
        "feedback": data.get("feedback"),
        "reason": data.get("reason"),
        "timestamp": datetime.utcnow().isoformat()
    }

    # Attach feedback to memory
    try:
        if memory["records"]:
            if log_id and 1 <= log_id <= len(memory["records"]):
                memory["records"][log_id - 1]["feedback"] = feedback
            else:
                memory["records"][-1]["feedback"] = feedback
            save_memory(memory)
        else:
            print("[⚠️ Reaper Feedback] No memory records found to attach feedback.")
    except Exception as e:
        print(f"[Reaper Feedback] Failed to attach feedback: {e}")

    # Store feedback globally
    try:
        with open(FEEDBACK_PATH, "r+", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []

            if not isinstance(existing, list):
                existing = []

            existing.append({"log_id": log_id, **feedback})
            f.seek(0)
            json.dump(existing, f, indent=2, ensure_ascii=False)
            f.truncate()

    except Exception as e:
        print(f"[Reaper Feedback] Could not save to feedback.json: {e}")

    return feedback

import json
import os
from datetime import datetime
import sys

# UTF-8 safety
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MEMORY_PATH = "data/reaper_memory.json"
FEEDBACK_PATH = "data/feedback.json"


# ===============================================================
# UTILITIES
# ===============================================================
def _ensure_file():
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    if not os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump({"records": [], "next_id": 1}, f, indent=2, ensure_ascii=False)


def _ensure_feedback_file():
    os.makedirs(os.path.dirname(FEEDBACK_PATH), exist_ok=True)
    if not os.path.exists(FEEDBACK_PATH):
        with open(FEEDBACK_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)


def _assign_missing_ids(records):
    """
    Assign log_id = 1..N for older versions where log_id was not stored.
    Ensures perfect monotonic continuity.
    """
    for i, rec in enumerate(records, start=1):
        rec.setdefault("log_id", i)
        rec["log_id"] = int(rec["log_id"])
    return records


# ===============================================================
# LOAD / SAVE
# ===============================================================
def load_memory():
    _ensure_file()

    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"records": [], "next_id": 1}
        save_memory(data)

    # Ensure keys exist
    data.setdefault("records", [])
    data.setdefault("next_id", len(data["records"]) + 1)

    # Normalize older memory
    data["records"] = _assign_missing_ids(data["records"])

    return data



def save_memory(memory_data):
    try:
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Reaper Memory] Failed to save: {e}")


# ===============================================================
# WRITE: STORE ANALYSIS (global monotonic ID)
# ===============================================================
def store_analysis(log_entry, ai_result):
    memory_data = load_memory()

    log_id = memory_data["next_id"]
    memory_data["next_id"] += 1

    record = {
        "log_id": log_id,
        "timestamp": datetime.utcnow().isoformat(),
        "log": log_entry,
        "result": ai_result,
        "feedback": None
    }

    memory_data["records"].append(record)
    save_memory(memory_data)

    return record


# ===============================================================
# READ: SIMILARITY RECALL
# ===============================================================
def recall_similar(log_entry):
    mem = load_memory()
    out = []

    for rec in mem["records"]:
        try:
            if (
                log_entry.get("event")
                and str(log_entry["event"]).lower() in str(rec["log"]).lower()
            ):
                out.append(rec)
        except Exception:
            pass

    return out[-3:]  # last 3 only


# ===============================================================
# FEEDBACK
# ===============================================================
def add_feedback(data):
    _ensure_file()
    _ensure_feedback_file()

    mem = load_memory()
    records = mem["records"]
    log_id = int(data.get("log_id"))

    fb_obj = {
        "feedback": data.get("feedback"),
        "reason": data.get("reason"),
        "timestamp": datetime.utcnow().isoformat()
    }

    # Attach to memory record
    updated = False
    for rec in records:
        if rec["log_id"] == log_id:
            rec["feedback"] = fb_obj
            updated = True
            break

    if updated:
        mem["records"] = records
        save_memory(mem)
    else:
        print(f"[⚠️ Reaper Feedback] No record found for log_id={log_id}")

    # Save global feedback
    try:
        with open(FEEDBACK_PATH, "r+", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except Exception:
                existing = []

            if not isinstance(existing, list):
                existing = []

            existing.append({"log_id": log_id, **fb_obj})
            f.seek(0)
            json.dump(existing, f, indent=2, ensure_ascii=False)
            f.truncate()

    except Exception as e:
        print(f"[Reaper Feedback] Could not save global feedback: {e}")

    return fb_obj

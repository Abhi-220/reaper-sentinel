# main.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from core.analyzer import batch_analyze
from core import memory
import subprocess
import sys
import os
import requests
import json
import re
from typing import Any, Dict

# ─────────────────────────────
# 🧠 UTF-8 Standardization
# ─────────────────────────────
# Force stdout encoding to UTF-8 when available (helps Windows)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ─────────────────────────────
# ⚙️ Reaper Memory Setup
# ─────────────────────────────
# Ensure files exist before we start handling requests
memory._ensure_file()
memory._ensure_feedback_file()

# ─────────────────────────────
# 🧱 FastAPI Initialization
# ─────────────────────────────
app = FastAPI(title="Reaper Sentinel API", version="0.6")

# Default Ollama host (change via ENV)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


# ─────────────────────────────
# 🧹 Safe Print & Emoji Sanitizer
# ─────────────────────────────
def safe_print(msg: Any) -> None:
    """
    Print safely across environments that may not support some Unicode characters.
    We prefer to print the full unicode string, but if the console fails, we fallback
    to an encoded/ignored representation so nothing crashes.
    """
    try:
        # Convert non-str types to JSON-like or str
        if not isinstance(msg, str):
            try:
                out = json.dumps(msg, ensure_ascii=False)
            except Exception:
                out = str(msg)
        else:
            out = msg
        print(out, flush=True)
    except UnicodeEncodeError:
        # Fallback: encode utf-8 ignoring errors and decode back for safe print
        try:
            print(out.encode("utf-8", errors="ignore").decode("utf-8"), flush=True)
        except Exception:
            # Last resort plain str
            print(str(out).encode("ascii", errors="ignore").decode("ascii"), flush=True)
    except Exception as e:
        # Never raise from logging
        try:
            print(f"[safe_print] Logging failed: {e}", flush=True)
        except Exception:
            pass


def sanitize_text(text: Any) -> Any:
    """
    Strip non-ascii characters from strings for safe console logging.
    If input is not a string, return as-is.
    """
    if not isinstance(text, str):
        return text
    # keep printable ASCII only
    return re.sub(r"[^\x00-\x7F]+", "", text)


# ─────────────────────────────
# 🩺 Health Check Endpoint
# ─────────────────────────────
@app.get("/healthz")
def health_check():
    ollama_ok, memory_ok = False, True

    # Check Ollama
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        ollama_ok = (r.status_code == 200)
    except Exception:
        ollama_ok = False

    # Check Memory
    try:
        data = memory.load_memory()
        memory_ok = isinstance(data, dict) and "records" in data
    except Exception:
        memory_ok = False

    status = (
        "healthy" if ollama_ok and memory_ok
        else "degraded" if ollama_ok or memory_ok
        else "unhealthy"
    )

    return {
        "status": status,
        "ollama_connected": ollama_ok,
        "memory_ok": memory_ok
    }


# ─────────────────────────────
# ⚔️ Root Endpoint
# ─────────────────────────────
@app.get("/")
def root():
    return {"message": "⚔️ Reaper Sentinel API is alive."}


# ─────────────────────────────
# 🧠 Log Analysis Endpoint
# ─────────────────────────────
class LogRequest(BaseModel):
    logs: list


@app.post("/analyze")
def analyze(request: LogRequest):
    results = batch_analyze(request.logs)
    return {"results": results}


# ─────────────────────────────
# 💬 Feedback Endpoint
# ─────────────────────────────
@app.post("/feedback")
def feedback(data: Dict[str, Any]):
    """
    Store user feedback for a specific log entry.
    Expected: {"log_id": 1, "feedback": "Accurate ✅", "reason": "Matched SOC alert signature"}
    - emojis and non-ascii are preserved in stored data
    - console logs are sanitized so Windows consoles don't crash
    """
    try:
        # Basic validation: must be object with at least 'feedback' or 'log_id'
        if not isinstance(data, dict):
            return JSONResponse(content={"status": "error", "message": "Invalid payload, expected JSON object."}, status_code=400)

        # Sanitized form for logging (no emojis)
        safe_log = {k: sanitize_text(v) for k, v in data.items()}
        # Use ensure_ascii=False so emojis appear where supported; safe_print will handle console fallback
        try:
            safe_print({"event": "feedback_received", "payload": safe_log})
        except Exception:
            safe_print(f"[API] Feedback received (sanitized): {safe_log}")

        # Persist full payload (emoji-preserved) to memory/feedback store
        fb = memory.add_feedback(data)

        safe_print({"event": "feedback_stored", "log_id": data.get("log_id"), "summary": sanitize_text(data.get("feedback"))})
        return JSONResponse(content={"status": "success", "message": "Feedback recorded.", "feedback": fb}, status_code=200)

    except Exception as e:
        safe_print({"event": "feedback_error", "error": str(e)})
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


# ─────────────────────────────
# 🧠 Memory Access Endpoint
# ─────────────────────────────
@app.get("/memory")
def get_memory():
    try:
        data = memory.load_memory()
        if not isinstance(data, dict) or "records" not in data:
            data = {"records": []}
        return JSONResponse(content=data, status_code=200)
    except Exception as e:
        safe_print({"event": "memory_read_error", "error": str(e)})
        return JSONResponse(content={"records": [], "warning": f"Memory unavailable: {str(e)}"}, status_code=200)

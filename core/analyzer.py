# core/analyzer.py
import json
import requests
import os
import time
import logging
from typing import List, Dict, Any
from core import memory

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "mistral")
REQUEST_TIMEOUT = int(os.getenv("ANALYZER_TIMEOUT", "120"))

# ─────────────────────────────────────────────
# LOGGER
# ─────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("reaper.analyzer")
if not logger.handlers:
    fh = logging.FileHandler("logs/reaper_analyzer.log", encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
logger.setLevel(logging.INFO)

# ─────────────────────────────────────────────
# SEVERITY LEVELS
# ─────────────────────────────────────────────
SEVERITY_LEVELS = ["Critical", "High", "Medium", "Low", "Informational"]

def normalize_severity(text: str) -> str:
    if not text:
        return "Informational"
    text = text.lower()
    for lvl in SEVERITY_LEVELS:
        if lvl.lower() in text:
            return lvl
    return "Informational"

# ─────────────────────────────────────────────
# PROMPT WITH CORRECT PLACEHOLDER
# ─────────────────────────────────────────────
ANALYZE_PROMPT = """You are Reaper Sentinel — an autonomous Tier-3 SOC AI, trained to act as a SIEM correlation engine.

Analyze the provided log(s) using STRICT security rules.

======================== RULES OF ANALYSIS ========================

1. NEVER overestimate severity.
   - A single failed login ≠ Critical
   - Mark High/Critical ONLY if the event OR correlated events prove malicious intent.

2. You MUST classify severity as one of:
   Critical, High, Medium, Low, Informational

3. For each log:
   - Identify log CATEGORY automatically (Authentication, Network, Process, IAM, File, Cloud, Access Control, or Other)
   - Map to MITRE ATT&CK:
       • Tactic (TAxxxx or None)
       • Technique (Txxxx or None)
   - Extract IoCs (IP, username, hash, domain, or None)
   - Detect BEHAVIOR pattern
   - Correlate logs to detect attack chains ONLY when visible.

4. Never assume anything not present in logs.

======================== OUTPUT FORMAT ========================

SEVERITY: <Critical|High|Medium|Low|Informational>
CATEGORY: <Authentication|Network|File|Process|Access Control|Cloud|IAM|Application|Other>
MITRE_TACTIC: <TAxxxx or None>
MITRE_TECHNIQUE: <Txxxx or None>
BEHAVIOR: <Short human SOC-style classification>
IOC: <IP/Username/Hash/Domain or None>
CHAIN: <Attack chain step or “None”>
CONFIDENCE: <High|Medium|Low>
REASON: <One-line SOC-grade justification>

========================
LOG TO ANALYZE:
{logs}
========================
"""

# ─────────────────────────────────────────────
# PARSER — Converts raw model text → dict
# ─────────────────────────────────────────────
def parse_reaper_output(text):
    fields = {
        "SEVERITY": None,
        "CATEGORY": None,
        "MITRE_TACTIC": None,
        "MITRE_TECHNIQUE": None,
        "BEHAVIOR": None,
        "IOC": None,
        "CHAIN": None,
        "CONFIDENCE": None,
        "REASON": None
    }

    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().upper()
        value = value.strip()

        if key in fields:
            fields[key] = value

    # Normalize severity
    fields["SEVERITY"] = normalize_severity(fields["SEVERITY"])
    return fields


# ─────────────────────────────────────────────
# SINGLE LOG ANALYSIS
# ─────────────────────────────────────────────
def analyze_log(entry: Dict[str, Any]) -> Dict[str, Any]:
    prompt = ANALYZE_PROMPT.format(logs=json.dumps(entry, indent=2))

    try:
        start = time.time()
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
            timeout=REQUEST_TIMEOUT
        )
        elapsed = round(time.time() - start, 2)

        if resp.status_code != 200:
            logger.error(f"{MODEL_NAME} | {elapsed}s | API {resp.status_code}")
            return {"ERROR": f"Ollama returned {resp.status_code}"}

        raw = resp.json().get("response", "").strip()

        parsed = parse_reaper_output(raw)

        logger.info(f"{MODEL_NAME} | {elapsed}s | OK | Severity={parsed['SEVERITY']}")
        return parsed

    except Exception as e:
        logger.exception("Analyzer failure")
        return {"ERROR": str(e)}


# ─────────────────────────────────────────────
# BATCH ANALYSIS (global log IDs)
# ─────────────────────────────────────────────
def batch_analyze(logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    memory_state = memory.load_memory()
    existing_count = len(memory_state.get("records", []))

    for i, entry in enumerate(logs, start=1):
        recalled = memory.recall_similar(entry)

        parsed = analyze_log(entry)
        memory.store_analysis(entry, parsed)   # Store structured dict

        global_id = existing_count + i

        results.append({
            "log_id": global_id,
            "result": parsed,
            "recalled": recalled
        })

    return results


# ─────────────────────────────────────────────
# Quick manual test runner
# ─────────────────────────────────────────────
if __name__ == "__main__":
    sample_log = {
        "timestamp": "2025-11-10T10:12:01Z",
        "event": "Failed login attempt",
        "source_ip": "45.76.123.12",
        "username": "admin",
        "details": "3 failed SSH auth attempts in 60s"
    }
    print("=== Reaper Sentinel Analyzer — local test ===")
    out = analyze_log(sample_log)
    print(out)

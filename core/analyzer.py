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
# SEVERITY NORMALIZATION
# ─────────────────────────────────────────────
SEVERITY_LEVELS = ["Critical", "High", "Medium", "Low", "Informational"]

SEVERITY_KEYWORDS = {
    "Critical": ["critical", "compromise", "ransom", "exfiltration", "privilege escalation"],
    "High": ["high", "exploit", "malware", "breach", "intrusion"],
    "Medium": ["medium", "suspicious", "anomaly", "warning"],
    "Low": ["low", "minor", "unusual"],
    "Informational": ["info", "informational", "benign", "normal", "heartbeat"]
}

def normalize_severity(text: str) -> str:
    """Map arbitrary text to one of the SEVERITY_LEVELS (safe fallback: Informational)."""
    if not text:
        return "Informational"
    lower = text.lower()
    # direct match for named tokens
    for lvl in SEVERITY_LEVELS:
        if lvl.lower() in lower:
            return lvl
    # keyword based matching
    for lvl, keywords in SEVERITY_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return lvl
    # fallback
    return "Informational"

# ─────────────────────────────────────────────
# MODEL PROMPT
# ─────────────────────────────────────────────
ANALYZE_PROMPT = """You are Reaper Sentinel, an advanced SIEM-grade Cybersecurity AI Analyst.

Your job is to analyze logs with the precision of a Tier-3 SOC Analyst.

When analyzing a log:
- Classify severity strictly as one of:
  Critical, High, Medium, Low, Informational
- Detect MITRE ATT&CK tactics and techniques.
- Identify Indicators of Compromise (IOCs).
- Detect anomalies, behavioral patterns, and attack progression.
- Provide concise, actionable reasoning.
- NEVER include extra text, disclaimers, or paragraphs.

Return your output STRICTLY in this format:

SEVERITY: <Critical|High|Medium|Low|Informational>
CATEGORY: <Authentication|Network|File|Process|Access Control|Cloud|IAM|Application|Other>
MITRE_TACTIC: <TAxxxx or None>
MITRE_TECHNIQUE: <Txxxx or None>
BEHAVIOR: <Short summary of suspicious behavior or “None”>
IOC: <IP/Domain/File hash/Username etc., or “None”>
CONFIDENCE: <High|Medium|Low>
REASON: <One-line SOC-grade reasoning>

Now analyze the following log:

{log}
"""


# ─────────────────────────────────────────────
# SINGLE LOG ANALYSIS
# ─────────────────────────────────────────────
def analyze_log(entry: Dict[str, Any]) -> str:
    """
    Call Ollama API to analyze a single log entry.
    Returns normalized, human-readable output prefixed with SEVERITY line.
    """
    prompt = ANALYZE_PROMPT.format(log=json.dumps(entry, indent=2))

    try:
        start = time.time()
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
            timeout=REQUEST_TIMEOUT
        )
        elapsed = round(time.time() - start, 2)

        if resp.status_code != 200:
            logger.error(f"{MODEL_NAME} | {elapsed}s | API {resp.status_code} | {resp.text[:200]}")
            return f"[ERROR] Ollama returned {resp.status_code}: {resp.text}"

        data = resp.json()
        raw = data.get("response", "").strip()

        # Try to parse severity from model output
        # Accept either "SEVERITY: X" or free text and normalize.
        severity = None
        for line in raw.splitlines():
            if line.strip().lower().startswith("severity:"):
                severity_candidate = line.split(":", 1)[1].strip()
                severity = normalize_severity(severity_candidate)
                break

        if severity is None:
            # fallback to scanning whole response
            severity = normalize_severity(raw)

        # Build a consistent return string: include SEVERITY line + model raw text
        normalized_output = f"SEVERITY: {severity}\n{raw}"

        logger.info(f"{MODEL_NAME} | {elapsed}s | OK | {severity} | len={len(raw)}")
        return normalized_output

    except requests.exceptions.ConnectionError:
        logger.exception(f"{MODEL_NAME} | ConnectionError -> {OLLAMA_HOST}")
        return f"[ERROR] Cannot connect to Ollama API at {OLLAMA_HOST}."
    except Exception as e:
        logger.exception(f"{MODEL_NAME} | Exception")
        return f"[EXCEPTION] {str(e)}"

# ─────────────────────────────────────────────
# BATCH ANALYSIS (Appends to memory and returns results)
# ─────────────────────────────────────────────
def batch_analyze(logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyze a list of log entries, append each to memory, and return a result list
    with global log_id, result text, and recalled entries metadata.
    """
    results = []
    mem = memory.load_memory()
    existing_count = len(mem.get("records", []))

    for i, entry in enumerate(logs, start=1):
        # recall similar items (non-blocking)
        recalled = memory.recall_similar(entry)
        if recalled:
            logger.debug(f"[MEMORY] Found {len(recalled)} similar entries for input #{i}")

        # analyze
        result_text = analyze_log(entry)

        # store analysis (memory stores timestamp, log, result)
        memory.store_analysis(entry, result_text)

        # compute global id (append-only)
        global_id = existing_count + i

        results.append({
            "log_id": global_id,
            "result": result_text,
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

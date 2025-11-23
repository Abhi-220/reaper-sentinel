# core/analyzer.py
import json
import requests
import os
import time
import logging
from typing import List, Dict, Any
from core import memory

# =====================================================================
# CONFIG
# =====================================================================
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "mistral")
REQUEST_TIMEOUT = int(os.getenv("ANALYZER_TIMEOUT", "120"))
RETRY_COUNT = int(os.getenv("ANALYZER_RETRIES", "3"))
RETRY_BACKOFF = float(os.getenv("ANALYZER_BACKOFF", "0.8"))  # multiplier

# =====================================================================
# LOGGER SETUP
# =====================================================================
os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("reaper.analyzer")
if not logger.handlers:
    fh = logging.FileHandler("logs/reaper_analyzer.log", encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

logger.setLevel(logging.INFO)

# =====================================================================
# SEVERITY NORMALIZATION
# =====================================================================
SEVERITY_LEVELS = ["Critical", "High", "Medium", "Low", "Informational"]

def normalize_severity(text: str) -> str:
    """Normalize severity extracted from model output."""
    if not text:
        return "Informational"
    text = str(text).lower()
    for lvl in SEVERITY_LEVELS:
        if lvl.lower() in text:
            return lvl
    return "Informational"


# =====================================================================
# MASTER PROMPT (FULL SIEM VERSION)
# =====================================================================
ANALYZE_PROMPT = """
You are **Reaper Sentinel**, an autonomous Tier-3 SOC AI designed to function as a SIEM correlation engine.

Your responsibility is to analyze logs with professional SOC rigor, classify them, detect IoCs, identify MITRE ATT&CK patterns, and correlate across events. 
You must NEVER hallucinate and NEVER produce text outside the required schema.

=========================================================
CORE ANALYSIS PRINCIPLES
=========================================================

1. NEVER overestimate severity.
   - A single failed login ≠ Critical.
   - High or Critical ONLY if the event itself OR correlated patterns indicate malicious intent.

2. ALWAYS classify severity as ONE of:
   Critical, High, Medium, Low, Informational

3. Correlate events based ONLY on visible evidence.
   Valid examples:
     - Multiple failed logins from same IP → brute-force
     - Failed login → success → privilege escalation
     - Lateral movement (remote execution / SMB / RDP)
     - Malware staging sequence
     - File modification + privilege escalation → persistence

4. NEVER assume anything not clearly present in the logs.

5. CATEGORY must match one of:
   Authentication, Network, File, Process, IAM, Access Control, Cloud, Application, Other

6. MITRE fields:
   - MITRE_TACTIC must be TAxxxx or None
   - MITRE_TECHNIQUE must be Txxxx or None
   Do NOT guess advanced technique names without evidence.

7. BEHAVIOR must be concise SOC-style summary.

8. IOC must capture IP, username, hash, domain, or file path if present.  
   If no indicators → "None"

9. CHAIN describes the attack step only if visible.  
   Otherwise "None".

10. CONFIDENCE:
   High = strong indicators  
   Medium = partial indicators  
   Low = weak/ambiguous

=========================================================
OUTPUT FORMAT (STRICT — DO NOT ADD ANY EXTRA TEXT)
=========================================================

SEVERITY: <Critical|High|Medium|Low|Informational>
CATEGORY: <Authentication|Network|File|Process|Access Control|Cloud|IAM|Application|Other>
MITRE_TACTIC: <TAxxxx or None>
MITRE_TECHNIQUE: <Txxxx or None>
BEHAVIOR: <Short human SOC-style classification>
IOC: <IP/Username/Hash/Domain or None>
CHAIN: <Attack chain step or "None">
CONFIDENCE: <High|Medium|Low>
REASON: <One-line SOC justification>

=========================================================
LOG TO ANALYZE:
{logs}
=========================================================
"""


# =====================================================================
# PARSER: STRICT SCHEMA PARSING
# =====================================================================
def parse_reaper_output(text: str) -> Dict[str, Any]:
    """Parse 9-field SIEM schema from model output into a stable dict."""
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

    if not text:
        # return defaults
        for k in fields:
            fields[k] = None
        return fields

    # If model returned a JSON-like string, try to parse first
    txt = text.strip()
    try:
        parsed_json = json.loads(txt)
        if isinstance(parsed_json, dict):
            for k, v in parsed_json.items():
                ku = str(k).strip().upper()
                if ku in fields:
                    fields[ku] = v
    except Exception:
        # fallback to line-by-line KEY: value parsing
        for line in txt.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            ku = key.strip().upper()
            if ku in fields:
                fields[ku] = value.strip()

    # Ensure severity normalization and fallbacks
    fields["SEVERITY"] = normalize_severity(fields.get("SEVERITY"))
    # Default other text fields to "None" (consistent schema) when missing
    for k in ["CATEGORY", "MITRE_TACTIC", "MITRE_TECHNIQUE", "BEHAVIOR", "IOC", "CHAIN", "CONFIDENCE", "REASON"]:
        if fields.get(k) is None:
            fields[k] = "None" if k in ["MITRE_TACTIC", "MITRE_TECHNIQUE", "IOC", "CHAIN"] else ""
    return fields


# =====================================================================
# SINGLE LOG ANALYSIS (with retries)
# =====================================================================
def _call_ollama(prompt: str) -> Dict[str, Any]:
    """Call Ollama with retry/backoff and return response JSON or raise."""
    attempt = 0
    backoff = 0.5
    while attempt < RETRY_COUNT:
        try:
            resp = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
                timeout=REQUEST_TIMEOUT
            )
            return {"status_code": resp.status_code, "text": resp.text, "json": resp.json() if resp.text else {}}
        except requests.exceptions.RequestException as e:
            logger.warning(f"Ollama call attempt {attempt+1}/{RETRY_COUNT} failed: {e}")
            attempt += 1
            time.sleep(backoff)
            backoff *= RETRY_BACKOFF
    # final attempt without swallow (return error status to caller)
    raise ConnectionError(f"Failed to connect to Ollama after {RETRY_COUNT} attempts")


def analyze_log(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a single log entry and return a structured dict aligned with the SIEM schema.
    This function never returns raw text as the final object — it always returns a dict.
    """
    prompt = ANALYZE_PROMPT.format(logs=json.dumps(entry, indent=2))
    result_obj: Dict[str, Any] = {
        "SEVERITY": "Informational",
        "CATEGORY": "Other",
        "MITRE_TACTIC": "None",
        "MITRE_TECHNIQUE": "None",
        "BEHAVIOR": "",
        "IOC": "None",
        "CHAIN": "None",
        "CONFIDENCE": "Low",
        "REASON": "",
        "raw": None,
        "timestamp": time.time()
    }

    try:
        start = time.time()
        resp = _call_ollama(prompt)
        elapsed = round(time.time() - start, 2)

        if resp.get("status_code") != 200:
            logger.error(f"{MODEL_NAME} | {elapsed}s | API ERROR {resp.get('status_code')}")
            result_obj.update({
                "REASON": f"Ollama returned {resp.get('status_code')}",
                "raw": resp.get("text") or ""
            })
            return result_obj

        # Prefer JSON if present, else text parsing
        try:
            raw_text = resp["json"].get("response", "") if isinstance(resp.get("json"), dict) else resp.get("text", "")
        except Exception:
            raw_text = resp.get("text", "")

        raw_text = (raw_text or "").strip()
        parsed = parse_reaper_output(raw_text)

        # Merge parsed into result_obj while preserving keys
        for k in ["SEVERITY", "CATEGORY", "MITRE_TACTIC", "MITRE_TECHNIQUE", "BEHAVIOR", "IOC", "CHAIN", "CONFIDENCE", "REASON"]:
            # parsed may contain "None" strings or empty strings; keep them
            result_obj[k] = parsed.get(k, result_obj.get(k))

        result_obj["raw"] = raw_text
        result_obj["timestamp"] = time.time()

        logger.info(f"{MODEL_NAME} | {elapsed}s | OK | Severity={result_obj['SEVERITY']}")
        return result_obj

    except ConnectionError as ce:
        logger.exception("Ollama connection failure")
        result_obj["REASON"] = str(ce)
        result_obj["raw"] = None
        return result_obj

    except Exception as e:
        logger.exception("Analyzer failure")
        result_obj["REASON"] = str(e)
        result_obj["raw"] = None
        return result_obj


# =====================================================================
# BATCH ANALYSIS
# =====================================================================
def batch_analyze(logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyze a list of log entries, persist each with memory.store_analysis which
    returns the saved record (including permanent log_id). Return list of results.
    """
    results: List[Dict[str, Any]] = []

    for entry in logs:
        # Non-blocking recall for context (already protected inside memory)
        try:
            recalled = memory.recall_similar(entry)
        except Exception:
            recalled = []

        parsed = analyze_log(entry)

        # store_analysis returns saved record including global log_id
        try:
            rec = memory.store_analysis(entry, parsed)
            log_id = rec.get("log_id")
        except Exception as e:
            logger.exception("Failed to store analysis in memory")
            # fallback: generate log_id as timestamp-based negative to avoid collision
            log_id = int(time.time() * 1000 * -1)
            rec = {"log_id": log_id}

        results.append({
            "log_id": log_id,
            "result": parsed,
            "recalled": recalled
        })

    return results


# =====================================================================
# MANUAL TEST
# =====================================================================
if __name__ == "__main__":
    sample_log = {
        "timestamp": "2025-11-10T10:12:01Z",
        "event": "Failed login attempt",
        "source_ip": "45.76.123.12",
        "username": "admin"
    }
    print("=== Reaper Sentinel Analyzer Test ===")
    out = analyze_log(sample_log)
    print(json.dumps(out, indent=2, ensure_ascii=False))

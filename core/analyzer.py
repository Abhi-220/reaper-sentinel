# core/analyzer.py
import json
import requests
import os
import time
import logging

# Config
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "mistral")

# Logger
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("reaper.analyzer")
if not logger.handlers:
    fh = logging.FileHandler("logs/reaper_analyzer.log")
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
logger.setLevel(logging.INFO)

def analyze_log(entry):
    prompt = f"""
You are Reaper Sentinel — an AI Security Analyst.
Analyze this log and classify it as Critical, Medium, or Benign.
Provide one-line reasoning.

Log:
{json.dumps(entry, indent=2)}
"""
    try:
        start = time.time()
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
            timeout=120
        )
        elapsed = round(time.time() - start, 2)

        if response.status_code == 200:
            data = response.json()
            result_text = data.get("response", "").strip()
            logger.info(f"{MODEL_NAME} | {elapsed}s | len={len(result_text)} | OK")
            return result_text
        else:
            logger.error(f"{MODEL_NAME} | {elapsed}s | API Error {response.status_code}")
            return f"[ERROR] Ollama returned {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        logger.error(f"{MODEL_NAME} | ConnectionError -> {OLLAMA_HOST}")
        return f"[ERROR] Cannot connect to Ollama API at {OLLAMA_HOST}."
    except Exception as e:
        logger.exception(f"{MODEL_NAME} | Exception")
        return f"[EXCEPTION] {str(e)}"

def batch_analyze(logs):
    results = []
    for i, entry in enumerate(logs, 1):
        result = analyze_log(entry)
        results.append({"log_id": i, "result": result})
    return results

# Optional manual test
if __name__ == "__main__":
    sample_log = {
        "timestamp": "2025-11-10T10:12:01Z",
        "event": "Failed login attempt",
        "source_ip": "45.76.123.12",
        "username": "admin"
    }
    print("=== Reaper Sentinel Analysis ===")
    print(analyze_log(sample_log))

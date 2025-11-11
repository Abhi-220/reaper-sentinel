import json
import subprocess
import requests
import os

# Use environment variable for dynamic model backend (Docker will provide this)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

def analyze_log(entry):
    prompt = f"""
    You are Reaper Sentinel — an AI Security Analyst.
    Analyze this log and classify it as Critical, Medium, or Benign.
    Provide one-line reasoning.

    Log:
    {json.dumps(entry, indent=2)}
    """

    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": "mistral", "prompt": prompt, "stream": False},
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("response", "No response received.")
        else:
            return f"Error {response.status_code}: {response.text}"

    except Exception as e:
        return f"Error: {e}"

def batch_analyze(logs):
    results = []
    for i, entry in enumerate(logs, 1):
        result = analyze_log(entry)
        results.append({"log_id": i, "result": result})
    return results


def analyze_log(entry):
    prompt = f"""
    You are Reaper Sentinel — an AI Security Analyst.
    Analyze this log and classify it as Critical, Medium, or Benign.
    Provide one-line reasoning.

    Log:
    {json.dumps(entry, indent=2)}
    """

    try:
        cmd = ["ollama", "run", "mistral", prompt]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def batch_analyze(logs):
    results = []
    for i, entry in enumerate(logs, 1):
        result = analyze_log(entry)
        results.append({"log_id": i, "result": result})
    return results

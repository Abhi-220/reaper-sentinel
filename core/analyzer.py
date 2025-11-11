import json
import requests
import os

# Use environment variable for dynamic model backend (Docker will provide this)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

def analyze_log(entry):
    """
    Send a log entry to the Ollama API for analysis.
    """
    prompt = f"""
    You are Reaper Sentinel — an AI Security Analyst.
    Analyze this log and classify it as Critical, Medium, or Benign.
    Provide one-line reasoning.

    Log:
    {json.dumps(entry, indent=2)}
    """

    try:
        # Call Ollama API instead of CLI
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )

        # Handle API response
        if response.status_code == 200:
            data = response.json()
            return data.get("response", "No response received.")
        else:
            return f"[ERROR] Ollama API returned {response.status_code}: {response.text}"

    except requests.exceptions.ConnectionError:
        return f"[ERROR] Cannot connect to Ollama API at {OLLAMA_HOST}. Check if container is running."
    except Exception as e:
        return f"[EXCEPTION] {str(e)}"


def batch_analyze(logs):
    """
    Analyze multiple log entries in sequence.
    """
    results = []
    for i, entry in enumerate(logs, 1):
        print(f"Analyzing log {i}/{len(logs)}...")
        result = analyze_log(entry)
        results.append({
            "log_id": i,
            "result": result
        })
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

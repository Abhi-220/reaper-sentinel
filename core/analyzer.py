import json
import subprocess

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

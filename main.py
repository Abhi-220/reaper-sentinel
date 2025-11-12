# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from core.analyzer import batch_analyze
import subprocess
import sys
import os
import requests

# Initialize FastAPI app first
app = FastAPI(title="Reaper Sentinel API", version="0.5")

# Environment variable
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


# Health check endpoint
@app.get("/healthz")
def health_check():
    """
    Basic health check: ensures FastAPI is running and Ollama is reachable.
    """
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        ollama_ok = (r.status_code == 200)
        status = "healthy" if ollama_ok else "degraded"
        return {"status": status, "ollama_connected": ollama_ok}
    except Exception as e:
        return {"status": "unhealthy", "ollama_connected": False, "error": str(e)}

class LogRequest(BaseModel):
    logs: list

@app.get("/")
def root():
    return {"message": "⚔️ Reaper Sentinel API is alive."}

@app.post("/analyze")
def analyze(request: LogRequest):
    results = batch_analyze(request.logs)
    return {"results": results}

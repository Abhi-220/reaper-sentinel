from fastapi import FastAPI
from pydantic import BaseModel
from core.analyzer import batch_analyze

app = FastAPI(title="Reaper Sentinel API", version="0.2")

class LogRequest(BaseModel):
    logs: list

@app.get("/")
def root():
    return {"message": "⚔️ Reaper Sentinel API is alive."}

@app.post("/analyze")
def analyze(request: LogRequest):
    results = batch_analyze(request.logs)
    return {"results": results}

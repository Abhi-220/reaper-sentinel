# reaper-sentinel
To build an AI-powered Sentinel that reads, understands, and prioritizes security alerts — reducing noise and empowering defenders to act faster and smarter.

Enter venv: venv\Scripts\activate
Exit venv: deactivate
Running reaper: python -m uvicorn reaper:app
Running Streamlit: streamlit run app.py
Run the following to avoid venv error: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass


### 🧠 Production Notes
- Implement automatic log rotation (e.g., delete logs older than 7 days).
- Run Reaper via Docker or Supervisor to auto-restart services.
- Use environment variables for API keys and model configs.


### ⚙️ Production Logging Mode

For production environments, replace the `shell=True` streaming mode with direct log redirection:

```python
log_stream = open(log_file, "a", buffering=1)

api_proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
    stdout=log_stream,
    stderr=subprocess.STDOUT,
    text=True
)

dash_proc = subprocess.Popen(
    ["streamlit", "run", "dashboard/app.py", "--server.port", "8501"],
    stdout=log_stream,
    stderr=subprocess.STDOUT,
    text=True
)


⚔️ Reaper Sentinel v0.5.1

AI-Powered Security Log Analyzer — Dockerized and Powered by Ollama

🧩 Features

🧠 AI-based log analysis using Ollama + Mistral

💻 Streamlit Dashboard for visualization

⚙️ FastAPI backend with /analyze and /healthz endpoints

🩺 Health check verifies Reaper ↔ Ollama connectivity

🔒 Non-root containers for improved security

📜 Automatic logging (latency, model, response size)

🚀 Getting Started
1. Clone the Repository
git clone https://github.com/Abhi-220/reaper-sentinel.git
cd reaper-sentinel

2. Build and Start with Docker Compose
docker compose up --build


This launches:

reaper-ollama → Ollama AI engine (port 11434)

reaper-sentinel → FastAPI backend + Streamlit dashboard

🧠 Model Setup

Reaper supports any model available on Ollama.
By default, it uses the model name set in MODEL_NAME (default: mistral).

To install your model inside the Ollama container:

docker exec -it reaper-ollama ollama pull mistral


You can replace mistral with other supported models like:

llama3

phi3

gemma2

✅ Health Check

Verify that Reaper and Ollama are communicating:

curl http://localhost:8000/healthz


Expected output:

{"status":"healthy","ollama_connected":true}

💻 Dashboard

Once running, open your browser:

API → http://localhost:8000

Dashboard → http://localhost:8501

Upload your logs (.json format) and click
“🧠 Analyze Logs with Reaper”

📊 Logs

All system logs are stored in:

logs/reaper_<date>.log


Each analysis entry includes:

[INFO] mistral | 1.52s | len=98 | OK

🧱 Directory Structure
reaper-sentinel/
├── core/
│   ├── analyzer.py
│   └── ...
├── dashboard/
│   └── app.py
├── main.py
├── run_reaper.py
├── Dockerfile
├── docker-compose.yml
└── logs/

🧰 Environment Variables
Variable	Default	Description
OLLAMA_HOST	http://ollama:11434	Ollama API endpoint
MODEL_NAME	mistral	AI model name
MODE	prod	Runtime mode
💀 Author’s Note

Reaper Sentinel is a vision in progress — built from scratch to fuse Security & AI. Each version evolves toward a self-learning, context-aware SOC assistant.
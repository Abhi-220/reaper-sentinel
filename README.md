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

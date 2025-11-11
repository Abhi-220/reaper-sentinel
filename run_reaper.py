# run_reaper.py
import subprocess
import sys
import signal

def run_health_check():
    print("🩺 Running Reaper Health Check...")
    subprocess.run([sys.executable, "health_check.py"], check=False)

def start_services():
    print("\n⚙️ Starting Reaper Sentinel API...")
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
    )

    print("\n💻 Launching Reaper Sentinel Dashboard...")
    dashboard = subprocess.Popen(
        ["streamlit", "run", "dashboard/app.py", "--server.port", "8501"]
    )

    return api, dashboard

def graceful_shutdown(api, dashboard):
    print("\n🛑 Shutting down Reaper services...")
    api.terminate()
    dashboard.terminate()
    api.wait()
    dashboard.wait()
    print("✅ Reaper Sentinel stopped cleanly.")

if __name__ == "__main__":
    run_health_check()
    api, dashboard = start_services()

    try:
        api.wait()
    except KeyboardInterrupt:
        graceful_shutdown(api, dashboard)

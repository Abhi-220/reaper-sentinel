# run_reaper.py
import subprocess
import sys
import signal
import datetime
import os
import logging
import threading

# ─────────────────────────────────────────────
# ⚙️ Setup Logging
# ─────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
log_file = f"logs/reaper_{datetime.date.today()}.log"

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def log(msg):
    print(msg)
    logging.info(msg)

# ─────────────────────────────────────────────
# 🩺 Health Check
# ─────────────────────────────────────────────
def run_health_check():
    log("🩺 Running Reaper Health Check...")
    result = subprocess.run([sys.executable, "health_check.py"], capture_output=True, text=True)
    logging.info(result.stdout.strip())
    if result.stderr.strip():
        logging.error(result.stderr.strip())

def start_services():
    log("\n⚙️ Starting Reaper Sentinel API...")
    api_cmd = f'"{sys.executable}" -m uvicorn main:app --host 0.0.0.0 --port 8000'
    api_proc = subprocess.Popen(
        api_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=True,   # keep shell=True for live output
    )

    log("\n💻 Launching Reaper Sentinel Dashboard...")
    dash_cmd = 'streamlit run dashboard/app.py --server.port 8501'
    dash_proc = subprocess.Popen(
        dash_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=True,
    )

    return api_proc, dash_proc



# ─────────────────────────────────────────────
# 🧾 Live Stream + Mirror to Log
# ─────────────────────────────────────────────
def stream_output(proc, prefix):
    """Show process output in console and log file simultaneously."""
    if not proc or proc.stdout is None:
        logging.warning(f"[{prefix}] Process has no stdout (likely failed to start).")
        return

    for line in iter(proc.stdout.readline, ''):
        line = line.strip()
        if line:
            # Mirror to console
            print(f"[{prefix}] {line}")
            # Mirror to log
            logging.info(f"[{prefix}] {line}")



# ─────────────────────────────────────────────
# 🧠 Graceful Shutdown
# ─────────────────────────────────────────────
def graceful_shutdown(api, dashboard):
    log("\n🛑 Shutting down Reaper services...")
    api.terminate()
    dashboard.terminate()
    api.wait()
    dashboard.wait()
    log("✅ Reaper Sentinel stopped cleanly.")


# ─────────────────────────────────────────────
# 🚀 Main
# ─────────────────────────────────────────────
if __name__ == "__main__":
    log(f"⚔️ Reaper Sentinel Launch - {datetime.datetime.now().isoformat()}")
    run_health_check()

    api, dashboard = start_services()

    # Stream both to terminal + file concurrently
    threading.Thread(target=stream_output, args=(api, "API"), daemon=True).start()
    threading.Thread(target=stream_output, args=(dashboard, "Dashboard"), daemon=True).start()

    try:
        api.wait()
    except KeyboardInterrupt:
        graceful_shutdown(api, dashboard)



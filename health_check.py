# health_check.py
import importlib
import os
import socket
import sys
import subprocess
import importlib.util

REQUIRED_MODULES = [
    "fastapi",
    "uvicorn",
    "streamlit",
    "pandas",
    "requests",
    "colorama",
    "matplotlib"
]

def check_python_version():
    print(f"🧠 Python version: {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        print("⚠️  Python 3.10 or higher is recommended.")
    else:
        print("✅ Python version OK")

def check_dependencies():
    print("\n📦 Checking dependencies...")
    missing = []
    for pkg in REQUIRED_MODULES:
        if importlib.util.find_spec(pkg) is None:
            missing.append(pkg)
    if missing:
        print("⚠️ Missing:", ", ".join(missing))
        print("Run this to install:")
        print(f"   {sys.executable} -m pip install " + " ".join(missing))
        return False
    print("✅ All dependencies found.")
    return True

def check_ports():
    print("\n🌐 Checking service ports...")
    ports = [8000, 8501]
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(('127.0.0.1', port))
            if result == 0:
                print(f"⚠️ Port {port} is already in use.")
            else:
                print(f"✅ Port {port} is free.")
    return True

def check_directories():
    print("\n📁 Checking directories...")
    dirs = ["data/reports", "data"]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"✅ Directory ready: {d}")
    return True

def check_ollama():
    print("\n🤖 Checking Ollama availability...")
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Ollama is installed and accessible.")
        else:
            print("⚠️ Ollama command returned an error. Check installation.")
    except FileNotFoundError:
        print("⚠️ Ollama not found. Install from https://ollama.ai")

def run_all():
    print("⚔️ Reaper Sentinel — System Health Check\n" + "="*45)
    check_python_version()
    check_dependencies()
    check_ports()
    check_directories()
    check_ollama()
    print("\n✅ Health check complete.\n")

if __name__ == "__main__":
    run_all()

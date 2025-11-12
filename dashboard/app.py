import sys
import os

# Ensure Reaper root is visible for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


import streamlit as st
import pandas as pd
import requests
import json
from core import storage, feedback
import matplotlib.pyplot as plt

# ─────────────────────────────
# ⚔️ Reaper Sentinel Dashboard v0.4
# ─────────────────────────────
st.set_page_config(page_title="Reaper Sentinel", page_icon="⚔️", layout="wide")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

def check_ollama_status():
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        return r.status_code == 200
    except:
        return False

ollama_connected = check_ollama_status()
status_emoji = "🟢" if ollama_connected else "🔴"
st.markdown(f"**Ollama:** {status_emoji} {'Connected' if ollama_connected else 'Disconnected'}")


st.title("⚔️ Reaper Sentinel Dashboard — v0.5 Memory Module")
st.markdown("### AI-Powered Security Log Analyzer with Memory & Feedback")
st.write("Upload your log file and let Reaper analyze it using AI. Each analysis will now be saved for future review.")

uploaded_file = st.file_uploader("📁 Upload Log File (JSON format)", type=["json"])

# Backend API URL
API_URL = "http://127.0.0.1:8000/analyze"

# ─────────────────────────────
# 🧠 Analyze New Log File
# ─────────────────────────────
if uploaded_file:
    logs = json.load(uploaded_file)
    st.success(f"Loaded {len(logs)} logs.")

    if st.button("🧠 Analyze Logs with Reaper"):
        with st.spinner("Reaper is thinking... ⚙️"):
            try:
                payload = {"logs": logs}
                response = requests.post(API_URL, json=payload)
                if response.status_code == 200:
                    data = response.json().get("results", [])
                    df = pd.DataFrame(data)

                    # Extract classification
                    def extract_class(severity_text):
                        if "Critical" in severity_text:
                            return "Critical"
                        elif "Medium" in severity_text:
                            return "Medium"
                        elif "Benign" in severity_text:
                            return "Benign"
                        else:
                            return "Unknown"

                    df["Severity"] = df["result"].apply(extract_class)
                    df["Color"] = df["Severity"].map({
                        "Critical": "🔴",
                        "Medium": "🟡",
                        "Benign": "🟢",
                        "Unknown": "⚫"
                    })

                    # Display results
                    st.markdown("### 🧾 AI Analysis Results")
                    st.dataframe(df[["Color", "Severity", "result"]], use_container_width=True)

                    # Download option (existing feature)
                    st.download_button(
                        label="💾 Download Results as JSON",
                        data=json.dumps(data, indent=2),
                        file_name="reaper_analysis.json",
                        mime="application/json"
                    )

                    # NEW IN v0.4: Save report to memory
                    saved_path = storage.save_report(data)
                    st.success(f"✅ Report saved to memory: {saved_path}")

                    # NEW IN v0.4: Summary analytics
                    st.markdown("### 📊 Analysis Summary")
                    critical = len(df[df["Severity"] == "Critical"])
                    medium = len(df[df["Severity"] == "Medium"])
                    benign = len(df[df["Severity"] == "Benign"])
                    total = len(df)

                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total Logs", total)
                    col2.metric("🟥 Critical", critical)
                    col3.metric("🟨 Medium", medium)
                    col4.metric("🟩 Benign", benign)

                    # Pie chart visualization
                    fig, ax = plt.subplots()
                    ax.pie(
                        [critical, medium, benign],
                        labels=["Critical", "Medium", "Benign"],
                        autopct="%1.1f%%",
                        startangle=90
                    )
                    st.pyplot(fig)

                    # NEW IN v0.4: Feedback capture
                    st.markdown("### 🧠 Feedback Section")
                    for i, row in df.iterrows():
                        col1, col2 = st.columns(2)
                        if col1.button(f"✅ Correct {i}"):
                            feedback.store_feedback({"entry": row.to_dict(), "feedback": "correct"})
                            st.toast(f"✅ Feedback saved for entry {i}")
                        if col2.button(f"❌ Incorrect {i}"):
                            feedback.store_feedback({"entry": row.to_dict(), "feedback": "incorrect"})
                            st.toast(f"❌ Feedback saved for entry {i}")
                else:
                    st.error(f"API returned status {response.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")

# ─────────────────────────────
# 📜 View Past Reports
# ─────────────────────────────
st.markdown("---")
st.subheader("📜 View Past Reports")

try:
    reports = storage.list_reports()
    if reports:
        selected = st.selectbox("Select a report to view", reports)
        if selected:
            old_data = storage.load_report(selected)
            st.json(old_data)
    else:
        st.info("No reports found yet. Upload and analyze a log file to create your first memory.")
except Exception as e:
    st.warning(f"Unable to load reports: {e}")

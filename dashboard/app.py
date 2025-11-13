import sys
import os

# Ensure Reaper root is visible for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import requests
import json
from core import storage
import matplotlib.pyplot as plt
import logging

# ─────────────────────────────
# 🪵 STREAMLIT DEBUG LOGGER
# ─────────────────────────────
LOG_PATH = "logs/dashboard_debug.log"
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

def debug(msg):
    logging.debug(msg)
    print("[DASHBOARD]", msg)

# ─────────────────────────────
# ⚔️ Reaper Sentinel Dashboard v0.6.1
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

tab1, tab2, tab3 = st.tabs(["🧠 Log Analyzer", "📚 Reaper Brain Memory", "💬 Feedback"])

# =====================================================================
# TAB 1 — ANALYZER
# =====================================================================
with tab1:
    st.title("⚔️ Reaper Sentinel Dashboard — v0.6.1 Intelligence Module")
    st.markdown("### AI-Powered Security Log Analyzer with Memory & Feedback")

    uploaded_file = st.file_uploader("📁 Upload Log File (JSON format)", type=["json"])

    API_URL = "http://127.0.0.1:8000/analyze"

    # INIT SESSION
    if "analysis_df" not in st.session_state:
        st.session_state.analysis_df = None

    # ANALYZE BUTTON
    if uploaded_file:
        logs = json.load(uploaded_file)
        st.success(f"Loaded {len(logs)} logs.")

        if st.button("🧠 Analyze Logs with Reaper"):
            with st.spinner("Reaper is analyzing... ⚙️"):
                try:
                    response = requests.post(API_URL, json={"logs": logs})

                    if response.status_code != 200:
                        st.error(f"API returned status {response.status_code}")
                        st.stop()

                    data = response.json().get("results", [])
                    df = pd.DataFrame(data)
                    df.index = range(1, len(df) + 1)

                    # ---------------------------------------------
                    # FIXED: Assign Severity BEFORE Color mapping
                    # ---------------------------------------------
                    def extract_class(text):
                        text = text.lower()
                        if "critical" in text: return "Critical"
                        if "high" in text: return "High"
                        if "medium" in text: return "Medium"
                        if "low" in text: return "Low"
                        if "benign" in text or "informational" in text or "safe" in text:
                            return "Informational"
                        return "Informational"

                    df["Severity"] = df["result"].apply(extract_class)

                    # Color mapping
                    df["Color"] = df["Severity"].map({
                        "Critical": "🔴",
                        "High": "🟧",
                        "Medium": "🟡",
                        "Low": "🟦",
                        "Informational": "⚫"
                    })

                    # Persist
                    st.session_state.analysis_df = df

                    # Save report
                    saved_path = storage.save_report(data)
                    st.success(f"Report saved to memory: {saved_path}")

                except Exception as e:
                    st.error(f"Error: {e}")
                    st.stop()

    # DISPLAY RESULTS
    df = st.session_state.analysis_df

    if df is None:
        st.info("Upload and analyze logs to begin.")
        st.stop()

    st.markdown("### 🧾 AI Analysis Results")
    st.dataframe(df[["Color", "Severity", "result"]], use_container_width=True)

    # =====================================================================
    # SUMMARY
    # =====================================================================
    st.markdown("### 📊 Analysis Summary")

    SEVERITY_LEVELS = ["Critical", "High", "Medium", "Low", "Informational"]

    counts = {lvl: (df["Severity"] == lvl).sum() for lvl in SEVERITY_LEVELS}
    total = len(df)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total Logs", total)
    col2.metric("Critical", counts["Critical"])
    col3.metric("High", counts["High"])
    col4.metric("Medium", counts["Medium"])
    col5.metric("Low", counts["Low"])
    col6.metric("Info", counts["Informational"])

    # PIE CHART
    fig, ax = plt.subplots()
    labels = [lvl for lvl in SEVERITY_LEVELS if counts[lvl] > 0]
    values = [counts[lvl] for lvl in labels]

    if values:
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
        st.pyplot(fig)
    else:
        st.info("No severity data yet.")

    # =====================================================================
    # INLINE FEEDBACK
    # =====================================================================
    st.markdown("### 💬 Provide Feedback to Train Reaper")

    if "feedback_status" not in st.session_state:
        st.session_state.feedback_status = ""

    with st.form("feedback_form_inline"):
        log_id = st.number_input("Select Log ID", min_value=1, max_value=len(df), step=1)
        feedback_choice = st.selectbox("Feedback", ["Accurate", "Inaccurate", "Needs Review"])
        reason = st.text_area("Reason (optional)")
        submitted = st.form_submit_button("Submit Feedback")

    if submitted:
        payload = {
            "log_id": int(log_id),
            "feedback": feedback_choice,
            "reason": reason
        }

        try:
            res = requests.post("http://127.0.0.1:8000/feedback", json=payload)
            if res.ok:
                st.session_state.feedback_status = f"Feedback recorded for Log #{log_id}!"
            else:
                st.session_state.feedback_status = f"Error: {res.text}"
        except Exception as e:
            st.session_state.feedback_status = f"Error: {e}"

    if st.session_state.feedback_status:
        st.info(st.session_state.feedback_status)


# =====================================================================
# TAB 2 — MEMORY VIEW
# =====================================================================
with tab2:
    st.markdown("### 🧠 Reaper Brain Memory")

    try:
        mem = requests.get("http://127.0.0.1:8000/memory").json()
        records = mem.get("records", [])

        if not records:
            st.info("No memory yet.")
        else:
            df_mem = pd.DataFrame(records)
            st.dataframe(df_mem, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading memory: {e}")


# =====================================================================
# TAB 3 — FEEDBACK ARCHIVE
# =====================================================================
with tab3:
    st.title("📚 Reaper Memory & Feedback Archive")

    try:
        mem = requests.get("http://127.0.0.1:8000/memory").json()
        records = mem.get("records", [])

        if not records:
            st.info("No logs analyzed yet.")
        else:
            df_arch = pd.DataFrame(records)
            df_arch.index = range(1, len(df_arch) + 1)

            st.dataframe(df_arch, use_container_width=True)

    except Exception as e:
        st.error("Unable to load memory.")


# =====================================================================
# REPORTS SECTION
# =====================================================================
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
        st.info("No reports found yet.")
except Exception as e:
    st.warning(f"Unable to load reports: {e}")

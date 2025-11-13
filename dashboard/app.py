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

# ───────────────────────────────────────────────
# STREAMLIT DEBUG LOGGER
# ───────────────────────────────────────────────
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

# ───────────────────────────────────────────────
# STREAMLIT LAYOUT
# ───────────────────────────────────────────────
st.set_page_config(page_title="Reaper Sentinel", page_icon="⚔️", layout="wide")

API_ANALYZE = "http://127.0.0.1:8000/analyze"
API_MEMORY = "http://127.0.0.1:8000/memory"
API_FEEDBACK = "http://127.0.0.1:8000/feedback"

# ───────────────────────────────────────────────
# TABS
# ───────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🧠 Log Analyzer", "📚 Reaper Brain Memory", "💬 Feedback"])

# ================================================================
# ======================== TAB 1 — ANALYZER =======================
# ================================================================
with tab1:
    st.title("⚔️ Reaper Sentinel Dashboard — v0.6.2 Intelligence Module")
    st.markdown("### AI-Powered Security Log Analyzer with Structured Output + Feedback Training")

    uploaded_file = st.file_uploader("📁 Upload Log File (JSON format)", type=["json"])

    # SESSION: store analysis results
    if "analysis_df" not in st.session_state:
        st.session_state.analysis_df = None

    if uploaded_file:
        logs = json.load(uploaded_file)
        st.success(f"Loaded {len(logs)} logs.")

        if st.button("🧠 Analyze Logs with Reaper"):
            with st.spinner("Reaper is analyzing… ⚙️"):
                try:
                    response = requests.post(API_ANALYZE, json={"logs": logs})
                    if not response.ok:
                        st.error(f"❌ API error: {response.status_code}")
                        st.stop()

                    results = response.json().get("results", [])

                    # Extract structured model output
                    rows = []
                    for item in results:
                        structured = item["result"]  # dict of SEVERITY, CATEGORY, ...
                        structured["log_id"] = item["log_id"]
                        rows.append(structured)

                    df = pd.DataFrame(rows)
                    df.index = df["log_id"]

                    # Store for session
                    st.session_state.analysis_df = df

                    # Save report
                    saved_path = storage.save_report(results)
                    st.success(f"💾 Report saved: {saved_path}")

                except Exception as e:
                    st.error(f"Error: {e}")
                    st.stop()

    # DISPLAY RESULTS
    df = st.session_state.get("analysis_df")

    if df is None or df.empty:
        st.info("Upload and analyze logs to begin.")
        st.stop()

    # --------------------------
    # FULL-WIDTH ANALYSIS TABLE
    # --------------------------
    st.markdown("### 🧾 AI Analysis Results (Structured)")
    st.dataframe(df, use_container_width=True)

    # --------------------------
    # SUMMARY ANALYTICS
    # --------------------------
    st.markdown("### 📊 Analysis Summary")

    SEVERITY_LEVELS = ["Critical", "High", "Medium", "Low", "Informational"]

    counts = {lvl: (df["SEVERITY"] == lvl).sum() for lvl in SEVERITY_LEVELS}
    total = len(df)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total Logs", total)
    col2.metric("Critical", counts["Critical"])
    col3.metric("High", counts["High"])
    col4.metric("Medium", counts["Medium"])
    col5.metric("Low", counts["Low"])
    col6.metric("Informational", counts["Informational"])

    # PIE CHART
    fig, ax = plt.subplots()
    valid_labels = [lvl for lvl in SEVERITY_LEVELS if counts[lvl] > 0]
    values = [counts[lvl] for lvl in valid_labels]

    if values:
        ax.pie(values, labels=valid_labels, autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
        st.pyplot(fig)

    # --------------------------
    # INLINE FEEDBACK
    # --------------------------
    st.markdown("### 💬 Train Reaper — Submit Feedback")

    if "feedback_status" not in st.session_state:
        st.session_state.feedback_status = ""

    with st.form("feedback_form_inline"):
        log_id = st.number_input("Select Log ID", min_value=1, max_value=len(df), step=1)
        fb_choice = st.selectbox("Feedback", ["Accurate", "Inaccurate", "Needs Review"])
        reason = st.text_area("Reason (optional)")

        submitted = st.form_submit_button("Submit Feedback")

    if submitted:
        try:
            payload = {
                "log_id": int(log_id),
                "feedback": fb_choice,
                "reason": reason
            }
            res = requests.post(API_FEEDBACK, json=payload)

            if res.ok:
                st.session_state.feedback_status = f"Feedback recorded for Log #{log_id}"
            else:
                st.session_state.feedback_status = f"Error: {res.text}"

        except Exception as e:
            st.session_state.feedback_status = f"Error: {e}"

    if st.session_state.feedback_status:
        st.info(st.session_state.feedback_status)


# ================================================================
# ======================== TAB 2 — MEMORY =========================
# ================================================================
with tab2:
    st.markdown("### 🧠 Reaper Brain Memory")

    try:
        mem = requests.get(API_MEMORY).json()

        if not mem.get("records"):
            st.info("🩶 No memory data yet.")
            st.stop()

        df_mem = pd.DataFrame(mem["records"])
        df_mem.index = range(1, len(df_mem) + 1)

        st.dataframe(df_mem, use_container_width=True)

    except Exception as e:
        st.error(f"Failed to load memory: {e}")


# ================================================================
# ======================== TAB 3 — ARCHIVE ========================
# ================================================================
with tab3:
    st.title("📚 Full Memory & Feedback Archive")

    try:
        mem = requests.get(API_MEMORY).json()
        records = mem.get("records", [])

        if not records:
            st.info("No records yet.")
            st.stop()

        df_arch = pd.DataFrame(records)
        df_arch.index = range(1, len(df_arch) + 1)

        st.dataframe(df_arch, use_container_width=True)

    except Exception as e:
        st.error(f"Unable to load archive: {e}")


# ================================================================
# ======================== REPORTS SECTION ========================
# ================================================================
st.markdown("---")
st.subheader("📜 View Past Reports")

try:
    reports = storage.list_reports()
    if reports:
        selected = st.selectbox("Select a report", reports)
        if selected:
            st.json(storage.load_report(selected))
    else:
        st.info("No reports found.")
except Exception as e:
    st.warning(f"Unable to load reports: {e}")

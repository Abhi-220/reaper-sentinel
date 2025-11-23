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
from typing import Any, Dict

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

def debug(msg: str):
    logging.debug(msg)
    print("[DASHBOARD]", msg)


# ───────────────────────────────────────────────
# CONFIG / API ENDPOINTS
# ───────────────────────────────────────────────
st.set_page_config(page_title="Reaper Sentinel", page_icon="⚔️", layout="wide")

API_ANALYZE = os.getenv("API_ANALYZE", "http://127.0.0.1:8000/analyze")
API_MEMORY = os.getenv("API_MEMORY", "http://127.0.0.1:8000/memory")
API_FEEDBACK = os.getenv("API_FEEDBACK", "http://127.0.0.1:8000/feedback")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


STRUCTURE_KEYS = [
    "SEVERITY", "CATEGORY", "MITRE_TACTIC", "MITRE_TECHNIQUE",
    "BEHAVIOR", "IOC", "CHAIN", "CONFIDENCE", "REASON"
]


# ───────────────────────────────────────────────
# PARSER
# ───────────────────────────────────────────────
def parse_result_to_structured(result: Any) -> Dict[str, Any]:
    out = {k: None for k in STRUCTURE_KEYS}
    out["RAW"] = None

    if isinstance(result, dict):
        for k, v in result.items():
            ku = k.strip().upper()
            if ku in out:
                out[ku] = v
        out["RAW"] = json.dumps(result, ensure_ascii=False)
        return out

    if isinstance(result, str):
        txt = result.strip()
        out["RAW"] = txt

        try:
            parsed = json.loads(txt)
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    ku = k.strip().upper()
                    if ku in out:
                        out[ku] = v
                return out
        except:
            pass

        for line in txt.splitlines():
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            ku = key.strip().upper()
            if ku in out:
                out[ku] = val.strip()
        return out

    out["RAW"] = str(result)
    return out


# ───────────────────────────────────────────────
# FIXED OLLAMA HEALTH CHECK
# ───────────────────────────────────────────────
def check_ollama_status() -> bool:
    try:
        url = f"{OLLAMA_HOST}/api/tags"
        debug(f"Checking Ollama health at {url}")
        r = requests.get(url, timeout=3)
        return r.ok
    except Exception as e:
        debug(f"Ollama health failed: {e}")
        return False


ollama_connected = check_ollama_status()
status_emoji = "🟢" if ollama_connected else "🔴"
st.markdown(f"**Ollama:** {status_emoji} {'Connected' if ollama_connected else 'Disconnected'}")


# ───────────────────────────────────────────────
# TABS
# ───────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🧠 Log Analyzer", "📚 Reaper Brain Memory", "💬 Feedback"])


# ================================================================
# TAB 1 — ANALYZER
# ================================================================
with tab1:
    st.title("⚔️ Reaper Sentinel Dashboard — v0.6.3 Intelligence Module")
    st.markdown("### AI-Powered Security Log Analyzer with Structured Output + Feedback Training")

    uploaded_file = st.file_uploader("📁 Upload Log File (JSON format)", type=["json"])

    # Initialize empty DF
    if "analysis_df" not in st.session_state:
        st.session_state.analysis_df = pd.DataFrame()

    if uploaded_file:
        try:
            logs = json.load(uploaded_file)
            st.success(f"Loaded {len(logs)} logs.")
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
            logs = None

        if logs:
            if st.button("🧠 Analyze Logs with Reaper"):
                with st.spinner("Analyzing…"):

                    response = requests.post(API_ANALYZE, json={"logs": logs}, timeout=300)
                    if not response.ok:
                        st.error(f"Error: {response.status_code}")
                        st.stop()

                    results = response.json().get("results", [])
                    rows = []

                    for item in results:
                        log_id = item.get("log_id")
                        parsed = parse_result_to_structured(item.get("result"))
                        parsed["log_id"] = int(log_id)
                        rows.append(parsed)

                    df_new = pd.DataFrame(rows)

                    # always enforce log_id as index
                    df_new = df_new.set_index("log_id", drop=False)

                    # Replace entire session with fresh batch (CRITICAL FIX)
                    st.session_state.analysis_df = df_new

                    # Save report
                    storage.save_report(results)
                    st.success("Report saved.")

    df = st.session_state.analysis_df

    if df.empty:
        st.info("Upload and analyze logs to begin.")
        st.stop()

    # Display results
    st.markdown("### 🧾 AI Analysis Results (Structured)")
    st.dataframe(df, use_container_width=True)

    # Summary
    st.markdown("### 📊 Summary")

    sev_levels = ["Critical", "High", "Medium", "Low", "Informational"]
    counts = {lvl: (df["SEVERITY"] == lvl).sum() for lvl in sev_levels}

    cols = st.columns(6)
    cols[0].metric("Total Logs", len(df))
    for i, lvl in enumerate(sev_levels):
        cols[i+1].metric(lvl, counts[lvl])

    # Pie chart
    fig, ax = plt.subplots()
    values = [counts[lvl] for lvl in sev_levels if counts[lvl] > 0]
    labels = [lvl for lvl in sev_levels if counts[lvl] > 0]

    if values:
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
        st.pyplot(fig)
    else:
        st.info("No data for visualization.")

    # Feedback
    st.markdown("### 💬 Submit Feedback")

    if "feedback_status" not in st.session_state:
        st.session_state.feedback_status = ""

    min_id, max_id = int(df.index.min()), int(df.index.max())

    with st.form("feedback_form"):
        target_id = st.number_input("Log ID", min_value=min_id, max_value=max_id, value=min_id)
        choice = st.selectbox("Feedback", ["Accurate", "Inaccurate", "Needs Review"])
        reason = st.text_area("Reason (optional)")
        submitted = st.form_submit_button("Submit")

    if submitted:
        payload = {"log_id": int(target_id), "feedback": choice, "reason": reason}
        try:
            r = requests.post(API_FEEDBACK, json=payload)
            if r.ok:
                st.session_state.feedback_status = f"Feedback saved for Log #{target_id}"
            else:
                st.session_state.feedback_status = f"Error: {r.status_code}"
        except Exception as e:
            st.session_state.feedback_status = f"Error: {e}"

    if st.session_state.feedback_status:
        st.info(st.session_state.feedback_status)


# ================================================================
# TAB 2 — MEMORY
# ================================================================
with tab2:
    st.markdown("### 🧠 Reaper Brain Memory")

    try:
        mem = requests.get(API_MEMORY, timeout=10).json()
        records = mem.get("records", [])
        if not records:
            st.info("Empty memory.")
            st.stop()
        df_mem = pd.DataFrame(records)
        st.dataframe(df_mem, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")


# ================================================================
# TAB 3 — ARCHIVE
# ================================================================
with tab3:
    st.markdown("### 📚 Full Memory Archive")
    try:
        mem = requests.get(API_MEMORY, timeout=10).json()
        df_arch = pd.DataFrame(mem.get("records", []))
        st.dataframe(df_arch, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")


# ================================================================
# REPORTS SECTION
# ================================================================
st.markdown("---")
st.subheader("📜 Past Reports")

try:
    reports = storage.list_reports()
    if reports:
        selected = st.selectbox("Select a report", reports)
        if selected:
            st.json(storage.load_report(selected))
    else:
        st.info("No reports stored.")
except Exception as e:
    st.warning(f"Error loading reports: {e}")

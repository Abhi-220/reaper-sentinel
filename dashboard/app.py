import streamlit as st
import pandas as pd
import requests
import json

# Reaper Sentinel Dashboard
st.set_page_config(page_title="Reaper Sentinel", page_icon="⚔️", layout="wide")

st.title("⚔️ Reaper Sentinel Dashboard")
st.markdown("### AI-Powered Security Log Analyzer")
st.write("Upload your log file and let Reaper analyze it using AI.")

uploaded_file = st.file_uploader("📁 Upload Log File (JSON format)", type=["json"])

# Backend API URL
API_URL = "http://127.0.0.1:8000/analyze"

if uploaded_file:
    logs = json.load(uploaded_file)
    st.success(f"Loaded {len(logs)} logs.")

    if st.button("🧠 Analyze Logs with Reaper"):
        with st.spinner("Reaper is thinking... ⚙️"):
            try:
                payload = {"logs": logs}
                response = requests.post(API_URL, json=payload)
                if response.status_code == 200:
                    data = response.json()["results"]
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

                    # Download option
                    st.download_button(
                        label="💾 Download Results as JSON",
                        data=json.dumps(data, indent=2),
                        file_name="reaper_analysis.json",
                        mime="application/json"
                    )
                else:
                    st.error(f"API returned status {response.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")

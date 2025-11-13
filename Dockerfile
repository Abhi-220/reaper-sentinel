# ⚔️ Reaper Sentinel Dockerfile (v0.6.2)
FROM python:3.12-slim

# ----------------------------
# System dependencies
# ----------------------------
RUN apt-get update && apt-get install -y \
    curl git bash build-essential \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------
# Create app directories
# ----------------------------
WORKDIR /app
RUN mkdir -p /app/data /app/logs

ENV PYTHONUNBUFFERED=1

# ----------------------------
# Install Python dependencies
# ----------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------
# Copy project
# ----------------------------
COPY . .

# ----------------------------
# Create non-root user (like old Dockerfile)
# ----------------------------
RUN adduser --disabled-password --gecos '' reaper || true
RUN chown -R reaper:reaper /app
USER reaper

# ----------------------------
# Expose FastAPI + Streamlit
# ----------------------------
EXPOSE 8000
EXPOSE 8501

# ----------------------------
# Start both backend + dashboard
# ----------------------------
CMD ["bash", "-c", "\
    uvicorn main:app --host 0.0.0.0 --port 8000 & \
    streamlit run dashboard/app.py --server.port=8501 --server.address=0.0.0.0 \
"]

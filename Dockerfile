# ⚔️ Reaper Sentinel Dockerfile (v0.5)
# Base lightweight Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Prevent Python from buffering stdout (important for live logs)
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into container
COPY . /app

# Expose ports for FastAPI and Streamlit
EXPOSE 8000 8501

# Default command to run Reaper
CMD ["python", "run_reaper.py"]

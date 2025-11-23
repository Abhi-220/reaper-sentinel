# 🐳 Deployment Guide (Docker + Compose)

## 1. Build Image
```bash
docker build -t reaper-sentinel .
```

## 2. Run
```bash
docker-compose up -d
```

Services:
- FastAPI → `localhost:8000`
- Dashboard → `localhost:8501`

# 🛠️ Developer Guide

## 1. Folder Structure
(Explained file-by-file)

## 2. How To Modify Analyzer
- Adjust prompt in `analyzer.py`
- Modify parsing logic
- Add new fields to memory

## 3. Extending the UI
- All dashboard logic in `dashboard/app.py`

## 4. Adding New Model
Set via:
```
export MODEL_NAME="llama3"
```

## 5. Logging
- Analyzer logs → `logs/reaper_analyzer.log`
- Dashboard logs → `logs/dashboard_debug.log`

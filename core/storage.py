import json, os, datetime

REPORT_DIR = "data/reports"

def save_report(data):
    os.makedirs(REPORT_DIR, exist_ok=True)
    filename = f"report_{datetime.date.today()}.json"
    filepath = os.path.join(REPORT_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    return filepath

def list_reports():
    os.makedirs(REPORT_DIR, exist_ok=True)
    return sorted(os.listdir(REPORT_DIR))

def load_report(filename):
    filepath = os.path.join(REPORT_DIR, filename)
    with open(filepath) as f:
        return json.load(f)

import json, os

FEEDBACK_FILE = "data/feedback.json"

def store_feedback(entry):
    os.makedirs("data", exist_ok=True)
    feedback = []
    if os.path.exists(FEEDBACK_FILE):
        feedback = json.load(open(FEEDBACK_FILE))
    feedback.append(entry)
    json.dump(feedback, open(FEEDBACK_FILE, "w"), indent=2)

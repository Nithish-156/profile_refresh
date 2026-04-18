"""
db.py
Logs profile refresh results to a local JSON file (logs/runs.json).
This file is committed back to the repo by the GitHub Actions workflow
so the dashboard can read it.
"""
import json
import os
from datetime import datetime, timezone

LOG_FILE = "logs/runs.json"
MAX_RECORDS = 200  # keep last N records

def init_profile_log():
    os.makedirs("logs", exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump([], f)

def log_profile_refresh(status: str, message: str):
    """Append a run record. status: 'success' | 'failed'"""
    init_profile_log()
    with open(LOG_FILE, "r") as f:
        records = json.load(f)

    records.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "message": message,
    })

    # Trim to last MAX_RECORDS
    records = records[-MAX_RECORDS:]

    with open(LOG_FILE, "w") as f:
        json.dump(records, f, indent=2)

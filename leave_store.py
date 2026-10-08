import os
from datetime import datetime

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REQ_FILE = os.path.join(BASE_DIR, "requests.csv")

ANNUAL_LEAVE_DAYS = 18  # change if your institution uses a different number

COLUMNS = [
    "id", "submitted_at", "employee", "email", "leave_type",
    "start_date", "end_date", "days", "reason", "urgent",
    "ai_recommendation", "ai_confidence", "status", "decided_at", "admin_note",
]
STR_COLS = [
    "submitted_at", "employee", "email", "leave_type", "start_date", "end_date",
    "reason", "ai_recommendation", "status", "decided_at", "admin_note",
]


def load_requests():
    """Return all leave requests as a DataFrame (empty if none yet)."""
    if not os.path.exists(REQ_FILE):
        return pd.DataFrame(columns=COLUMNS)
    try:
        df = pd.read_csv(REQ_FILE)
    except Exception:
        return pd.DataFrame(columns=COLUMNS)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS].copy()
    for col in STR_COLS:
        df[col] = df[col].fillna("").astype(str)
    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    df["days"] = pd.to_numeric(df["days"], errors="coerce").fillna(0).astype(int)
    return df


def add_request(employee, email, leave_type, start_date, end_date, days,
                reason, urgent, ai_recommendation, ai_confidence):
    """Save a new request. Status is ALWAYS 'Pending' (never auto-approved)."""
    df = load_requests()
    new_id = 1 if df.empty else int(df["id"].max()) + 1
    row = {
        "id": new_id,
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "employee": employee.strip(),
        "email": (email or "").strip(),
        "leave_type": leave_type,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "days": int(days),
        "reason": reason.strip(),
        "urgent": int(bool(urgent)),
        "ai_recommendation": ai_recommendation,
        "ai_confidence": round(float(ai_confidence), 2),
        "status": "Pending",
        "decided_at": "",
        "admin_note": "",
    }
    new_df = pd.DataFrame([row]) if df.empty else pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    new_df.to_csv(REQ_FILE, index=False)
    return new_id


def set_status(req_id, status, note=""):
    """Used by the administrator only: set Approved or Rejected."""
    df = load_requests()
    mask = df["id"] == int(req_id)
    df.loc[mask, "status"] = status
    df.loc[mask, "decided_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    df.loc[mask, "admin_note"] = note
    df.to_csv(REQ_FILE, index=False)


def get_leave_balance(employee):
    """Annual leave days left = ANNUAL_LEAVE_DAYS minus approved annual leave."""
    df = load_requests()
    if df.empty:
        return ANNUAL_LEAVE_DAYS
    mine = df[
        (df["employee"].str.strip().str.lower() == employee.strip().lower())
        & (df["leave_type"] == "Annual Leave")
        & (df["status"] == "Approved")
    ]
    return max(0, ANNUAL_LEAVE_DAYS - int(mine["days"].sum()))


def count_staff_on_leave(start_date, end_date):
    """How many APPROVED requests overlap the given period."""
    df = load_requests()
    df = df[df["status"] == "Approved"]
    if df.empty:
        return 0
    s = pd.to_datetime(df["start_date"], errors="coerce")
    e = pd.to_datetime(df["end_date"], errors="coerce")
    overlap = (s <= pd.Timestamp(end_date)) & (e >= pd.Timestamp(start_date))
    return int(overlap.sum())
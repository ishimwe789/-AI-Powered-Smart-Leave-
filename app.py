import os
from datetime import date, timedelta

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.tree import DecisionTreeClassifier

from admin_dashboard import show_admin_dashboard
from email_service import notify_submission
from leave_store import (
    ANNUAL_LEAVE_DAYS,
    add_request,
    count_staff_on_leave,
    get_leave_balance,
    load_requests,
)

st.set_page_config(
    page_title="AI-Powered Smart Leave Management System",
    page_icon="🤖",
    layout="wide",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.csv")
FEATURES = ["days_requested", "leave_balance", "staff_on_leave", "urgent"]
LEAVE_TYPES = [
    "Annual Leave", "Sick Leave", "Maternity/Paternity Leave",
    "Study Leave", "Compassionate Leave", "Other",
]


# ---------------------------------------------------------------- AI model
@st.cache_resource
def train_model():
    if not os.path.exists(DATA_FILE):
        return None, "data.csv was not found. Please make sure data.csv is inside the project folder."
    df = pd.read_csv(DATA_FILE)
    missing = [c for c in FEATURES + ["decision"] if c not in df.columns]
    if missing:
        return None, f"data.csv is missing columns: {', '.join(missing)}"
    model = DecisionTreeClassifier(max_depth=4, random_state=42)
    model.fit(df[FEATURES], df["decision"])
    return model, None


def ai_recommend(model, days, balance, staff, urgent, leave_type):
    # Only Annual Leave uses up the annual balance; other types are treated as "balance OK".
    model_balance = balance if leave_type == "Annual Leave" else max(balance, days)
    X = pd.DataFrame([[days, model_balance, staff, int(urgent)]], columns=FEATURES)
    decision = model.predict(X)[0]
    confidence = float(model.predict_proba(X).max())
    return decision, confidence


def explain(days, balance, staff, urgent, leave_type):
    notes = []
    if leave_type == "Annual Leave":
        if days > balance:
            notes.append(f"Requested {days} days but only {balance} annual leave days remain.")
        else:
            notes.append(f"{balance} annual leave days available, {days} requested.")
    if staff >= 4:
        notes.append(f"{staff} colleagues are already approved on leave in this period (high workload risk).")
    elif staff > 0:
        notes.append(f"{staff} colleague(s) already approved on leave in this period.")
    else:
        notes.append("Nobody else is approved on leave in this period.")
    if urgent:
        notes.append("Request marked urgent.")
    return notes


# ---------------------------------------------------------------- Sidebar
st.sidebar.title("📋 System Menu")
page = st.sidebar.radio("Go to", ["Employee Page", "Administrator Dashboard"])
st.sidebar.markdown("---")
st.sidebar.caption("🏫 RP Ngoma College")
st.sidebar.caption("💻 Information Technology")
st.sidebar.caption("🤖 AI Decision Support")

if page == "Administrator Dashboard":
    show_admin_dashboard()
    st.stop()  # nothing below runs for the admin page

# ---------------------------------------------------------------- Employee page
st.title("🤖 AI-Powered Smart Leave Management System")
st.subheader("Case Study: RP Ngoma College")
st.write(
    "An intelligent leave management system that uses Artificial Intelligence "
    "to provide decision support for employee leave requests."
)
st.info(
    "The AI only gives a **recommendation**. Every request stays **Pending** "
    "until the administrator approves or rejects it."
)

model, model_error = train_model()
if model_error:
    st.error(model_error)
    st.stop()

tab_request, tab_track = st.tabs(["📝 Request Leave", "🔎 Track My Request"])

with tab_request:
    with st.form("leave_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Full name")
        email = c2.text_input("Email (to receive updates, optional)")
        leave_type = c1.selectbox("Leave type", LEAVE_TYPES)
        urgent = c2.checkbox("This request is urgent")
        start_date = c1.date_input("Start date", value=date.today() + timedelta(days=1))
        end_date = c2.date_input("End date", value=date.today() + timedelta(days=1))
        reason = st.text_area("Reason for leave")
        submitted = st.form_submit_button("Submit Leave Request")

    if submitted:
        errors = []
        if not name.strip():
            errors.append("Please enter your full name.")
        if not reason.strip():
            errors.append("Please enter the reason for leave.")
        if end_date < start_date:
            errors.append("End date cannot be before the start date.")

        days = 0
        if not errors:
            days = int(np.busday_count(start_date, end_date + timedelta(days=1)))
            if days == 0:
                errors.append("The selected dates contain no working days (Monday to Friday).")

        if errors:
            for e in errors:
                st.error(e)
        else:
            balance = get_leave_balance(name)
            staff = count_staff_on_leave(start_date, end_date)
            decision, confidence = ai_recommend(model, days, balance, staff, urgent, leave_type)

            req_id = add_request(
                name, email, leave_type, start_date, end_date, days,
                reason, urgent, f"AI suggests: {decision}", confidence,
            )

            st.success(
                f"Request #{req_id} submitted. Status: **Pending administrator approval**. "
                "Keep your request number to track it."
            )
            st.markdown(f"### 🤖 AI Recommendation (advice only): **{decision}**")
            st.progress(confidence, text=f"Confidence: {confidence:.0%}")
            for note in explain(days, balance, staff, urgent, leave_type):
                st.write(f"- {note}")

            if email.strip():
                ok, info = notify_submission(name, email, req_id, leave_type, start_date, end_date, days)
                (st.caption if ok else st.warning)(info)

with tab_track:
    st.write(f"Annual leave allowance: **{ANNUAL_LEAVE_DAYS} working days** per year.")
    query = st.text_input("Enter your full name or request number")
    if query.strip():
        df = load_requests()
        if query.strip().isdigit():
            mine = df[df["id"] == int(query.strip())]
        else:
            mine = df[df["employee"].str.strip().str.lower() == query.strip().lower()]
        if mine.empty:
            st.warning("No request found.")
        else:
            st.dataframe(
                mine[["id", "leave_type", "start_date", "end_date", "days", "status", "decided_at", "admin_note"]]
            )
            if not query.strip().isdigit():
                st.info(f"Annual leave days remaining: **{get_leave_balance(query)}**")

st.divider()
st.markdown("### ℹ️ System Limitation")
st.write(
    "The current system uses a small sample dataset for demonstration. Real institutional "
    "data would be required to develop a more reliable real-world system."
)
st.caption("AI-Powered Smart Leave Management System | RP Ngoma College | Information Technology")
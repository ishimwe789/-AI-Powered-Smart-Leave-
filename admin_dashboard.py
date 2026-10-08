import streamlit as st

from email_service import notify_decision
from leave_store import load_requests, set_status


def _decide(row, status, note):
    """Apply the administrator's decision and notify the employee by email."""
    rid = int(row["id"])
    set_status(rid, status, note)
    msg = f"Request #{rid} ({row['employee']}) was {status.lower()}."
    if row["email"]:
        ok, info = notify_decision(row["employee"], row["email"], rid, status, note)
        msg += f" {info}"
    else:
        msg += " (No employee email on file.)"
    st.session_state["flash"] = msg
    st.rerun()


def show_admin_dashboard():
    st.title("🛡️ Administrator Dashboard")

    # ---------- Login ----------
    if not st.session_state.get("is_admin", False):
        st.info("Administrator access only.")
        pwd = st.text_input("Admin password", type="password")
        if st.button("Login"):
            try:
                correct = st.secrets["ADMIN_PASSWORD"]
            except Exception:
                st.error("ADMIN_PASSWORD is missing in .streamlit/secrets.toml")
                return
            if pwd == correct:
                st.session_state["is_admin"] = True
                st.rerun()
            else:
                st.error("Wrong password.")
        return

    if st.sidebar.button("🚪 Logout"):
        st.session_state["is_admin"] = False
        st.rerun()

    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))

    df = load_requests()

    # ---------- Summary ----------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", len(df))
    c2.metric("Pending", int((df["status"] == "Pending").sum()))
    c3.metric("Approved", int((df["status"] == "Approved").sum()))
    c4.metric("Rejected", int((df["status"] == "Rejected").sum()))

    st.divider()

    # ---------- Pending requests ----------
    st.subheader("Pending Requests")
    pending = df[df["status"] == "Pending"]
    if pending.empty:
        st.info("No pending requests.")

    for _, r in pending.iterrows():
        rid = int(r["id"])
        with st.container(border=True):
            urgent_tag = " 🔴 URGENT" if int(r["urgent"] or 0) else ""
            st.markdown(
                f"**#{rid} - {r['employee']}**{urgent_tag}  \n"
                f"{r['leave_type']} | {r['start_date']} to {r['end_date']} | {r['days']} working day(s)"
            )
            st.write(f"Reason: {r['reason']}")
            st.caption(
                f"🤖 AI recommendation (advice only): {r['ai_recommendation']} "
                f"(confidence {r['ai_confidence']})"
            )
            note = st.text_input("Note to employee (optional)", key=f"note_{rid}")
            col_a, col_b, _ = st.columns([1, 1, 4])
            if col_a.button("✅ Approve", key=f"approve_{rid}"):
                _decide(r, "Approved", note)
            if col_b.button("❌ Reject", key=f"reject_{rid}"):
                _decide(r, "Rejected", note)

    st.divider()

    # ---------- History ----------
    st.subheader("All Requests (History)")
    st.dataframe(df)
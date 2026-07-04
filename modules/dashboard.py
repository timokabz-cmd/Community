import streamlit as st
from datetime import date
from database import get_db_connection
from modules.collections import get_messages
from modules.reports import get_portfolio_at_risk
from modules.loans import get_upcoming_installments
from modules.theme import money_column

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected. Set up a SACCO Profile first.")
        return

    conn = get_db_connection()
    total_customers = conn.execute("SELECT COUNT(*) FROM customers WHERE sacco_id = ?", (sacco_id,)).fetchone()[0]
    members = conn.execute("SELECT COUNT(*) FROM customers WHERE sacco_id = ? AND member_type='Member'", (sacco_id,)).fetchone()[0]
    active_loans = conn.execute("SELECT COUNT(*) FROM loans WHERE sacco_id = ? AND status='Active'", (sacco_id,)).fetchone()[0]
    outstanding = conn.execute("SELECT COALESCE(SUM(balance),0) FROM loans WHERE sacco_id = ? AND status='Active'", (sacco_id,)).fetchone()[0]
    collected_total = conn.execute(
        """SELECT COALESCE(SUM(repayments.amount),0) FROM repayments
           JOIN loans ON repayments.loan_id = loans.id WHERE loans.sacco_id = ?""",
        (sacco_id,)
    ).fetchone()[0]
    total_savings = conn.execute("SELECT COALESCE(SUM(balance),0) FROM savings_accounts WHERE sacco_id = ?", (sacco_id,)).fetchone()[0]

    today_str = date.today().strftime('%Y-%m-%d')
    expected_today = conn.execute(
        """SELECT COALESCE(SUM(loan_schedule.due_amount - loan_schedule.paid_amount),0) FROM loan_schedule
           JOIN loans ON loan_schedule.loan_id = loans.id
           WHERE loan_schedule.due_date = ? AND loan_schedule.status != 'Paid' AND loans.sacco_id = ?""",
        (today_str, sacco_id)
    ).fetchone()[0]
    collected_today = conn.execute(
        """SELECT COALESCE(SUM(repayments.amount),0) FROM repayments
           JOIN loans ON repayments.loan_id = loans.id
           WHERE repayments.date LIKE ? AND loans.sacco_id = ?""",
        (today_str + '%', sacco_id)
    ).fetchone()[0]
    conn.close()

    at_risk_count = len(get_portfolio_at_risk(sacco_id))

    st.write("#### Today's Snapshot")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Expected Today", f"UGX {expected_today:,.0f}")
    col2.metric("Collected Today", f"UGX {collected_today:,.0f}")
    col3.metric("High-Risk Loans", at_risk_count)
    col4.metric("Cash Collected (All-Time)", f"UGX {collected_total:,.0f}")

    st.write("#### Business Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Customers", total_customers, delta=f"{members} members", delta_color="off")
    col2.metric("Active Loans", active_loans)
    col3.metric("Outstanding Loans", f"UGX {outstanding:,.0f}")
    col4.metric("Total Savings Held", f"UGX {total_savings:,.0f}")

    st.write("#### 🔔 Upcoming Repayments (next 7 days)")
    upcoming = get_upcoming_installments(sacco_id, days=7)
    if upcoming:
        st.dataframe(
            [{"Due Date": u['due_date'], "Customer": u['customer_name'], "Phone": u['customer_phone'],
              "Amount Due": u['due_amount'] - u['paid_amount'], "Loan ID": u['loan_id']} for u in upcoming],
            column_config={"Amount Due": money_column()},
            use_container_width=True
        )
    else:
        st.info("No repayments due in the next 7 days.")

    st.write("#### Recent Client Messages")
    messages = get_messages(sacco_id, limit=5)
    if not messages:
        st.info("No messages sent yet. Record a repayment in Collections to see auto-generated confirmations here.")
    for m in messages:
        st.write(f"**{m['customer_name']}** — {m['sent_at']}")
        st.caption(m['message'])

import streamlit as st
from datetime import date
from database import get_db_connection
from modules.collections import get_messages
from modules.reports import get_portfolio_at_risk
from modules.loans import get_upcoming_installments

def render():
    conn = get_db_connection()
    total_customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    members = conn.execute("SELECT COUNT(*) FROM customers WHERE member_type='Member'").fetchone()[0]
    active_loans = conn.execute("SELECT COUNT(*) FROM loans WHERE status='Active'").fetchone()[0]
    outstanding = conn.execute("SELECT COALESCE(SUM(balance),0) FROM loans WHERE status='Active'").fetchone()[0]
    collected_total = conn.execute("SELECT COALESCE(SUM(amount),0) FROM repayments").fetchone()[0]
    total_savings = conn.execute("SELECT COALESCE(SUM(balance),0) FROM savings_accounts").fetchone()[0]

    today_str = date.today().strftime('%Y-%m-%d')
    expected_today = conn.execute(
        "SELECT COALESCE(SUM(due_amount - paid_amount),0) FROM loan_schedule WHERE due_date = ? AND status != 'Paid'",
        (today_str,)
    ).fetchone()[0]
    collected_today = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM repayments WHERE date LIKE ?",
        (today_str + '%',)
    ).fetchone()[0]
    conn.close()

    at_risk_count = len(get_portfolio_at_risk())

    st.write("#### Today's Snapshot")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Expected Today", f"UGX {expected_today:,.0f}")
    col2.metric("Collected Today", f"UGX {collected_today:,.0f}")
    col3.metric("High-Risk Loans", at_risk_count)
    col4.metric("Cash Collected (All-Time)", f"UGX {collected_total:,.0f}")

    st.write("#### Business Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Customers", f"{total_customers} ({members} members)")
    col2.metric("Active Loans", active_loans)
    col3.metric("Outstanding Loans", f"UGX {outstanding:,.0f}")
    col4.metric("Total Savings Held", f"UGX {total_savings:,.0f}")

    st.write("#### ðŸ”” Upcoming Repayments (next 7 days)")
    upcoming = get_upcoming_installments(days=7)
    if upcoming:
        st.dataframe(
            [{"Due Date": u['due_date'], "Customer": u['customer_name'], "Phone": u['customer_phone'],
              "Amount Due": u['due_amount'] - u['paid_amount'], "Loan ID": u['loan_id']} for u in upcoming],
            use_container_width=True
        )
    else:
        st.info("No repayments due in the next 7 days.")

    st.write("#### Recent Client Messages")
    messages = get_messages(limit=5)
    if not messages:
        st.info("No messages sent yet. Record a repayment in Collections to see auto-generated confirmations here.")
    for m in messages:
        st.write(f"**{m['customer_name']}** â€” {m['sent_at']}")
        st.caption(m['message'])

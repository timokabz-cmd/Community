import streamlit as st
from datetime import date
from database import get_db_connection
from modules.loans import get_loans
from modules.collections import get_messages

def get_portfolio_at_risk():
    """Returns loans with at least one overdue, unpaid installment."""
    conn = get_db_connection()
    today_str = date.today().strftime('%Y-%m-%d')
    rows = conn.execute(
        """SELECT DISTINCT loans.id, customers.name as customer_name, loans.balance FROM loan_schedule JOIN loans ON loan_schedule.loan_id = loans.id JOIN customers ON loans.customer_id = customers.id WHERE loan_schedule.status != 'Paid' AND loan_schedule.due_date < ? AND loans.status = 'Active'""",
        (today_str,)
    ).fetchall()
    conn.close()
    return rows

def render():
    st.write("#### Portfolio Summary")
    loans = get_loans()
    active = [l for l in loans if l['status'] == 'Active']
    closed = [l for l in loans if l['status'] == 'Closed']
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Loans Issued", len(loans))
    col2.metric("Active Loans", len(active))
    col3.metric("Closed Loans", len(closed))

    if active:
        outstanding_total = sum(l['balance'] for l in active)
        st.write(f"**Total Outstanding Portfolio:** UGX {outstanding_total:,.0f}")

    st.write("#### ⚠️ Portfolio at Risk (overdue installments)")
    at_risk = get_portfolio_at_risk()
    if at_risk:
        st.dataframe(
            [{"Loan ID": r['id'], "Customer": r['customer_name'], "Balance": r['balance']} for r in at_risk],
            use_container_width=True
        )
    else:
        st.success("No overdue installments right now.")

    st.write("#### Client Messages Log")
    messages = get_messages(limit=50)
    if messages:
        st.dataframe(
            [{"Date": m['sent_at'], "Customer": m['customer_name'], "Message": m['message']} for m in messages],
            use_container_width=True
        )
    else:
        st.info("No messages sent yet.")

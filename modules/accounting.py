import streamlit as st
from datetime import datetime
from database import get_db_connection

def post_double_entry(account_debit, account_credit, amount, description, reference=None, txn_date=None):
    """Posts a balanced debit/credit pair to the ledger for any transaction. txn_date (a date/datetime) lets seeded or backdated transactions carry a realistic historical timestamp instead of always using 'now'."""
    conn = get_db_connection()
    today = txn_date.strftime('%Y-%m-%d %H:%M') if txn_date else datetime.now().strftime('%Y-%m-%d %H:%M')
    conn.execute(
        "INSERT INTO ledger (date, account, debit, credit, description, reference) VALUES (?,?,?,?,?,?)",
        (today, account_debit, amount, 0, description, reference)
    )
    conn.execute(
        "INSERT INTO ledger (date, account, debit, credit, description, reference) VALUES (?,?,?,?,?,?)",
        (today, account_credit, 0, amount, description, reference)
    )
    conn.commit()
    conn.close()

def get_ledger(limit=300):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM ledger ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows

def get_trial_balance():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT account, SUM(debit) as total_debit, SUM(credit) as total_credit FROM ledger GROUP BY account ORDER BY account"
    ).fetchall()
    conn.close()
    return rows

def render():
    st.write("#### Double-Entry Ledger")
    st.caption("Every loan disbursement, repayment, and savings transaction posts a balanced debit/credit entry here automatically.")
    ledger = get_ledger()
    if ledger:
        st.dataframe(
            [{"Date": l['date'], "Account": l['account'], "Debit": l['debit'],
              "Credit": l['credit'], "Description": l['description'], "Reference": l['reference']} for l in ledger],
            use_container_width=True
        )
    else:
        st.info("No ledger entries yet.")

    st.write("#### Trial Balance")
    tb = get_trial_balance()
    if tb:
        total_debit = sum(row['total_debit'] for row in tb)
        total_credit = sum(row['total_credit'] for row in tb)
        st.dataframe(
            [{"Account": row['account'], "Total Debit": row['total_debit'], "Total Credit": row['total_credit']} for row in tb],
            use_container_width=True
        )
        st.write(f"**Total Debits: UGX {total_debit:,.0f} | Total Credits: UGX {total_credit:,.0f}**")
        if abs(total_debit - total_credit) < 0.01:
            st.success("Books are balanced ✅")
        else:
            st.error("Books are out of balance — check ledger entries.")
    else:
        st.info("No transactions posted yet.")

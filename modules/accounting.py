import streamlit as st
from datetime import datetime
from database import get_db_connection
from modules.theme import money_column

def post_double_entry(account_debit, account_credit, amount, description, reference=None, sacco_id=None):
    conn = get_db_connection()
    cur  = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    cur.execute(
        "INSERT INTO ledger (date, account, debit, credit, description, reference, sacco_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (today, account_debit, amount, 0, description, reference, sacco_id)
    )
    cur.execute(
        "INSERT INTO ledger (date, account, debit, credit, description, reference, sacco_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (today, account_credit, 0, amount, description, reference, sacco_id)
    )
    conn.commit()
    cur.close()
    conn.close()

def get_ledger(sacco_id, limit=300):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM ledger WHERE sacco_id = %s ORDER BY id DESC LIMIT %s",
        (sacco_id, limit)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_trial_balance(sacco_id):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute(
        """SELECT account, SUM(debit) AS total_debit, SUM(credit) AS total_credit
           FROM ledger WHERE sacco_id = %s
           GROUP BY account ORDER BY account""",
        (sacco_id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected. Set up a SACCO Profile first.")
        return

    st.write("#### Double-Entry Ledger")
    st.caption("Every loan disbursement, repayment, and savings transaction posts a balanced debit/credit entry here automatically.")
    ledger = get_ledger(sacco_id)
    if ledger:
        st.dataframe(
            [{"Date": l['date'], "Account": l['account'], "Debit": l['debit'],
              "Credit": l['credit'], "Description": l['description'], "Reference": l['reference']}
             for l in ledger],
            column_config={"Debit": money_column(), "Credit": money_column()},
            use_container_width=True
        )
    else:
        st.info("No ledger entries yet.")

    st.write("#### Trial Balance")
    tb = get_trial_balance(sacco_id)
    if tb:
        total_debit  = sum(row['total_debit']  for row in tb)
        total_credit = sum(row['total_credit'] for row in tb)
        st.dataframe(
            [{"Account": row['account'], "Total Debit": row['total_debit'],
              "Total Credit": row['total_credit']} for row in tb],
            column_config={"Total Debit": money_column(), "Total Credit": money_column()},
            use_container_width=True
        )
        st.write(f"**Total Debits: UGX {total_debit:,.0f} | Total Credits: UGX {total_credit:,.0f}**")
        if abs(total_debit - total_credit) < 0.01:
            st.success("Books are balanced ✅")
        else:
            st.error("Books are out of balance — check ledger entries.")
    else:
        st.info("No transactions posted yet.")

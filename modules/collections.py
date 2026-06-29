import streamlit as st
import secrets
from datetime import datetime
from database import get_db_connection
from modules.accounting import post_double_entry
from modules.loans import get_loans, get_loan, allocate_payment

def log_message(customer_id, message, sent_at=None):
    conn = get_db_connection()
    timestamp = sent_at.strftime('%Y-%m-%d %H:%M') if sent_at else datetime.now().strftime('%Y-%m-%d %H:%M')
    conn.execute(
        "INSERT INTO messages_log (customer_id, message, sent_at) VALUES (?,?,?)",
        (customer_id, message, timestamp)
    )
    conn.commit()
    conn.close()

def get_messages(limit=20):
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT messages_log.*, customers.name as customer_name FROM messages_log JOIN customers ON messages_log.customer_id = customers.id ORDER BY messages_log.id DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return rows

def record_repayment(loan_id, amount, method="Mobile Money", reference=None, txn_date=None):
    """Simulates an automated mobile money webhook: applies the payment to the loan and its schedule, posts the ledger entry, and fires an instant client confirmation â€” with no manual staff handling in between."""
    loan = get_loan(loan_id)
    if loan is None:
        return None, "Loan not found"
    if amount <= 0:
        return None, "Amount must be greater than zero"

    reference = reference or f"MM-{secrets.token_hex(4).upper()}"
    today = txn_date.strftime('%Y-%m-%d %H:%M') if txn_date else datetime.now().strftime('%Y-%m-%d %H:%M')

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO repayments (loan_id, amount, method, reference, date) VALUES (?,?,?,?,?)",
        (loan_id, amount, method, reference, today)
    )
    new_balance = max(round(loan['balance'] - amount, 2), 0)
    new_status = 'Closed' if new_balance <= 0 else 'Active'
    conn.execute("UPDATE loans SET balance = ?, status = ? WHERE id = ?", (new_balance, new_status, loan_id))
    conn.commit()
    conn.close()

    allocate_payment(loan_id, amount)
    post_double_entry("Cash/Bank", "Loans Receivable", amount, f"Repayment for loan #{loan_id}", reference, txn_date=txn_date)

    message = (
        f"Dear {loan['customer_name']}, we have received your payment of "
        f"UGX {amount:,.0f} via {method} (Ref: {reference}). "
        f"Your new loan balance is UGX {new_balance:,.0f}. Thank you."
    )
    log_message(loan['customer_id'], message, sent_at=txn_date)
    return new_balance, message

def get_repayments(limit=20):
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT repayments.*, customers.name as customer_name FROM repayments JOIN loans ON repayments.loan_id = loans.id JOIN customers ON loans.customer_id = customers.id ORDER BY repayments.id DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return rows

def render():
    st.write("#### ðŸ“² Mobile Money Webhook Simulation")
    st.caption(
        "Simulates an incoming mobile money payment notification (MTN/Airtel). Submitting this form "
        "applies the payment, updates the repayment schedule and ledger, and sends a confirmation "
        "message automatically â€” no staff handling in between."
    )
    active_loans = get_loans(status='Active')
    if not active_loans:
        st.info("No active loans to collect against.")
    else:
        with st.form("webhook_form", clear_on_submit=True):
            loan_map = {f"Loan #{l['id']} â€” {l['customer_name']} (Bal: {l['balance']:,.0f})": l['id'] for l in active_loans}
            loan_choice = st.selectbox("Loan", list(loan_map.keys()))
            amount = st.number_input("Amount received (UGX)", min_value=0.0, step=1000.0)
            method = st.selectbox("Channel", ["MTN MoMo", "Airtel Money", "Bank Transfer", "Cash"])
            submitted = st.form_submit_button("Simulate Webhook / Record Payment")
            if submitted:
                if amount <= 0:
                    st.error("Amount must be greater than zero.")
                else:
                    loan_id = loan_map[loan_choice]
                    new_balance, message = record_repayment(loan_id, amount, method)
                    st.success(f"Payment processed automatically. New balance: UGX {new_balance:,.0f}")
                    st.write("**Auto-generated client confirmation:**")
                    st.code(message, language=None)

    st.write("#### Recent Repayments")
    repayments = get_repayments(limit=20)
    if repayments:
        st.dataframe(
            [{"Date": r['date'], "Customer": r['customer_name'], "Loan ID": r['loan_id'],
              "Amount": r['amount'], "Method": r['method'], "Reference": r['reference']} for r in repayments],
            use_container_width=True
        )
    else:
        st.info("No repayments recorded yet.")

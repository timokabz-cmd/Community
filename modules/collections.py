import streamlit as st
import secrets
from datetime import datetime, date
from database import get_db_connection
from modules.accounting import post_double_entry
from modules.loans import get_loans, get_loan, allocate_payment
from modules.theme import money_column

PAYMENT_METHODS = ["MTN MoMo", "Airtel Money", "Bank Transfer", "Cash"]

def log_message(customer_id, message):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO messages_log (customer_id, message, sent_at) VALUES (%s,%s,%s)",
        (customer_id, message, datetime.now().strftime('%Y-%m-%d %H:%M'))
    )
    conn.commit()
    cur.close()
    conn.close()

def get_messages(sacco_id, limit=20):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT messages_log.*, customers.name AS customer_name
        FROM messages_log
        JOIN customers ON messages_log.customer_id = customers.id
        WHERE customers.sacco_id = %s
        ORDER BY messages_log.id DESC LIMIT %s
    """, (sacco_id, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def record_repayment(loan_id, amount, sacco_id, method="Mobile Money", reference=None):
    loan = get_loan(loan_id)
    if loan is None:
        return None, "Loan not found."
    if amount <= 0:
        return None, "Amount must be greater than zero."
    reference = reference or f"REF-{secrets.token_hex(4).upper()}"
    today     = datetime.now().strftime('%Y-%m-%d %H:%M')
    conn      = get_db_connection()
    cur       = conn.cursor()
    new_balance = max(round(loan['balance'] - amount, 2), 0)
    new_status  = 'Closed' if new_balance <= 0 else 'Active'
    cur.execute(
        "INSERT INTO repayments (loan_id, amount, method, reference, date) VALUES (%s,%s,%s,%s,%s)",
        (loan_id, amount, method, reference, today)
    )
    cur.execute(
        "UPDATE loans SET balance = %s, status = %s WHERE id = %s",
        (new_balance, new_status, loan_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    allocate_payment(loan_id, amount)
    post_double_entry(
        "Cash/Bank", "Loans Receivable", amount,
        f"Repayment for Loan #{loan_id}", reference, sacco_id=sacco_id
    )
    closing_note = " Your loan is now FULLY REPAID. Well done! 🎉" if new_status == 'Closed' else ""
    message = (
        f"Dear {loan['customer_name']}, we have received your payment of "
        f"UGX {amount:,.0f} via {method} (Ref: {reference}). "
        f"Your new loan balance is UGX {new_balance:,.0f}.{closing_note} Thank you."
    )
    log_message(loan['customer_id'], message)
    return new_balance, message

def get_repayments(sacco_id, limit=50):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT repayments.*, customers.name AS customer_name
        FROM repayments
        JOIN loans     ON repayments.loan_id = loans.id
        JOIN customers ON loans.customer_id  = customers.id
        WHERE loans.sacco_id = %s
        ORDER BY repayments.id DESC LIMIT %s
    """, (sacco_id, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_overdue_loans(sacco_id):
    conn      = get_db_connection()
    cur       = conn.cursor()
    today_str = date.today().strftime('%Y-%m-%d')
    cur.execute("""
        SELECT loans.id AS loan_id, customers.name AS customer_name,
               customers.phone AS customer_phone, customers.village,
               loans.balance,
               MIN(loan_schedule.due_date)  AS oldest_due,
               COUNT(loan_schedule.id)      AS overdue_count,
               SUM(loan_schedule.due_amount - loan_schedule.paid_amount) AS total_overdue_amount
        FROM loan_schedule
        JOIN loans     ON loan_schedule.loan_id   = loans.id
        JOIN customers ON loans.customer_id = customers.id
        WHERE loan_schedule.status  != 'Paid'
          AND loan_schedule.due_date < %s
          AND loans.status   = 'Active'
          AND loans.sacco_id = %s
        GROUP BY loans.id, customers.name, customers.phone, customers.village, loans.balance
        ORDER BY oldest_due ASC
    """, (today_str, sacco_id))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_collection_summary(sacco_id):
    conn      = get_db_connection()
    cur       = conn.cursor()
    today_str = date.today().strftime('%Y-%m-%d')
    month_str = date.today().strftime('%Y-%m')
    cur.execute("""
        SELECT COALESCE(SUM(r.amount),0) AS t FROM repayments r
        JOIN loans l ON r.loan_id = l.id
        WHERE l.sacco_id = %s AND r.date LIKE %s
    """, (sacco_id, today_str + '%'))
    today_total = list(cur.fetchone().values())[0]
    cur.execute("""
        SELECT COALESCE(SUM(r.amount),0) AS t FROM repayments r
        JOIN loans l ON r.loan_id = l.id
        WHERE l.sacco_id = %s AND r.date LIKE %s
    """, (sacco_id, month_str + '%'))
    month_total = list(cur.fetchone().values())[0]
    cur.execute("""
        SELECT r.method, COUNT(*) AS txns, COALESCE(SUM(r.amount),0) AS total
        FROM repayments r JOIN loans l ON r.loan_id = l.id
        WHERE l.sacco_id = %s
        GROUP BY r.method ORDER BY total DESC
    """, (sacco_id,))
    by_method = cur.fetchall()
    cur.execute("""
        SELECT COALESCE(SUM(ls.due_amount - ls.paid_amount),0) AS t
        FROM loan_schedule ls JOIN loans l ON ls.loan_id = l.id
        WHERE l.sacco_id = %s AND ls.status != 'Paid' AND ls.due_date < %s
    """, (sacco_id, today_str))
    overdue_total = list(cur.fetchone().values())[0]
    cur.close()
    conn.close()
    return today_total, month_total, by_method, overdue_total

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected. Set up a SACCO Profile first.")
        return

    today_total, month_total, by_method, overdue_total = get_collection_summary(sacco_id)
    overdue_loans = get_overdue_loans(sacco_id)

    st.write("#### Collection Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Collected Today",      f"UGX {today_total:,.0f}")
    c2.metric("Collected This Month", f"UGX {month_total:,.0f}")
    c3.metric("Total Overdue Amount", f"UGX {overdue_total:,.0f}",
              delta=f"{len(overdue_loans)} loans overdue",
              delta_color="inverse" if overdue_loans else "normal")
    c4.metric("Overdue Loans", len(overdue_loans),
              delta_color="inverse" if overdue_loans else "normal")

    if by_method:
        with st.expander("Payment channel breakdown"):
            total_col = sum(r['total'] for r in by_method) or 1
            st.dataframe(
                [{"Channel": r['method'] or 'Unknown', "Transactions": r['txns'],
                  "Total (UGX)": r['total'], "Share": f"{r['total']/total_col*100:.1f}%"}
                 for r in by_method],
                column_config={"Total (UGX)": money_column()},
                use_container_width=True, hide_index=True
            )

    st.divider()
    st.write("#### ⚠️ Overdue Loans — Follow-Up List")
    if not overdue_loans:
        st.success("✅ No overdue loans right now.")
    else:
        st.error(f"🚨 {len(overdue_loans)} loan(s) overdue.")
        today_dt = date.today()
        for row in overdue_loans:
            try:
                oldest_dt    = datetime.strptime(row['oldest_due'], '%Y-%m-%d').date()
                days_overdue = (today_dt - oldest_dt).days
            except Exception:
                days_overdue = 0
            severity = "🔴" if days_overdue > 30 else "🟡"
            col_a, col_b = st.columns([3,1])
            with col_a:
                st.markdown(f"{severity} **{row['customer_name']}** — Loan #{row['loan_id']} | 📞 {row['customer_phone']} | 📍 {row['village'] or '—'}")
                st.caption(f"Overdue since {row['oldest_due']} ({days_overdue} days) | {row['overdue_count']} missed | Overdue: UGX {row['total_overdue_amount']:,.0f}")
            with col_b:
                st.caption(f"Balance: UGX {row['balance']:,.0f}")

    st.divider()
    st.write("#### 📲 Record a Repayment")
    active_loans = get_loans(sacco_id, status='Active')
    if not active_loans:
        st.info("No active loans to collect against.")
    else:
        with st.form("repayment_form", clear_on_submit=True):
            loan_map    = {f"Loan #{l['id']} — {l['customer_name']} (Bal: UGX {l['balance']:,.0f})": l['id'] for l in active_loans}
            loan_choice = st.selectbox("Loan", list(loan_map.keys()))
            col_f1, col_f2 = st.columns(2)
            with col_f1: amount    = st.number_input("Amount received (UGX)", min_value=0.0, step=1000.0)
            with col_f2: method    = st.selectbox("Payment channel", PAYMENT_METHODS)
            reference = st.text_input("Reference (optional)", placeholder="e.g. MTN transaction ID")
            submitted = st.form_submit_button("Process Payment", type="primary")
            if submitted:
                if amount <= 0:
                    st.error("Amount must be greater than zero.")
                else:
                    loan_id = loan_map[loan_choice]
                    new_balance, message = record_repayment(loan_id, amount, sacco_id, method, reference.strip() or None)
                    if new_balance is None:
                        st.error(message)
                    else:
                        if new_balance == 0:
                            st.balloons()
                            st.success("🎉 Loan fully repaid!")
                        else:
                            st.success(f"✅ UGX {amount:,.0f} processed. New balance: UGX {new_balance:,.0f}")
                        st.code(message, language=None)

    st.divider()
    st.write("#### Recent Repayments")
    repayments = get_repayments(sacco_id, limit=50)
    if repayments:
        st.dataframe(
            [{"Date": r['date'], "Customer": r['customer_name'], "Loan": r['loan_id'],
              "Amount": r['amount'], "Channel": r['method'], "Reference": r['reference']}
             for r in repayments],
            column_config={"Amount": money_column()},
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No repayments recorded yet.")

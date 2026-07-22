import streamlit as st
from datetime import date
from database import get_db_connection
from modules.collections import get_messages
from modules.loans import get_upcoming_installments
from modules.theme import money_column
from modules.nssf_engine import get_tier

def _get_at_risk_count(sacco_id):
    conn      = get_db_connection()
    cur       = conn.cursor()
    today_str = date.today().strftime('%Y-%m-%d')
    cur.execute("""
        SELECT COUNT(DISTINCT loans.id) AS c FROM loan_schedule
        JOIN loans ON loan_schedule.loan_id = loans.id
        WHERE loan_schedule.status != 'Paid'
          AND loan_schedule.due_date < %s
          AND loans.status = 'Active'
          AND loans.sacco_id = %s
    """, (today_str, sacco_id))
    count = list(cur.fetchone().values())[0]
    cur.close()
    conn.close()
    return count

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected. Set up a SACCO Profile first.")
        return

    conn      = get_db_connection()
    cur       = conn.cursor()
    today_str = date.today().strftime('%Y-%m-%d')
    month_str = date.today().strftime('%Y-%m')

    cur.execute("SELECT COUNT(*) AS c FROM customers WHERE sacco_id = %s", (sacco_id,))
    total_customers = list(cur.fetchone().values())[0]

    cur.execute("SELECT COUNT(*) AS c FROM customers WHERE sacco_id = %s AND member_type='Member'", (sacco_id,))
    members = list(cur.fetchone().values())[0]

    cur.execute("SELECT COUNT(*) AS c FROM loans WHERE sacco_id = %s AND status='Active'", (sacco_id,))
    active_loans = list(cur.fetchone().values())[0]

    cur.execute("SELECT COALESCE(SUM(balance),0) AS s FROM loans WHERE sacco_id = %s AND status='Active'", (sacco_id,))
    outstanding = list(cur.fetchone().values())[0]

    cur.execute("""
        SELECT COALESCE(SUM(repayments.amount),0) AS s FROM repayments
        JOIN loans ON repayments.loan_id = loans.id WHERE loans.sacco_id = %s
    """, (sacco_id,))
    collected_total = list(cur.fetchone().values())[0]

    cur.execute("SELECT COALESCE(SUM(balance),0) AS s FROM savings_accounts WHERE sacco_id = %s", (sacco_id,))
    total_savings = list(cur.fetchone().values())[0]

    cur.execute("""
        SELECT COALESCE(SUM(loan_schedule.due_amount - loan_schedule.paid_amount),0) AS s
        FROM loan_schedule
        JOIN loans ON loan_schedule.loan_id = loans.id
        WHERE loan_schedule.due_date = %s
          AND loan_schedule.status != 'Paid'
          AND loans.sacco_id = %s
    """, (today_str, sacco_id))
    expected_today = list(cur.fetchone().values())[0]

    cur.execute("""
        SELECT COALESCE(SUM(repayments.amount),0) AS s FROM repayments
        JOIN loans ON repayments.loan_id = loans.id
        WHERE repayments.date LIKE %s AND loans.sacco_id = %s
    """, (today_str + '%', sacco_id))
    collected_today = list(cur.fetchone().values())[0]

    cur.execute("SELECT COUNT(*) AS c FROM customers WHERE sacco_id = %s", (sacco_id,))
    total_mem = list(cur.fetchone().values())[0]

    cur.execute("SELECT COUNT(*) AS c FROM customers WHERE sacco_id = %s AND nssf_registered = 1", (sacco_id,))
    nssf_reg = list(cur.fetchone().values())[0]

    cur.execute("""
        SELECT COALESCE(SUM(nssf_amount),0) AS s FROM nssf_contributions
        WHERE sacco_id = %s AND remitted = 0
    """, (sacco_id,))
    nssf_unremitted = list(cur.fetchone().values())[0]

    cur.execute("""
        SELECT c.name, COALESCE(SUM(g.points),0) AS pts
        FROM customers c
        LEFT JOIN gold_points_ledger g ON g.customer_id = c.id
        WHERE c.sacco_id = %s
        GROUP BY c.id, c.name ORDER BY pts DESC LIMIT 1
    """, (sacco_id,))
    top_gold = cur.fetchone()

    cur.close()
    conn.close()

    at_risk_count  = _get_at_risk_count(sacco_id)
    compliance_pct = (nssf_reg / total_mem * 100) if total_mem else 0

    st.write("#### Today's Snapshot")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Expected Today",           f"UGX {expected_today:,.0f}")
    c2.metric("Collected Today",          f"UGX {collected_today:,.0f}")
    c3.metric("High-Risk Loans (PAR)",    at_risk_count,
              delta="overdue installments" if at_risk_count > 0 else "Portfolio clean ✅",
              delta_color="inverse" if at_risk_count > 0 else "normal")
    c4.metric("Cash Collected (All-Time)", f"UGX {collected_total:,.0f}")

    st.write("#### Business Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Customers",          total_customers, delta=f"{members} members", delta_color="off")
    c2.metric("Active Loans",       active_loans)
    c3.metric("Outstanding",        f"UGX {outstanding:,.0f}")
    c4.metric("Total Savings Held", f"UGX {total_savings:,.0f}")

    st.write("#### 🇺🇬 NSSF & Gold Points")
    n1, n2, n3, n4 = st.columns(4)
    n1.metric("NSSF Compliance",    f"{compliance_pct:.1f}%",
              f"{nssf_reg} of {total_mem} registered",
              delta_color="normal" if compliance_pct >= 80 else "inverse")
    n2.metric("Unremitted to NSSF", f"UGX {nssf_unremitted:,.0f}",
              "pending submission" if nssf_unremitted > 0 else "Fully remitted ✅",
              delta_color="inverse" if nssf_unremitted > 0 else "normal")
    if top_gold and top_gold['pts'] > 0:
        tier = get_tier(int(top_gold['pts']))
        n3.metric("🏅 Top Gold Earner", top_gold['name'], f"{top_gold['pts']:,} pts — {tier}")
    else:
        n3.metric("🏅 Gold Points", "No earners yet", "Make deposits to start earning")
    n4.metric("NSSF Unregistered", total_mem - nssf_reg,
              "members to follow up" if (total_mem - nssf_reg) > 0 else "Full compliance ✅",
              delta_color="inverse" if (total_mem - nssf_reg) > 0 else "normal")

    st.write("#### 🔔 Upcoming Repayments (next 7 days)")
    upcoming = get_upcoming_installments(sacco_id, days=7)
    if upcoming:
        st.dataframe(
            [{"Due Date": u['due_date'], "Customer": u['customer_name'],
              "Phone": u['customer_phone'],
              "Amount Due": u['due_amount'] - u['paid_amount'],
              "Loan ID": u['loan_id']} for u in upcoming],
            column_config={"Amount Due": money_column()},
            use_container_width=True
        )
    else:
        st.info("No repayments due in the next 7 days.")

    st.write("#### Recent Client Messages")
    messages = get_messages(sacco_id, limit=5)
    if not messages:
        st.info("No messages sent yet.")
    for m in messages:
        st.write(f"**{m['customer_name']}** — {m['sent_at']}")
        st.caption(m['message'])

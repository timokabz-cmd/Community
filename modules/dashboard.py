import streamlit as st
from datetime import date
from database import get_db_connection
from modules.collections import get_messages
from modules.loans import get_upcoming_installments
from modules.theme import money_column
from modules.nssf_engine import get_tier, get_points_balance

def _get_at_risk_count(sacco_id):
    """Local PAR check — no dependency on reports module."""
    conn = get_db_connection()
    today_str = date.today().strftime('%Y-%m-%d')
    rows = conn.execute("""
        SELECT DISTINCT loans.id FROM loan_schedule
        JOIN loans ON loan_schedule.loan_id = loans.id
        WHERE loan_schedule.status != 'Paid'
          AND loan_schedule.due_date < ?
          AND loans.status = 'Active'
          AND loans.sacco_id = ?
    """, (today_str, sacco_id)).fetchall()
    conn.close()
    return len(rows)

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected. Set up a SACCO Profile first.")
        return

    conn = get_db_connection()
    total_customers = conn.execute(
        "SELECT COUNT(*) FROM customers WHERE sacco_id = ?", (sacco_id,)
    ).fetchone()[0]
    members = conn.execute(
        "SELECT COUNT(*) FROM customers WHERE sacco_id = ? AND member_type='Member'", (sacco_id,)
    ).fetchone()[0]
    active_loans = conn.execute(
        "SELECT COUNT(*) FROM loans WHERE sacco_id = ? AND status='Active'", (sacco_id,)
    ).fetchone()[0]
    outstanding = conn.execute(
        "SELECT COALESCE(SUM(balance),0) FROM loans WHERE sacco_id = ? AND status='Active'", (sacco_id,)
    ).fetchone()[0]
    collected_total = conn.execute(
        """SELECT COALESCE(SUM(repayments.amount),0) FROM repayments
           JOIN loans ON repayments.loan_id = loans.id WHERE loans.sacco_id = ?""",
        (sacco_id,)
    ).fetchone()[0]
    total_savings = conn.execute(
        "SELECT COALESCE(SUM(balance),0) FROM savings_accounts WHERE sacco_id = ?", (sacco_id,)
    ).fetchone()[0]

    today_str = date.today().strftime('%Y-%m-%d')
    expected_today = conn.execute(
        """SELECT COALESCE(SUM(loan_schedule.due_amount - loan_schedule.paid_amount),0)
           FROM loan_schedule
           JOIN loans ON loan_schedule.loan_id = loans.id
           WHERE loan_schedule.due_date = ?
             AND loan_schedule.status != 'Paid'
             AND loans.sacco_id = ?""",
        (today_str, sacco_id)
    ).fetchone()[0]
    collected_today = conn.execute(
        """SELECT COALESCE(SUM(repayments.amount),0) FROM repayments
           JOIN loans ON repayments.loan_id = loans.id
           WHERE repayments.date LIKE ? AND loans.sacco_id = ?""",
        (today_str + '%', sacco_id)
    ).fetchone()[0]

    # NSSF compliance snapshot
    total_mem     = conn.execute(
        "SELECT COUNT(*) FROM customers WHERE sacco_id = ?", (sacco_id,)
    ).fetchone()[0]
    nssf_reg      = conn.execute(
        "SELECT COUNT(*) FROM customers WHERE sacco_id = ? AND nssf_registered = 1", (sacco_id,)
    ).fetchone()[0]
    nssf_unremitted = conn.execute(
        "SELECT COALESCE(SUM(nssf_amount),0) FROM nssf_contributions WHERE sacco_id = ? AND remitted = 0",
        (sacco_id,)
    ).fetchone()[0]

    # Gold points — top earner this SACCO
    top_gold = conn.execute("""
        SELECT c.name, COALESCE(SUM(g.points),0) AS pts
        FROM customers c
        LEFT JOIN gold_points_ledger g ON g.customer_id = c.id
        WHERE c.sacco_id = ?
        GROUP BY c.id ORDER BY pts DESC LIMIT 1
    """, (sacco_id,)).fetchone()

    conn.close()

    at_risk_count  = _get_at_risk_count(sacco_id)
    compliance_pct = (nssf_reg / total_mem * 100) if total_mem else 0

    # ── Today's Snapshot ─────────────────────────────────────────────────────
    st.write("#### Today's Snapshot")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Expected Today",          f"UGX {expected_today:,.0f}")
    c2.metric("Collected Today",         f"UGX {collected_today:,.0f}")
    c3.metric("High-Risk Loans (PAR)",   at_risk_count,
              delta="overdue installments" if at_risk_count > 0 else "Portfolio clean ✅",
              delta_color="inverse" if at_risk_count > 0 else "normal")
    c4.metric("Cash Collected (All-Time)", f"UGX {collected_total:,.0f}")

    # ── Business Overview ─────────────────────────────────────────────────────
    st.write("#### Business Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Customers",        total_customers, delta=f"{members} members", delta_color="off")
    c2.metric("Active Loans",     active_loans)
    c3.metric("Outstanding",      f"UGX {outstanding:,.0f}")
    c4.metric("Total Savings Held", f"UGX {total_savings:,.0f}")

    # ── NSSF & Gold Points strip ──────────────────────────────────────────────
    st.write("#### 🇺🇬 NSSF & Gold Points")
    n1, n2, n3, n4 = st.columns(4)
    n1.metric("NSSF Compliance",      f"{compliance_pct:.1f}%",
              f"{nssf_reg} of {total_mem} registered",
              delta_color="normal" if compliance_pct >= 80 else "inverse")
    n2.metric("Unremitted to NSSF",   f"UGX {nssf_unremitted:,.0f}",
              "pending submission" if nssf_unremitted > 0 else "Fully remitted ✅",
              delta_color="inverse" if nssf_unremitted > 0 else "normal")
    if top_gold and top_gold['pts'] > 0:
        tier = get_tier(int(top_gold['pts']))
        n3.metric("🏅 Top Gold Earner",  top_gold['name'], f"{top_gold['pts']:,} pts — {tier}")
    else:
        n3.metric("🏅 Gold Points",      "No earners yet", "Make deposits to start earning")
    n4.metric("NSSF Unregistered",    total_mem - nssf_reg,
              "members to follow up" if (total_mem - nssf_reg) > 0 else "Full compliance ✅",
              delta_color="inverse" if (total_mem - nssf_reg) > 0 else "normal")

    # ── Upcoming Repayments ───────────────────────────────────────────────────
    st.write("#### 🔔 Upcoming Repayments (next 7 days)")
    upcoming = get_upcoming_installments(sacco_id, days=7)
    if upcoming:
        st.dataframe(
            [{"Due Date":   u['due_date'],
              "Customer":   u['customer_name'],
              "Phone":      u['customer_phone'],
              "Amount Due": u['due_amount'] - u['paid_amount'],
              "Loan ID":    u['loan_id']} for u in upcoming],
            column_config={"Amount Due": money_column()},
            use_container_width=True
        )
    else:
        st.info("No repayments due in the next 7 days.")

    # ── Recent Messages ───────────────────────────────────────────────────────
    st.write("#### Recent Client Messages")
    messages = get_messages(sacco_id, limit=5)
    if not messages:
        st.info("No messages sent yet. Record a repayment in Collections to see auto-generated confirmations here.")
    for m in messages:
        st.write(f"**{m['customer_name']}** — {m['sent_at']}")
        st.caption(m['message'])

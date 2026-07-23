import streamlit as st
from datetime import date
from database import get_db_connection
from modules.collections import get_messages
from modules.loans import get_upcoming_installments
from modules.theme import money_column
from modules.nssf_engine import get_tier

@st.cache_data(ttl=60, show_spinner=False)
def _get_dashboard_stats(sacco_id):
    """
    All 12 dashboard metrics in a single DB round-trip.
    Cached for 60 seconds — fast repeat loads, still live data.
    """
    conn      = get_db_connection()
    cur       = conn.cursor()
    today_str = date.today().strftime('%Y-%m-%d')
    month_str = date.today().strftime('%Y-%m')

    cur.execute("""
        SELECT
            -- membership
            COUNT(*)                                              AS total_customers,
            COUNT(*) FILTER (WHERE member_type = 'Member')       AS members,
            COUNT(*) FILTER (WHERE nssf_registered = 1)         AS nssf_reg,
            COUNT(*) FILTER (WHERE nssf_registered = 0
                             OR nssf_registered IS NULL)         AS nssf_unreg
        FROM customers WHERE sacco_id = %s
    """, (sacco_id,))
    mem = cur.fetchone()

    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'Active')            AS active_loans,
            COALESCE(SUM(balance) FILTER
                     (WHERE status = 'Active'), 0)               AS outstanding
        FROM loans WHERE sacco_id = %s
    """, (sacco_id,))
    loan_stats = cur.fetchone()

    cur.execute("""
        SELECT COALESCE(SUM(r.amount), 0) AS collected_total
        FROM repayments r
        JOIN loans l ON r.loan_id = l.id
        WHERE l.sacco_id = %s
    """, (sacco_id,))
    repay_all = cur.fetchone()

    cur.execute("""
        SELECT COALESCE(SUM(balance), 0) AS total_savings
        FROM savings_accounts WHERE sacco_id = %s
    """, (sacco_id,))
    sav = cur.fetchone()

    cur.execute("""
        SELECT
            COALESCE(SUM(ls.due_amount - ls.paid_amount)
                FILTER (WHERE ls.due_date = %s
                        AND ls.status != 'Paid'), 0)             AS expected_today,
            COUNT(DISTINCT l.id)
                FILTER (WHERE ls.status != 'Paid'
                        AND ls.due_date < %s)                    AS at_risk_count
        FROM loan_schedule ls
        JOIN loans l ON ls.loan_id = l.id
        WHERE l.sacco_id = %s AND l.status = 'Active'
    """, (today_str, today_str, sacco_id))
    schedule_stats = cur.fetchone()

    cur.execute("""
        SELECT COALESCE(SUM(r.amount), 0) AS collected_today
        FROM repayments r
        JOIN loans l ON r.loan_id = l.id
        WHERE l.sacco_id = %s AND r.date LIKE %s
    """, (sacco_id, today_str + '%'))
    today_col = cur.fetchone()

    cur.execute("""
        SELECT COALESCE(SUM(nssf_amount), 0) AS unremitted
        FROM nssf_contributions
        WHERE sacco_id = %s AND remitted = 0
    """, (sacco_id,))
    nssf_stats = cur.fetchone()

    cur.execute("""
        SELECT c.name, COALESCE(SUM(g.points), 0) AS pts
        FROM customers c
        LEFT JOIN gold_points_ledger g ON g.customer_id = c.id
        WHERE c.sacco_id = %s
        GROUP BY c.id, c.name
        ORDER BY pts DESC LIMIT 1
    """, (sacco_id,))
    top_gold = cur.fetchone()

    cur.close()
    conn.close()

    return {
        'total_customers':  mem['total_customers'],
        'members':          mem['members'],
        'nssf_reg':         mem['nssf_reg'],
        'nssf_unreg':       mem['nssf_unreg'],
        'active_loans':     loan_stats['active_loans'],
        'outstanding':      loan_stats['outstanding'],
        'collected_total':  repay_all['collected_total'],
        'total_savings':    sav['total_savings'],
        'expected_today':   schedule_stats['expected_today'],
        'at_risk_count':    schedule_stats['at_risk_count'],
        'collected_today':  today_col['collected_today'],
        'nssf_unremitted':  nssf_stats['unremitted'],
        'top_gold_name':    top_gold['name'] if top_gold and top_gold['pts'] > 0 else None,
        'top_gold_pts':     int(top_gold['pts']) if top_gold else 0,
    }

@st.cache_data(ttl=60, show_spinner=False)
def _get_upcoming_cached(sacco_id):
    return get_upcoming_installments(sacco_id, days=7)

@st.cache_data(ttl=60, show_spinner=False)
def _get_messages_cached(sacco_id):
    return get_messages(sacco_id, limit=5)

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected. Set up a SACCO Profile first.")
        return

    s          = _get_dashboard_stats(sacco_id)
    compliance = (s['nssf_reg'] / s['total_customers'] * 100) if s['total_customers'] else 0

    # ── Today's Snapshot ──────────────────────────────────────────────────────
    st.write("#### Today's Snapshot")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Expected Today",            f"UGX {s['expected_today']:,.0f}")
    c2.metric("Collected Today",           f"UGX {s['collected_today']:,.0f}")
    c3.metric("High-Risk Loans (PAR)",     int(s['at_risk_count']),
              delta="overdue installments" if s['at_risk_count'] > 0 else "Portfolio clean ✅",
              delta_color="inverse" if s['at_risk_count'] > 0 else "normal")
    c4.metric("Cash Collected (All-Time)", f"UGX {s['collected_total']:,.0f}")

    # ── Business Overview ─────────────────────────────────────────────────────
    st.write("#### Business Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Customers",          s['total_customers'],
              delta=f"{s['members']} members", delta_color="off")
    c2.metric("Active Loans",       s['active_loans'])
    c3.metric("Outstanding",        f"UGX {s['outstanding']:,.0f}")
    c4.metric("Total Savings Held", f"UGX {s['total_savings']:,.0f}")

    # ── NSSF & Gold Points ────────────────────────────────────────────────────
    st.write("#### 🇺🇬 NSSF & Gold Points")
    n1, n2, n3, n4 = st.columns(4)
    n1.metric("NSSF Compliance",    f"{compliance:.1f}%",
              f"{s['nssf_reg']} of {s['total_customers']} registered",
              delta_color="normal" if compliance >= 80 else "inverse")
    n2.metric("Unremitted to NSSF", f"UGX {s['nssf_unremitted']:,.0f}",
              "pending submission" if s['nssf_unremitted'] > 0 else "Fully remitted ✅",
              delta_color="inverse" if s['nssf_unremitted'] > 0 else "normal")
    if s['top_gold_name']:
        tier = get_tier(s['top_gold_pts'])
        n3.metric("🏅 Top Gold Earner", s['top_gold_name'],
                  f"{s['top_gold_pts']:,} pts — {tier}")
    else:
        n3.metric("🏅 Gold Points", "No earners yet", "Make deposits to start")
    n4.metric("NSSF Unregistered",  s['nssf_unreg'],
              "members to follow up" if s['nssf_unreg'] > 0 else "Full compliance ✅",
              delta_color="inverse" if s['nssf_unreg'] > 0 else "normal")

    # ── Upcoming Repayments ───────────────────────────────────────────────────
    st.write("#### 🔔 Upcoming Repayments (next 7 days)")
    upcoming = _get_upcoming_cached(sacco_id)
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

    # ── Recent Messages ───────────────────────────────────────────────────────
    st.write("#### Recent Client Messages")
    messages = _get_messages_cached(sacco_id)
    if not messages:
        st.info("No messages sent yet.")
    for m in messages:
        st.write(f"**{m['customer_name']}** — {m['sent_at']}")
        st.caption(m['message'])

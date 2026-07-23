import streamlit as st
from datetime import date, datetime
from collections import defaultdict, Counter
from database import get_db_connection
from modules.theme import money_column

GREEN = "#3F7A4D"; AMBER = "#A4732B"; RED = "#B0492E"; BLUE = "#2A4F82"

@st.cache_data(ttl=60, show_spinner=False)
def compute_risk_scores(sacco_id):
    """
    Single query pulls loans + overdue counts + savings + gold points
    instead of N+3 separate queries (one per loan).
    Cached 60 seconds.
    """
    conn      = get_db_connection()
    cur       = conn.cursor()
    today_str = date.today().strftime('%Y-%m-%d')

    # One query: loans + customer info
    cur.execute("""
        SELECT l.id, l.balance, l.customer_id, l.member_type,
               c.name AS customer_name, c.phone AS customer_phone,
               c.occupation, c.gender, c.date_of_birth,
               c.nssf_registered, c.village
        FROM loans l
        JOIN customers c ON l.customer_id = c.id
        WHERE l.status = 'Active' AND l.sacco_id = %s
    """, (sacco_id,))
    loans = cur.fetchall()

    if not loans:
        cur.close(); conn.close()
        return []

    loan_ids = [l['id'] for l in loans]

    # One query: overdue counts + days per loan
    cur.execute("""
        SELECT
            loan_id,
            COUNT(*) FILTER (WHERE status != 'Paid'
                             AND due_date < %s)          AS missed_count,
            MIN(due_date) FILTER (WHERE status != 'Paid'
                                  AND due_date < %s)     AS oldest_due
        FROM loan_schedule
        WHERE loan_id = ANY(%s)
        GROUP BY loan_id
    """, (today_str, today_str, loan_ids))
    overdue_map = {r['loan_id']: r for r in cur.fetchall()}

    # One query: savings balances for members
    customer_ids = [l['customer_id'] for l in loans]
    cur.execute("""
        SELECT customer_id, balance
        FROM savings_accounts
        WHERE customer_id = ANY(%s)
    """, (customer_ids,))
    savings_map = {r['customer_id']: r['balance'] for r in cur.fetchall()}

    # One query: gold points per customer
    cur.execute("""
        SELECT customer_id, COALESCE(SUM(points), 0) AS total
        FROM gold_points_ledger
        WHERE customer_id = ANY(%s)
        GROUP BY customer_id
    """, (customer_ids,))
    gold_map = {r['customer_id']: int(r['total']) for r in cur.fetchall()}

    cur.close()
    conn.close()

    today_dt = date.today()
    results  = []
    for loan in loans:
        od           = overdue_map.get(loan['id'], {})
        missed_count = od.get('missed_count') or 0
        days_overdue = 0
        if od.get('oldest_due'):
            try:
                days_overdue = (today_dt - datetime.strptime(od['oldest_due'], '%Y-%m-%d').date()).days
            except Exception:
                pass

        savings_balance = savings_map.get(loan['customer_id'], 0)
        gold_points     = gold_map.get(loan['customer_id'], 0)

        risk = ('High'   if days_overdue > 30 or missed_count >= 3
                else 'Medium' if days_overdue > 0  or missed_count >= 1
                else 'Low')
        if (risk == 'Medium' and not loan['nssf_registered']
                and savings_balance == 0 and gold_points == 0):
            risk = 'High'

        results.append({
            'loan_id':             loan['id'],
            'customer':            loan['customer_name'],
            'phone':               loan['customer_phone'],
            'village':             loan['village'] or '—',
            'member_type':         loan['member_type'],
            'occupation':          loan['occupation'],
            'gender':              loan['gender'],
            'balance':             loan['balance'],
            'missed_installments': int(missed_count),
            'days_overdue':        days_overdue,
            'savings_balance':     savings_balance,
            'nssf_registered':     bool(loan['nssf_registered']),
            'gold_points':         gold_points,
            'risk':                risk,
        })

    order = {'High': 0, 'Medium': 1, 'Low': 2}
    results.sort(key=lambda r: (order[r['risk']], -r['days_overdue']))
    return results

@st.cache_data(ttl=60, show_spinner=False)
def get_category_breakdown(sacco_id):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT c.occupation,
               COUNT(DISTINCT c.id) AS customer_count,
               COALESCE(SUM(l.balance) FILTER (WHERE l.status='Active'), 0) AS outstanding,
               COUNT(DISTINCT c.id) FILTER (WHERE c.nssf_registered=1) AS nssf_count
        FROM customers c
        LEFT JOIN loans l ON l.customer_id = c.id
        WHERE c.sacco_id = %s
        GROUP BY c.occupation
    """, (sacco_id,))
    by_occupation = cur.fetchall()

    cur.execute("""
        SELECT member_type, COUNT(*) AS count
        FROM customers WHERE sacco_id = %s GROUP BY member_type
    """, (sacco_id,))
    member_split = cur.fetchall()

    cur.execute("""
        SELECT c.gender, COUNT(DISTINCT c.id) AS count,
               COALESCE(SUM(l.balance) FILTER (WHERE l.status='Active'), 0) AS loan_balance
        FROM customers c
        LEFT JOIN loans l ON l.customer_id = c.id
        WHERE c.sacco_id = %s GROUP BY c.gender
    """, (sacco_id,))
    gender_split = cur.fetchall()

    cur.close(); conn.close()
    return by_occupation, member_split, gender_split

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected.")
        return

    with st.spinner("Calculating risk scores..."):
        scores = compute_risk_scores(sacco_id)

    high   = [s for s in scores if s['risk'] == 'High']
    medium = [s for s in scores if s['risk'] == 'Medium']
    low    = [s for s in scores if s['risk'] == 'Low']

    st.write("#### Risk Intelligence")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔴 High Risk",       len(high),
              "Immediate action" if high else "None",
              delta_color="inverse" if high else "normal")
    c2.metric("🟡 Medium Risk",     len(medium),
              "Monitor closely"  if medium else "None",
              delta_color="inverse" if medium else "normal")
    c3.metric("🟢 Low Risk",        len(low),   "On track")
    c4.metric("Total Active Loans", len(scores))

    if not scores:
        st.info("No active loans to analyze yet.")
        return

    if high:
        st.error(f"🚨 {len(high)} high-risk borrower(s) — follow up this week.")
        for s in high:
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(
                    f"🔴 **{s['customer']}** — Loan #{s['loan_id']} | "
                    f"📞 {s['phone']} | 📍 {s['village']}"
                )
                flags = []
                if s['missed_installments'] > 0: flags.append(f"{s['missed_installments']} missed")
                if s['days_overdue'] > 0:         flags.append(f"{s['days_overdue']} days overdue")
                if not s['nssf_registered']:       flags.append("⚠️ Not NSSF registered")
                if s['gold_points'] == 0:          flags.append("No Gold Points")
                st.caption(" | ".join(flags) if flags else "Elevated risk profile")
            with col_b:
                st.caption(f"Balance: UGX {s['balance']:,.0f}")
                st.caption(f"Savings: UGX {s['savings_balance']:,.0f}")
    else:
        st.success("✅ No high-risk borrowers.")

    st.divider()
    st.write("#### Full Risk Scorecard")
    st.dataframe(
        [{"Loan": s['loan_id'], "Customer": s['customer'], "Type": s['member_type'],
          "Occupation": s['occupation'] or '—', "Balance": s['balance'],
          "Missed": s['missed_installments'], "Days Overdue": s['days_overdue'],
          "Savings": s['savings_balance'], "NSSF": "✅" if s['nssf_registered'] else "⚠️",
          "Gold Pts": s['gold_points'], "Risk": s['risk']} for s in scores],
        column_config={"Balance": money_column(), "Savings": money_column()},
        use_container_width=True, hide_index=True
    )

    st.divider()
    st.write("#### Portfolio by Category")
    breakdown, member_split, gender_split = get_category_breakdown(sacco_id)

    col_occ, col_gender = st.columns(2)
    with col_occ:
        st.write("**By Occupation:**")
        if breakdown:
            total_cust = sum(b['customer_count'] for b in breakdown) or 1
            st.dataframe(
                [{"Occupation":  b['occupation'] or 'Not specified',
                  "Customers":   b['customer_count'],
                  "NSSF Reg.":   b['nssf_count'],
                  "Outstanding": b['outstanding'],
                  "Share":       f"{b['customer_count']/total_cust*100:.0f}%"}
                 for b in sorted(breakdown, key=lambda x: x['customer_count'], reverse=True)],
                column_config={"Outstanding": money_column()},
                use_container_width=True, hide_index=True
            )
    with col_gender:
        st.write("**By Gender:**")
        if gender_split:
            st.dataframe(
                [{"Gender":       g['gender'] or 'Not recorded',
                  "Customers":    g['count'],
                  "Loan Balance": g['loan_balance']}
                 for g in gender_split],
                column_config={"Loan Balance": money_column()},
                use_container_width=True, hide_index=True
            )

    if member_split:
        total_split = sum(m['count'] for m in member_split) or 1
        st.write("**Members vs Outsiders:**")
        st.dataframe(
            [{"Type": m['member_type'], "Count": m['count'],
              "Share": f"{m['count']/total_split*100:.0f}%"}
             for m in member_split],
            use_container_width=True, hide_index=True
        )

    st.divider()
    st.write("#### Concentration Risk")
    if breakdown:
        total_outstanding = sum(b['outstanding'] for b in breakdown) or 1
        risky = [b for b in breakdown if b['outstanding'] / total_outstanding > 0.4]
        if risky:
            for b in risky:
                pct = b['outstanding'] / total_outstanding * 100
                st.warning(
                    f"⚠️ **{b['occupation'] or 'Unspecified'}** holds "
                    f"**{pct:.0f}%** of outstanding portfolio "
                    f"(UGX {b['outstanding']:,.0f}). Consider diversifying lending."
                )
        else:
            st.success("✅ No single occupation group dominates — good diversification.")

    st.divider()
    st.write("#### NSSF Engagement vs Loan Risk")
    nssf_yes = Counter(s['risk'] for s in scores if s['nssf_registered'])
    nssf_no  = Counter(s['risk'] for s in scores if not s['nssf_registered'])
    st.dataframe(
        [{"Risk Level": lvl,
          "NSSF Registered":  nssf_yes.get(lvl, 0),
          "Not Registered":   nssf_no.get(lvl, 0)}
         for lvl in ['High', 'Medium', 'Low']],
        use_container_width=True, hide_index=True
    )

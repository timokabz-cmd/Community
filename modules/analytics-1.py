import streamlit as st
from datetime import date, datetime
from collections import defaultdict, Counter
from database import get_db_connection
from modules.theme import money_column

GREEN = "#3F7A4D"; AMBER = "#A4732B"; RED = "#B0492E"; BLUE = "#2A4F82"

def compute_risk_scores(sacco_id):
    conn      = get_db_connection()
    cur       = conn.cursor()
    today_str = date.today().strftime('%Y-%m-%d')
    today_dt  = date.today()

    cur.execute("""
        SELECT l.*, c.name AS customer_name, c.member_type, c.occupation,
               c.gender, c.date_of_birth, c.nssf_registered,
               c.village, c.phone AS customer_phone
        FROM loans l JOIN customers c ON l.customer_id = c.id
        WHERE l.status = 'Active' AND l.sacco_id = %s
    """, (sacco_id,))
    loans = cur.fetchall()

    results = []
    for loan in loans:
        cur.execute("SELECT * FROM loan_schedule WHERE loan_id = %s", (loan['id'],))
        schedule = cur.fetchall()
        overdue      = [s for s in schedule if s['status'] != 'Paid' and s['due_date'] < today_str]
        missed_count = len(overdue)
        days_overdue = 0
        if overdue:
            oldest       = min(overdue, key=lambda s: s['due_date'])
            days_overdue = (today_dt - datetime.strptime(oldest['due_date'], '%Y-%m-%d').date()).days

        savings_balance = 0
        if loan['member_type'] == 'Member':
            cur.execute("SELECT balance FROM savings_accounts WHERE customer_id = %s", (loan['customer_id'],))
            sav = cur.fetchone()
            if sav:
                savings_balance = sav['balance']

        cur.execute(
            "SELECT COALESCE(SUM(points),0) AS p FROM gold_points_ledger WHERE customer_id = %s",
            (loan['customer_id'],)
        )
        gold_points = list(cur.fetchone().values())[0]

        risk = 'High' if (days_overdue > 30 or missed_count >= 3) else 'Medium' if (days_overdue > 0 or missed_count >= 1) else 'Low'
        if risk == 'Medium' and not loan['nssf_registered'] and savings_balance == 0 and gold_points == 0:
            risk = 'High'

        results.append({
            'loan_id': loan['id'], 'customer': loan['customer_name'],
            'phone': loan['customer_phone'], 'village': loan['village'] or '—',
            'member_type': loan['member_type'], 'occupation': loan['occupation'],
            'gender': loan['gender'], 'balance': loan['balance'],
            'missed_installments': missed_count, 'days_overdue': days_overdue,
            'savings_balance': savings_balance,
            'nssf_registered': bool(loan['nssf_registered']),
            'gold_points': int(gold_points), 'risk': risk,
        })

    cur.close()
    conn.close()
    order = {'High': 0, 'Medium': 1, 'Low': 2}
    results.sort(key=lambda r: (order[r['risk']], -r['days_overdue']))
    return results

def get_category_breakdown(sacco_id):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT c.occupation,
               COUNT(DISTINCT c.id) AS customer_count,
               COALESCE(SUM(CASE WHEN l.status='Active' THEN l.balance ELSE 0 END),0) AS outstanding,
               COUNT(DISTINCT CASE WHEN c.nssf_registered=1 THEN c.id END) AS nssf_count
        FROM customers c
        LEFT JOIN loans l ON l.customer_id = c.id
        WHERE c.sacco_id = %s
        GROUP BY c.occupation
    """, (sacco_id,))
    by_occupation = cur.fetchall()

    cur.execute(
        "SELECT member_type, COUNT(*) AS count FROM customers WHERE sacco_id = %s GROUP BY member_type",
        (sacco_id,)
    )
    member_split = cur.fetchall()

    cur.execute("""
        SELECT gender, COUNT(*) AS count,
               COALESCE(SUM(CASE WHEN l.status='Active' THEN l.balance ELSE 0 END),0) AS loan_balance
        FROM customers c
        LEFT JOIN loans l ON l.customer_id = c.id
        WHERE c.sacco_id = %s GROUP BY gender
    """, (sacco_id,))
    gender_split = cur.fetchall()

    cur.close()
    conn.close()
    return by_occupation, member_split, gender_split

def _risk_badge(risk):
    colors = {'High': RED, 'Medium': AMBER, 'Low': GREEN}
    color  = colors.get(risk, BLUE)
    return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:10px;font-size:0.75rem;font-weight:600;">{risk}</span>'

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected.")
        return

    scores = compute_risk_scores(sacco_id)
    high   = [s for s in scores if s['risk'] == 'High']
    medium = [s for s in scores if s['risk'] == 'Medium']
    low    = [s for s in scores if s['risk'] == 'Low']

    st.write("#### Risk Intelligence")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔴 High Risk",   len(high),   "Immediate action" if high else "None", delta_color="inverse" if high else "normal")
    c2.metric("🟡 Medium Risk", len(medium), "Monitor closely"  if medium else "None", delta_color="inverse" if medium else "normal")
    c3.metric("🟢 Low Risk",    len(low),    "On track")
    c4.metric("Total Active Loans", len(scores))

    if not scores:
        st.info("No active loans to analyze yet.")
        return

    if high:
        st.error(f"🚨 {len(high)} high-risk borrower(s) — follow up this week.")
        for s in high:
            col_a, col_b = st.columns([3,1])
            with col_a:
                st.markdown(f"🔴 **{s['customer']}** — Loan #{s['loan_id']} | 📞 {s['phone']} | 📍 {s['village']}")
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
                [{"Occupation": b['occupation'] or 'Not specified',
                  "Customers": b['customer_count'], "NSSF Reg.": b['nssf_count'],
                  "Outstanding": b['outstanding'],
                  "Share": f"{b['customer_count']/total_cust*100:.0f}%"}
                 for b in sorted(breakdown, key=lambda x: x['customer_count'], reverse=True)],
                column_config={"Outstanding": money_column()},
                use_container_width=True, hide_index=True
            )
    with col_gender:
        st.write("**By Gender:**")
        if gender_split:
            st.dataframe(
                [{"Gender": g['gender'] or 'Not recorded',
                  "Customers": g['count'], "Loan Balance": g['loan_balance']}
                 for g in gender_split],
                column_config={"Loan Balance": money_column()},
                use_container_width=True, hide_index=True
            )

    if member_split:
        total_split = sum(m['count'] for m in member_split) or 1
        st.write("**Members vs Outsiders:**")
        st.dataframe(
            [{"Type": m['member_type'], "Count": m['count'],
              "Share": f"{m['count']/total_split*100:.0f}%"} for m in member_split],
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
                st.warning(f"⚠️ **{b['occupation'] or 'Unspecified'}** holds **{pct:.0f}%** of outstanding portfolio.")
        else:
            st.success("✅ No single occupation group dominates — good diversification.")

    st.divider()
    st.write("#### NSSF Engagement vs Loan Risk")
    nssf_yes = Counter(s['risk'] for s in scores if s['nssf_registered'])
    nssf_no  = Counter(s['risk'] for s in scores if not s['nssf_registered'])
    st.dataframe(
        [{"Risk Level": lvl, "NSSF Registered": nssf_yes.get(lvl,0), "Not Registered": nssf_no.get(lvl,0)}
         for lvl in ['High','Medium','Low']],
        use_container_width=True, hide_index=True
    )

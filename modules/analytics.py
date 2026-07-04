import streamlit as st
from datetime import date, datetime
from database import get_db_connection
from modules.theme import status_badge_html, money_column

def compute_risk_scores(sacco_id):
    """Risk-scores every active loan using missed installments, days overdue, and (for members) how much savings cushion they have against their balance."""
    conn = get_db_connection()
    today_str = date.today().strftime('%Y-%m-%d')
    loans = conn.execute(
        """SELECT loans.*, customers.name as customer_name, customers.member_type, customers.occupation FROM loans
           JOIN customers ON loans.customer_id = customers.id WHERE loans.status = 'Active' AND loans.sacco_id = ?""",
        (sacco_id,)
    ).fetchall()

    results = []
    for loan in loans:
        schedule = conn.execute(
            "SELECT * FROM loan_schedule WHERE loan_id = ?", (loan['id'],)
        ).fetchall()
        overdue = [s for s in schedule if s['status'] != 'Paid' and s['due_date'] < today_str]
        missed_count = len(overdue)
        days_overdue = 0
        if overdue:
            oldest = min(overdue, key=lambda s: s['due_date'])
            days_overdue = (date.today() - datetime.strptime(oldest['due_date'], '%Y-%m-%d').date()).days

        savings_balance = 0
        if loan['member_type'] == 'Member':
            sav = conn.execute(
                "SELECT balance FROM savings_accounts WHERE customer_id = ?", (loan['customer_id'],)
            ).fetchone()
            if sav:
                savings_balance = sav['balance']

        if days_overdue > 30 or missed_count >= 2:
            risk = 'High'
        elif days_overdue > 0 or missed_count == 1:
            risk = 'Medium'
        else:
            risk = 'Low'

        results.append({
            'loan_id': loan['id'], 'customer': loan['customer_name'], 'member_type': loan['member_type'],
            'occupation': loan['occupation'], 'balance': loan['balance'], 'missed_installments': missed_count,
            'days_overdue': days_overdue, 'savings_balance': savings_balance, 'risk': risk
        })
    conn.close()
    order = {'High': 0, 'Medium': 1, 'Low': 2}
    results.sort(key=lambda r: order[r['risk']])
    return results

def get_category_breakdown(sacco_id):
    conn = get_db_connection()
    by_occupation = conn.execute(
        """SELECT customers.occupation, COUNT(DISTINCT customers.id) as customer_count,
           COALESCE(SUM(CASE WHEN loans.status='Active' THEN loans.balance ELSE 0 END),0) as outstanding
           FROM customers LEFT JOIN loans ON loans.customer_id = customers.id
           WHERE customers.sacco_id = ? GROUP BY customers.occupation""",
        (sacco_id,)
    ).fetchall()
    member_split = conn.execute(
        "SELECT member_type, COUNT(*) as count FROM customers WHERE sacco_id = ? GROUP BY member_type",
        (sacco_id,)
    ).fetchall()
    conn.close()
    return by_occupation, member_split

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected. Set up a SACCO Profile first.")
        return

    st.write("#### ⚠️ Risk Analysis")
    st.caption("Every active loan, scored by missed installments, days overdue, and savings cushion (for members).")
    scores = compute_risk_scores(sacco_id)
    if scores:
        st.dataframe(
            [{"Loan ID": s['loan_id'], "Customer": s['customer'], "Type": s['member_type'],
              "Occupation": s['occupation'] or '—', "Balance": s['balance'], "Missed": s['missed_installments'],
              "Days Overdue": s['days_overdue'], "Savings": s['savings_balance'], "Risk": s['risk']} for s in scores],
            column_config={"Balance": money_column(), "Savings": money_column()},
            use_container_width=True
        )
        high = [s for s in scores if s['risk'] == 'High']
        if high:
            st.error(f"🚨 {len(high)} high-risk borrower(s) — recommend follow-up this week.")
            for s in high:
                st.markdown(
                    f"{status_badge_html('High Risk', kind='high')} &nbsp; "
                    f"**{s['customer']}** — Loan #{s['loan_id']}, UGX {s['balance']:,.0f} outstanding, "
                    f"{s['missed_installments']} missed, {s['days_overdue']} days overdue",
                    unsafe_allow_html=True
                )
        else:
            st.success("No high-risk borrowers right now.")
    else:
        st.info("No active loans to analyze yet.")

    st.write("#### Customer Categories")
    breakdown, member_split = get_category_breakdown(sacco_id)
    if breakdown:
        st.dataframe(
            [{"Occupation": b['occupation'] or 'Not specified', "Customers": b['customer_count'],
              "Outstanding Balance": b['outstanding']} for b in breakdown],
            column_config={"Outstanding Balance": money_column()},
            use_container_width=True
        )

    st.write("#### Members vs Outsiders")
    if member_split:
        st.dataframe(
            [{"Type": m['member_type'], "Count": m['count']} for m in member_split],
            use_container_width=True
        )

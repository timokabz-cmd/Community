import streamlit as st
import requests
from database import get_db_connection
from modules.analytics import compute_risk_scores, get_category_breakdown
from modules.loans import get_upcoming_installments
from modules.customers import get_customers
from modules.nssf_engine import get_tier

def build_data_summary(sacco_id):
    conn = get_db_connection()
    cur  = conn.cursor()

    def scalar(q, *args):
        cur.execute(q, args)
        return list(cur.fetchone().values())[0]

    total_customers = scalar("SELECT COUNT(*) FROM customers WHERE sacco_id=%s", sacco_id)
    members         = scalar("SELECT COUNT(*) FROM customers WHERE sacco_id=%s AND member_type='Member'", sacco_id)
    female          = scalar("SELECT COUNT(*) FROM customers WHERE sacco_id=%s AND LOWER(gender)='female'", sacco_id)
    pwd             = scalar("SELECT COUNT(*) FROM customers WHERE sacco_id=%s AND LOWER(pwd_status)='yes'", sacco_id)
    subsistence     = scalar("SELECT COUNT(*) FROM customers WHERE sacco_id=%s AND LOWER(subsistence_status)='yes'", sacco_id)
    active_loans    = scalar("SELECT COUNT(*) FROM loans WHERE sacco_id=%s AND status='Active'", sacco_id)
    outstanding     = scalar("SELECT COALESCE(SUM(balance),0) FROM loans WHERE sacco_id=%s AND status='Active'", sacco_id)
    closed_loans    = scalar("SELECT COUNT(*) FROM loans WHERE sacco_id=%s AND status='Closed'", sacco_id)
    due_total       = scalar("SELECT COALESCE(SUM(ls.due_amount),0) FROM loan_schedule ls JOIN loans l ON ls.loan_id=l.id WHERE l.sacco_id=%s", sacco_id)
    paid_total      = scalar("SELECT COALESCE(SUM(ls.paid_amount),0) FROM loan_schedule ls JOIN loans l ON ls.loan_id=l.id WHERE l.sacco_id=%s", sacco_id)
    total_savings   = scalar("SELECT COALESCE(SUM(balance),0) FROM savings_accounts WHERE sacco_id=%s", sacco_id)
    savings_accs    = scalar("SELECT COUNT(*) FROM savings_accounts WHERE sacco_id=%s", sacco_id)
    total_deposits  = scalar("SELECT COALESCE(SUM(st.amount),0) FROM savings_transactions st JOIN savings_accounts sa ON st.account_id=sa.id WHERE sa.sacco_id=%s AND st.type='Deposit'", sacco_id)
    nssf_reg        = scalar("SELECT COUNT(*) FROM customers WHERE sacco_id=%s AND nssf_registered=1", sacco_id)
    nssf_contrib    = scalar("SELECT COALESCE(SUM(nssf_amount),0) FROM nssf_contributions WHERE sacco_id=%s", sacco_id)
    nssf_unrem      = scalar("SELECT COALESCE(SUM(nssf_amount),0) FROM nssf_contributions WHERE sacco_id=%s AND remitted=0", sacco_id)
    gold_earners    = scalar("SELECT COUNT(DISTINCT customer_id) FROM gold_points_ledger WHERE sacco_id=%s", sacco_id)
    total_gold_pts  = scalar("SELECT COALESCE(SUM(points),0) FROM gold_points_ledger WHERE sacco_id=%s", sacco_id)
    streak_3        = scalar("SELECT COUNT(*) FROM gold_points_ledger WHERE sacco_id=%s AND reason='streak_3_months'", sacco_id)
    streak_6        = scalar("SELECT COUNT(*) FROM gold_points_ledger WHERE sacco_id=%s AND reason='streak_6_months'", sacco_id)

    cur.close()
    conn.close()

    repay_rate    = (paid_total / due_total * 100) if due_total > 0 else 100
    compliance_pct= (nssf_reg / total_customers * 100) if total_customers else 0
    risk_scores   = compute_risk_scores(sacco_id)
    high_risk     = [r for r in risk_scores if r['risk'] == 'High']
    medium_risk   = [r for r in risk_scores if r['risk'] == 'Medium']
    upcoming      = get_upcoming_installments(sacco_id, days=7)

    lines = [
        "=== SACCO OPERATING DATA ===", "",
        "--- MEMBERSHIP ---",
        f"Total: {total_customers} ({members} members, {total_customers-members} outsiders).",
        f"Female: {female} ({female/total_customers*100:.0f}%)." if total_customers else "",
        f"PWD: {pwd}. Subsistence economy: {subsistence}.",
        "", "--- LOAN PORTFOLIO ---",
        f"Active loans: {active_loans}. Outstanding: UGX {outstanding:,.0f}.",
        f"Closed/repaid: {closed_loans}.",
        f"Repayment rate: {repay_rate:.1f}%.",
        f"High-risk: {len(high_risk)}. Medium-risk: {len(medium_risk)}.",
    ]
    for r in high_risk[:5]:
        lines.append(f"  - {r['customer']}: UGX {r['balance']:,.0f}, {r['missed_installments']} missed, {r['days_overdue']} days, NSSF: {'YES' if r['nssf_registered'] else 'NO'}, Gold: {r['gold_points']}.")
    lines += [
        "", "--- SAVINGS ---",
        f"Accounts: {savings_accs}. Held: UGX {total_savings:,.0f}. Deposited ever: UGX {total_deposits:,.0f}.",
        f"Savings-to-loan ratio: {total_savings/outstanding:.2f}x." if outstanding > 0 else "",
        "", "--- NSSF ---",
        f"Registered: {nssf_reg} of {total_customers} ({compliance_pct:.1f}%).",
        f"Total contributions: UGX {nssf_contrib:,.0f}. Unremitted: UGX {nssf_unrem:,.0f}.",
        "", "--- GOLD POINTS ---",
        f"Earners: {gold_earners}. Total points: {total_gold_pts:,}.",
        f"3-month streaks: {streak_3}. 6-month Patriot streaks: {streak_6}.",
        "", "--- UPCOMING (7 days) ---",
        f"Installments due: {len(upcoming)}.",
    ]
    for u in upcoming[:10]:
        lines.append(f"  - {u['customer_name']}: UGX {u['due_amount']-u['paid_amount']:,.0f} due {u['due_date']}.")

    return "\n".join(l for l in lines if l is not None)

def generate_local_insights(sacco_id):
    conn = get_db_connection()
    cur  = conn.cursor()

    def scalar(q, *args):
        cur.execute(q, args)
        return list(cur.fetchone().values())[0]

    risk_scores  = compute_risk_scores(sacco_id)
    high_risk    = [r for r in risk_scores if r['risk'] == 'High']
    upcoming     = get_upcoming_installments(sacco_id, days=7)
    total_cust   = scalar("SELECT COUNT(*) FROM customers WHERE sacco_id=%s", sacco_id)
    nssf_reg     = scalar("SELECT COUNT(*) FROM customers WHERE sacco_id=%s AND nssf_registered=1", sacco_id)
    unremitted   = scalar("SELECT COALESCE(SUM(nssf_amount),0) FROM nssf_contributions WHERE sacco_id=%s AND remitted=0", sacco_id)
    gold_earners = scalar("SELECT COUNT(DISTINCT customer_id) FROM gold_points_ledger WHERE sacco_id=%s", sacco_id)
    outstanding  = scalar("SELECT COALESCE(SUM(balance),0) FROM loans WHERE sacco_id=%s AND status='Active'", sacco_id)
    total_savings= scalar("SELECT COALESCE(SUM(balance),0) FROM savings_accounts WHERE sacco_id=%s", sacco_id)

    cur.close()
    conn.close()

    breakdown, _, _ = get_category_breakdown(sacco_id)
    compliance_pct  = (nssf_reg / total_cust * 100) if total_cust else 0
    insights        = []

    if high_risk:
        names = ', '.join(r['customer'] for r in high_risk[:3])
        insights.append(f"🚨 **{len(high_risk)} high-risk loan(s)** — starting with: {names}{'...' if len(high_risk)>3 else '.'}  Call or visit before end of week.")
    else:
        insights.append("✅ **No high-risk borrowers** — portfolio is clean right now.")

    if upcoming:
        insights.append(f"📅 **{len(upcoming)} repayment(s) due in 7 days.** Send reminders today.")

    if compliance_pct < 80:
        insights.append(f"🇺🇬 **NSSF compliance is {compliance_pct:.0f}%** — {total_cust-nssf_reg} member(s) unregistered. Use the NSSF Outreach Export in Reports.")
    else:
        insights.append(f"🇺🇬 **Strong NSSF compliance: {compliance_pct:.0f}%** — keep it up.")

    if unremitted > 0:
        insights.append(f"💰 **UGX {unremitted:,.0f} in NSSF contributions** pending remittance. Go to NSSF Compliance to mark as remitted.")

    gp_pct = (gold_earners / total_cust * 100) if total_cust else 0
    if gp_pct < 30:
        insights.append(f"🏅 **Only {gp_pct:.0f}% of members earn Gold Points.** Encourage regular deposits.")
    else:
        insights.append(f"🏅 **{gp_pct:.0f}% of members earning Gold Points** — strong engagement.")

    if outstanding > 0:
        stl = total_savings / outstanding
        if stl < 0.5:
            insights.append(f"⚠️ **Savings-to-loan ratio is {stl:.2f}x** — lending more than savings held. Prioritise savings mobilisation.")
        elif stl >= 1.0:
            insights.append(f"💪 **Savings-to-loan ratio is {stl:.2f}x** — savings exceed loan book. Strong liquidity.")

    if breakdown and outstanding > 0:
        biggest = max(breakdown, key=lambda b: b['outstanding'])
        pct = biggest['outstanding'] / outstanding * 100
        if pct > 40:
            insights.append(f"📊 **Concentration risk:** {pct:.0f}% of loans in '{biggest['occupation'] or 'unspecified'}'. Consider diversifying.")

    summary = build_data_summary(sacco_id)
    return summary, insights

SYSTEM_PROMPT = """You are an expert SACCO operations analyst specialising in Uganda's community lending sector. You understand PDM, Emyooga, NDP IV, NSSF Uganda, MTN MoMo, Airtel Money, and Tier-4 financial institutions. Your answers are practical, actionable, grounded in the data provided, and written for a SACCO field officer or manager. Be concise — 2-4 sentences per insight unless more is clearly needed. Only use the data block provided."""

SUGGESTED_QUESTIONS = [
    "Which borrowers should I follow up with this week?",
    "How healthy is our savings-to-loan ratio?",
    "What is our NSSF compliance rate and what should we do about it?",
    "Which occupation group is our biggest concentration risk?",
    "How is the Gold Points programme affecting member engagement?",
    "Who are our top 3 savers and what tier are they on?",
    "What would you recommend to improve our repayment rate?",
    "How much NSSF have we collected but not yet remitted?",
]

def ask_ai(question, context):
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        api_key = None
    if not api_key:
        return None, "No ANTHROPIC_API_KEY found in Secrets. Add one in Streamlit Cloud → Manage app → Settings → Secrets."
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 800, "system": SYSTEM_PROMPT,
                  "messages": [{"role": "user", "content": f"SACCO data:\n\n{context}\n\nQuestion: {question}"}]},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        text = "".join(b.get("text","") for b in data.get("content",[]) if b.get("type")=="text")
        return text, None
    except Exception as e:
        return None, f"AI request failed: {e}"

def get_customer_insight(customer_id, sacco_id):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id=%s", (customer_id,))
    customer = cur.fetchone()
    cur.execute("SELECT balance FROM savings_accounts WHERE customer_id=%s", (customer_id,))
    savings  = cur.fetchone()
    cur.execute("SELECT * FROM loans WHERE customer_id=%s", (customer_id,))
    loans    = cur.fetchall()
    cur.execute("SELECT COALESCE(SUM(points),0) AS p FROM gold_points_ledger WHERE customer_id=%s", (customer_id,))
    gold_pts = list(cur.fetchone().values())[0]
    cur.execute("SELECT COALESCE(SUM(nssf_amount),0) AS s FROM nssf_contributions WHERE customer_id=%s", (customer_id,))
    nssf_c   = list(cur.fetchone().values())[0]
    cur.close()
    conn.close()
    active_loans = [l for l in loans if l['status'] == 'Active']
    outstanding  = sum(l['balance'] for l in active_loans)
    risk_scores  = compute_risk_scores(sacco_id)
    active_ids   = {l['id'] for l in active_loans}
    my_risk      = [r for r in risk_scores if r['loan_id'] in active_ids]
    return {'customer': customer, 'savings_balance': savings['balance'] if savings else None,
            'loans': loans, 'active_loans': active_loans, 'outstanding': outstanding,
            'risk': my_risk, 'gold_points': int(gold_pts), 'nssf_contrib': float(nssf_c)}

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected.")
        return

    st.write("#### 🔍 Member Profile Search")
    name_query = st.text_input("Search by name", placeholder="e.g. Nakato Sarah")
    if name_query:
        all_customers = get_customers(sacco_id)
        matches = [c for c in all_customers if name_query.lower() in c['name'].lower()]
        if not matches:
            st.warning(f"No customer found matching '{name_query}'.")
        else:
            if len(matches) > 1:
                match_map   = {f"{c['name']} ({c['phone']})": c['id'] for c in matches}
                pick        = st.selectbox("Multiple matches — select one", list(match_map.keys()))
                customer_id = match_map[pick]
            else:
                customer_id = matches[0]['id']
            info = get_customer_insight(customer_id, sacco_id)
            c    = info['customer']
            tier = get_tier(info['gold_points'])
            col1, col2 = st.columns([2,1])
            with col1:
                st.write(f"**{c['name']}** — {c['member_type']} | {c['occupation'] or '—'}")
                st.write(f"📞 {c['phone']} | 📍 {c['village'] or '—'}, {c['parish'] or '—'}")
                if c['nssf_registered']:
                    st.success(f"🇺🇬 NSSF Registered — {c['nssf_number'] or 'Number not captured'}")
                else:
                    st.warning("⚠️ Not NSSF registered")
            with col2:
                st.metric("Gold Points",   f"{info['gold_points']:,}")
                st.caption(tier)
                st.metric("NSSF Contrib.", f"UGX {info['nssf_contrib']:,.0f}")
                if info['savings_balance'] is not None:
                    st.metric("Savings",   f"UGX {info['savings_balance']:,.0f}")
                st.metric("Active Loans",  len(info['active_loans']), f"UGX {info['outstanding']:,.0f}")
            if info['risk']:
                for r in info['risk']:
                    st.error(f"⚠️ Loan #{r['loan_id']} — Risk: **{r['risk']}** | {r['missed_installments']} missed | {r['days_overdue']} days overdue")
            elif info['active_loans']:
                st.success("✅ No missed installments on active loans.")
        st.divider()

    st.write("#### 📊 Daily Intelligence Brief")
    with st.spinner("Analysing data..."):
        summary, insights = generate_local_insights(sacco_id)
    for insight in insights:
        st.markdown(insight)
    with st.expander("📋 View full data context"):
        st.text(summary)

    st.divider()
    st.write("#### 🤖 Ask the AI Analyst")
    st.caption("Ask anything about your SACCO — loans, savings, NSSF, collections, risk.")
    cols = st.columns(2)
    selected_q = None
    for i, q in enumerate(SUGGESTED_QUESTIONS):
        if cols[i % 2].button(q, key=f"sq_{i}"):
            selected_q = q
    question = st.text_input("Or type your own question", value=selected_q or "",
                              placeholder="e.g. Which members are at risk of defaulting this month?")
    if st.button("Ask AI", type="primary") and question:
        with st.spinner("Claude is analysing your SACCO data..."):
            answer, error = ask_ai(question, summary)
        if error:
            st.warning(error)
        elif answer:
            st.markdown("**AI Analyst:**")
            st.success(answer)

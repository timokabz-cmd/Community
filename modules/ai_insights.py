import streamlit as st
import requests
from database import get_db_connection
from modules.analytics import compute_risk_scores, get_category_breakdown
from modules.loans import get_upcoming_installments

def build_data_summary():
    """Pulls cross-referenced stats from customers, loans, savings, and risk data into a compact text block — this is what powers both the rule-based insights and the AI Q&A context."""
    conn = get_db_connection()
    total_customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    members = conn.execute("SELECT COUNT(*) FROM customers WHERE member_type='Member'").fetchone()[0]
    outsiders = total_customers - members
    active_loans = conn.execute("SELECT COUNT(*) FROM loans WHERE status='Active'").fetchone()[0]
    outstanding = conn.execute("SELECT COALESCE(SUM(balance),0) FROM loans WHERE status='Active'").fetchone()[0]
    total_savings = conn.execute("SELECT COALESCE(SUM(balance),0) FROM savings_accounts").fetchone()[0]
    conn.close()

    risk_scores = compute_risk_scores()
    high_risk = [r for r in risk_scores if r['risk'] == 'High']
    upcoming = get_upcoming_installments(days=7)

    lines = [
        f"Total customers: {total_customers} ({members} members, {outsiders} outsiders/non-members).",
        f"Active loans: {active_loans}. Total outstanding balance: UGX {outstanding:,.0f}.",
        f"Total member savings held: UGX {total_savings:,.0f}.",
        f"High-risk borrowers: {len(high_risk)}.",
    ]
    for r in high_risk[:10]:
        lines.append(
            f" - {r['customer']} ({r['occupation'] or 'unspecified'}): balance UGX {r['balance']:,.0f}, "
            f"{r['missed_installments']} missed installment(s), {r['days_overdue']} days overdue, "
            f"savings UGX {r['savings_balance']:,.0f}."
        )
    lines.append(f"Repayments due in the next 7 days: {len(upcoming)}.")
    for u in upcoming[:10]:
        lines.append(f" - {u['customer_name']}: UGX {u['due_amount'] - u['paid_amount']:,.0f} due {u['due_date']}.")
    return "\n".join(lines)

def generate_local_insights():
    """Rule-based 'AI' summary — works with zero external API key."""
    summary = build_data_summary()
    risk_scores = compute_risk_scores()
    high_risk_count = len([r for r in risk_scores if r['risk'] == 'High'])

    insights = []
    if high_risk_count > 0:
        insights.append(
            f"⚠️ {high_risk_count} borrower(s) are high-risk — consider prioritizing follow-up calls "
            "or field visits this week."
        )
    else:
        insights.append("✅ No high-risk borrowers detected right now.")

    breakdown, _ = get_category_breakdown()
    with_balances = [b for b in breakdown if b['outstanding'] and b['outstanding'] > 0]
    if with_balances:
        biggest = max(with_balances, key=lambda b: b['outstanding'])
        insights.append(
            f"📊 Your largest concentration of outstanding debt is in the "
            f"'{biggest['occupation'] or 'unspecified'}' category — worth checking for concentration risk."
        )

    return summary, insights

def ask_ai(question, context):
    """Optional: sends the question + data summary to the Anthropic API for a natural-language answer. Requires ANTHROPIC_API_KEY in the app's Secrets."""
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None, (
            "No ANTHROPIC_API_KEY found in this app's Secrets. Add one in "
            "Streamlit Cloud → Manage app → Settings → Secrets to enable natural-language Q&A. "
            "The rule-based insights above still work without it."
        )

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 500,
                "messages": [{
                    "role": "user",
                    "content": (
                        "You are a SACCO operations analyst. Using only the data below, "
                        "answer the question concisely and practically for a Ugandan community "
                        "lender's admin.\n\nDATA:\n" + context + "\n\nQUESTION: " + question
                    ),
                }],
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
        return text, None
    except Exception as e:
        return None, f"AI request failed: {e}"

def render():
    st.write("#### 🤖 AI Insights")
    st.caption("Cross-references customers, loans, savings, and risk data across the whole system.")

    summary, insights = generate_local_insights()
    for line in insights:
        st.write(line)

    with st.expander("View the raw data summary used for this analysis"):
        st.text(summary)

    st.write("#### Ask a Question")
    st.caption(
        "e.g. 'Which borrowers should I follow up with this week?' or 'How healthy is our savings-to-loan ratio?' "
        "Needs an ANTHROPIC_API_KEY in Secrets for a written answer."
    )
    question = st.text_input("Your question")
    if st.button("Ask AI") and question:
        with st.spinner("Analyzing..."):
            answer, error = ask_ai(question, summary)
        if error:
            st.warning(error)
        else:
            st.write(answer)

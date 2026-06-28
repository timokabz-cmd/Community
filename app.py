import streamlit as pd
import streamlit as st
import pandas as pd
from database import init_db, get_db_connection, record_repayment

# Initialize system database
init_db()

st.set_page_config(page_title="SaccoOS - Recovery & Ledger Engine", layout="wide")

# App Header
st.title("📊 SaccoOS: Recovery & Ledger Dashboard")
st.caption("Active monitoring engine for Tier-4 micro-lenders and community SACCOs.")
st.markdown("---")

# Sidebar - Live Simulation Tool
st.sidebar.header("📱 Live Mobile Money Loop Simulation")
st.sidebar.markdown("Simulate an incoming direct API payment webhook from MTN/Airtel.")

# Fetch active loans for selection dropdown
conn = get_db_connection()
loans_df = pd.read_sql_query('''
    SELECT l.id as loan_id, m.name, m.phone, l.amount_owed, l.risk_level 
    FROM loans l JOIN members m ON l.member_id = m.id 
    WHERE l.status != 'Cleared'
''', conn)
conn.close()

if not loans_df.empty:
    selected_loan_label = st.sidebar.selectbox(
        "Select Target Borrower",
        options=loans_df.index,
        format_func=lambda x: f"{loans_df.loc[x, 'name']} (Owes: UGX {loans_df.loc[x, 'amount_owed']:,})"
    )
    
    loan_record = loans_df.loc[selected_loan_label]
    sim_amount = st.sidebar.number_input("Payment Amount (UGX)", min_value=1000, value=int(loan_record['amount_owed']), step=50000)

    if st.sidebar.button("⚡ Simulate MoMo API Hook Execution"):
        success, message = record_repayment(int(loan_record['loan_id']), float(sim_amount), loan_record['phone'])
        if success:
            st.sidebar.success(message)
            
            # Simulated Instant Notifications Showcase
            st.toast(f"💬 SMS Sent to Customer: Received UGX {sim_amount:,}.", icon="✉️")
            st.toast(f"🔔 WhatsApp Alert to Owner: {loan_record['name']} paid UGX {sim_amount:,}.", icon="📲")
else:
    st.sidebar.info("All current active dummy loans are cleared.")

# --- MAIN DASHBOARD INTERFACE ---

# 1. High-Level Recovery Metrics
conn = get_db_connection()
total_portfolio = conn.execute("SELECT SUM(amount_disbursed) FROM loans").fetchone()[0] or 0
total_outstanding = conn.execute("SELECT SUM(amount_owed) FROM loans").fetchone()[0] or 0
high_risk_count = conn.execute("SELECT COUNT(*) FROM loans WHERE risk_level = 'High' AND status = 'Active'").fetchone()[0] or 0
total_collected_today = conn.execute("SELECT SUM(amount) FROM ledger WHERE account_debit = 'Mobile Money Escrow A/C'").fetchone()[0] or 0
conn.close()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Outstanding Portfolio", f"UGX {total_outstanding:,.0f}")
with col2:
    st.metric("Collected via Automated Loop Today", f"UGX {total_collected_today:,.0f}", delta=f"UGX {total_collected_today:,.0f}")
with col3:
    st.metric("High-Risk Accounts Flagged", int(high_risk_count), delta_color="inverse")
with col4:
    st.metric("Total System Portfolio Value", f"UGX {total_portfolio:,.0f}")

st.markdown("### 🚨 Recovery Watchlist & Portfolio Health")

# 2. Risk Tracking Table Layout
conn = get_db_connection()
portfolio_query = '''
    SELECT l.id as [Loan ID], m.name as [Borrower], m.phone as [Contact Phone], 
           l.amount_disbursed as [Principal], l.amount_owed as [Remaining Balance], 
           l.due_date as [Expected Pay Date], l.risk_level as [Risk Assessment]
    FROM loans l JOIN members m ON l.member_id = m.id
    WHERE l.status != 'Cleared'
    ORDER BY CASE l.risk_level WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END
'''
portfolio_df = pd.read_sql_query(portfolio_query, conn)
conn.close()

if not portfolio_df.empty:
    # Stylize the table rows to make risk categories pop instantly
    def color_risk(val):
        color = '#ff4b4b' if val == 'High' else ('#ffa500' if val == 'Medium' else '#2e7d32')
        return f'color: {color}; font-weight: bold;'
    
    st.dataframe(portfolio_df.style.map(color_risk, subset=['Risk Assessment']), use_container_width=True, hide_index=True)
else:
    st.success("🎉 Beautiful! No outstanding arrears found on the portfolio dashboard.")

# 3. Real-Time Immutable Ledger Auditing Panel
st.markdown("### 🔒 Live Double-Entry Financial Ledger (Un-deletable Trail)")
st.info("System Integrity Guard: Every action below is an irreversible balance transaction mapped directly to accounting entities.")

conn = get_db_connection()
ledger_df = pd.read_sql_query('SELECT timestamp as [Timestamp], account_debit as [Debit (DR Account)], account_credit as [Credit (CR Account)], amount as [Amount Transactioned], narration as [Audit Narration/Reference] FROM ledger ORDER BY id DESC', conn)
conn.close()

if not ledger_df.empty:
    st.table(ledger_df)
else:
    st.caption("No financial events have hit the engine ledger yet today.")

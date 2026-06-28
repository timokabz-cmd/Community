import streamlit as st
import pandas as pd
import plotly.express as px
from database import init_db, get_db_connection, add_new_member, issue_loan_request, update_loan_status, process_manual_payment

# Initialize underlying database configuration
init_db()

st.set_page_config(page_title="SaccoOS - Enterprise Workspace Matrix", layout="wide")

# Top Header Architecture
st.title("🏛️ SaccoOS Enterprise Command Center")
st.caption("Active Financial Management Systems Architecture for Tier-4 Credit Co-Operatives.")
st.markdown("---")

# 👥 Role-Based Workspace Matrix Selector (Primary UI Controller)
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=70)
st.sidebar.markdown("### **User Access Control**")
current_workspace = st.sidebar.radio(
    "Switch Current Workspace Profile:",
    ["📝 Office Operations (Staff)", "🏢 Executive Management", "📊 Business Intelligence & Analytics"]
)
st.sidebar.markdown("---")

# ====================================================================
# 🚀 WORKSPACE 1: OFFICE OPERATIONS (Staff Workspace)
# ====================================================================
if current_workspace == "📝 Office Operations (Staff)":
    st.header("📝 Front-Office Operations Workspace")
    st.info("Authorized Workflow Panel: Tailored for data verification, intake registrations, and instant cash management.")
    
    tab1, tab2, tab3 = st.tabs(["👥 Member Registration & Lookup", "💰 New Loan Origination", "⚡ Counter Cash Counter"])
    
    with tab1:
        st.subheader("Register New SACCO Member")
        with st.form("new_member_form"):
            col1, col2 = st.columns(2)
            with col1:
                m_name = st.text_input("Full Names (As on National ID)")
                m_phone = st.text_input("Mobile Phone (Primary Connection)")
            with col2:
                m_nid = st.text_input("National Identification Number (NIN)")
                m_savings = st.number_input("Opening Capital Savings Deposit (UGX)", min_value=0, step=50000)
            
            submit_member = st.form_submit_button("💾 Save Member to Database Master Table")
            if submit_member:
                if m_name and m_phone:
                    success, message = add_new_member(m_name, m_phone, m_nid, m_savings)
                    if success: st.success(message)
                    else: st.error(message)
                else: st.warning("Name and Phone fields are required inputs.")
                
        st.markdown("### Quick System Member Directory Lookup")
        conn = get_db_connection()
        members_df = pd.read_sql_query("SELECT id, name, phone, national_id, savings_balance, shares_balance FROM members", conn)
        conn.close()
        st.dataframe(members_df, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Record New Client Loan Application File")
        conn = get_db_connection()
        m_list = pd.read_sql_query("SELECT id, name FROM members", conn)
        conn.close()
        
        if not m_list.empty:
            with st.form("loan_origination_form"):
                selected_member_row = st.selectbox("Select Target Applicant Account", options=m_list.index, format_func=lambda x: m_list.loc[x, 'name'])
                l_type = st.selectbox("Loan Product Classification", ["Business Expansion", "Agricultural Input", "Emergency Support Line", "Asset Development"])
                l_amount = st.number_input("Requested Principal Amount (UGX)", min_value=100000, step=100000)
                l_collateral = st.text_area("Itemized Collateral Securities Verification Details")
                l_duration = st.slider("Term Length (In Months)", 1, 24, 6)
                
                submit_loan = st.form_submit_button("📑 Route Request to Management Approval Queue")
                if submit_loan:
                    issue_loan_request(int(m_list.loc[selected_member_row, 'id']), l_type, l_amount, l_collateral, l_duration)
                    st.success("Loan successfully routed to Executive approval queue.")
        else:
            st.warning("Register a member before creating loan files.")

    with tab3:
        st.subheader("Process Counter Over-The-Counter Cash Payments")
        conn = get_db_connection()
        active_loans = pd.read_sql_query('''
            SELECT l.id, m.name, l.amount_owed 
            FROM loans l JOIN members m ON l.member_id = m.id WHERE l.status='Active'
        ''', conn)
        conn.close()
        
        if not active_loans.empty:
            with st.form("manual_payment_form"):
                sel_loan = st.selectbox("Select Paying Borrower Profile", options=active_loans.index, format_func=lambda x: f"{active_loans.loc[x, 'name']} (Balance: {active_loans.loc[x, 'amount_owed']:,})")
                p_amount = st.number_input("Cash Tendered Amount (UGX)", min_value=1000, step=50000)
                p_operator = st.text_input("Acting Staff Member Name (Audit Trail Sign-off)")
                
                submit_pay = st.form_submit_button("⚡ Execute Double-Entry Ledger Movement")
                if submit_pay:
                    if p_operator:
                        ok, msg = process_manual_payment(int(active_loans.loc[sel_loan, 'id']), p_amount, p_operator)
                        if ok: st.success(msg)
                        else: st.error(msg)
                    else: st.warning("Authorized Operator Sign-off required.")
        else:
            st.info("No active outstanding loans to process counter payments for.")

# ====================================================================
# 🏢 WORKSPACE 2: EXECUTIVE MANAGEMENT (Control Workspace)
# ====================================================================
elif current_workspace == "🏢 Executive Management":
    st.header("🏢 Executive Management Oversight Board")
    st.warning("Privileged Operations Area: Core Portfolio Risk parameters, Credit Authorizations, and Corporate Risk Assessment KPIs.")
    
    # Financial Analytics Rollups Calculation
    conn = get_db_connection()
    total_savings = conn.execute("SELECT SUM(savings_balance) FROM members").fetchone()[0] or 0
    total_shares = conn.execute("SELECT SUM(shares_balance) FROM members").fetchone()[0] or 0
    total_disbursed = conn.execute("SELECT SUM(amount_disbursed) FROM loans WHERE status='Active'").fetchone()[0] or 0
    total_owed = conn.execute("SELECT SUM(amount_owed) FROM loans WHERE status='Active'").fetchone()[0] or 0
    high_risk_portfolio = conn.execute("SELECT SUM(amount_owed) FROM loans WHERE risk_level='High' AND status='Active'").fetchone()[0] or 0
    conn.close()
    
    # Calculate Portfolio at Risk Ratio (PAR %)
    par_ratio = (high_risk_portfolio / total_owed * 100) if total_owed > 0 else 0.0
    
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Total Member Asset Savings", f"UGX {total_savings:,.0f}")
    with m2: st.metric("Active Outstanding Book Assets", f"UGX {total_owed:,.0f}")
    with m3: st.metric("Portfolio At Risk (PAR %)", f"{par_ratio:.2f}%", delta="Target max < 5%", delta_color="inverse")
    with m4: st.metric("Total Cooperative Shares Capital", f"UGX {total_shares:,.0f}")
        
    st.markdown("---")
    st.subheader("📋 Pending Credit Request Approvals Queue")
    
    conn = get_db_connection()
    pending_loans = pd.read_sql_query('''
        SELECT l.id, m.name, l.loan_type, l.amount_disbursed as [Requested Amount], l.collateral_details 
        FROM loans l JOIN members m ON l.member_id = m.id WHERE l.status='Pending'
    ''', conn)
    conn.close()
    
    if not pending_loans.empty:
        st.dataframe(pending_loans, use_container_width=True, hide_index=True)
        col_app1, col_app2 = st.columns(2)
        with col_app1:
            target_id = st.number_input("Target Loan ID to Process", min_value=1, step=1)
        with col_app2:
            decision = st.selectbox("Action Decision", ["Approve & Disburse Asset", "Reject Application"])
            
        if st.button("⚖️ Authorize System Record Decision Entry"):
            final_status = "Approved" if decision == "Approve & Disburse Asset" else "Rejected"
            update_loan_status(target_id, final_status)
            st.success(f"Loan record ID {target_id} processed cleanly as: {final_status}")
    else:
        st.success("🎉 No pending credit pipeline applications waiting inside the authorization queues.")

    st.markdown("### 🚨 Active Delinquency & Risk Watchlist Matrix")
    conn = get_db_connection()
    watchlist = pd.read_sql_query('''
        SELECT l.id as [Loan ID], m.name as [Borrower], m.phone as [Contact Phone], 
               l.amount_owed as [Balance Due], l.due_date as [Maturity Target], l.risk_level as [Assessed Risk Level]
        FROM loans l JOIN members m ON l.member_id = m.id WHERE l.status='Active' 
        ORDER BY CASE l.risk_level WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END
    ''', conn)
    conn.close()
    
    def highlight_risk(val):
        color = '#ff4b4b' if val == 'High' else ('#ffa500' if val == 'Medium' else '#2e7d32')
        return f'color: {color}; font-weight: bold;'
    
    if not watchlist.empty:
        st.dataframe(watchlist.style.map(highlight_risk, subset=['Assessed Risk Level']), use_container_width=True, hide_index=True)
    else:
        st.info("No active loan lines found under portfolio tracking.")

# ====================================================================
# 📊 WORKSPACE 3: DATA ANALYTICS (BI Dashboard Workspace)
# ====================================================================
else:
    st.header("📊 Business Intelligence & Advanced Data Analytics Data Engine")
    st.info("System Engine Analytics Module: Aggregating macro portfolio metrics for credit modeling and liquid profiling.")
    
    conn = get_db_connection()
    all_loans_df = pd.read_sql_query('''
        SELECT l.id, l.loan_type, l.amount_disbursed, l.amount_owed, l.amount_paid, l.risk_level, l.status
        FROM loans l
    ''', conn)
    ledger_entries_df = pd.read_sql_query("SELECT id, timestamp, amount, account_debit FROM ledger", conn)
    conn.close()
    
    if not all_loans_df.empty:
        g1, g2 = st.columns(2)
        
        with g1:
            st.markdown("### Total Outstanding Credit Exposure by Sector")
            fig_sector = px.pie(all_loans_df, values='amount_owed', names='loan_type', hole=0.4,
                                color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_sector, use_container_width=True)
            
        with g2:
            st.markdown("### Credit Book Portfolio Risk Classification Distribution")
            fig_risk = px.bar(all_loans_df, x='risk_level', y='amount_disbursed', color='status',
                              title="Volume of Capital Tranches Disbursed by Risk Categorization Profile",
                              labels={'risk_level': 'Internal Risk Matrix Tag', 'amount_disbursed':'Total Disbursed (UGX)'},
                              barmode='group')
            st.plotly_chart(fig_risk, use_container_width=True)
            
        st.markdown("### 🔒 Core Double-Entry Audit Trail Ledger Analytics Data Stream")
        conn = get_db_connection()
        full_ledger = pd.read_sql_query('''
            SELECT timestamp as [Timestamp], account_debit as [Debit (DR)], account_credit as [Credit (CR)], 
                   amount as [Tranche Amount], narration as [System Event Narration], operator_name as [Acting Staff Entity] 
            FROM ledger ORDER BY id DESC
        ''', conn)
        conn.close()
        st.dataframe(full_ledger, use_container_width=True, hide_index=True)
    else:
        st.caption("No core transaction data sets available inside the database schema matrix yet.")

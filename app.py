import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# 🗄️ CORE DATABASE ENGINE (Updated to v2 to clear old table schema errors)
DB_NAME = "sacco_v2.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # 1. Create Members Table with full updated columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            national_id TEXT,
            savings_balance REAL DEFAULT 0.0,
            shares_balance REAL DEFAULT 0.0,
            joined_date TEXT NOT NULL
        )
    ''')
    # 2. Create Loans Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            loan_type TEXT NOT NULL,
            amount_disbursed REAL NOT NULL,
            amount_owed REAL NOT NULL,
            amount_paid REAL DEFAULT 0.0,
            date_issued TEXT,
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            risk_level TEXT DEFAULT 'Low',
            collateral_details TEXT,
            FOREIGN KEY(member_id) REFERENCES members(id)
        )
    ''')
    # 3. Create General Ledger Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            loan_id INTEGER,
            account_debit TEXT NOT NULL,
            account_credit TEXT NOT NULL,
            amount REAL NOT NULL,
            narration TEXT NOT NULL,
            operator_name TEXT DEFAULT 'System Automated'
        )
    ''')
    
    # Auto-seed mock transactional data if the database is brand new
    cursor.execute("SELECT COUNT(*) FROM members")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO members (name, phone, national_id, savings_balance, shares_balance, joined_date) VALUES (?, ?, ?, ?, ?, ?)", [
            ("John Okello", "256772000111", "CM95012345XYZ", 650000, 250000, "2025-01-15"),
            ("Sarah Namubiru", "256701222333", "CF91043215ABC", 1450000, 500000, "2025-03-22"),
            ("David Mukasa", "256782444555", "CM88098765LMN", 180000, 60000, "2025-05-10"),
            ("Grace Nakato", "256752777888", "CF99071623PQR", 3000000, 1200000, "2026-02-11")
        ])
        cursor.executemany("INSERT INTO loans (member_id, loan_type, amount_disbursed, amount_owed, amount_paid, date_issued, due_date, status, risk_level, collateral_details) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
            (1, "Business Expansion", 1500000, 1100000, 400000, "2026-01-10", "2026-07-10", "Active", "Low", "Shop Inventory Kraal Receipt"),
            (2, "Agricultural Input", 3000000, 3000000, 0, "2026-02-15", "2026-05-15", "Active", "High", "Kibanja Land Agreement"),
            (3, "Emergency Support Line", 400000, 50000, 350000, "2026-06-01", "2026-07-01", "Active", "Medium", "Logbook Copy"),
            (4, "Asset Development", 5000000, 5000000, 0, None, "2027-06-28", "Pending", "Low", "Land Title Deed")
        ])
    conn.commit()
    conn.close()

def add_new_member(name, phone, national_id, initial_savings):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        joined_date = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("INSERT INTO members (name, phone, national_id, savings_balance, joined_date) VALUES (?, ?, ?, ?, ?)", (name, phone, national_id, initial_savings, joined_date))
        conn.commit()
        return True, "Member registered successfully!"
    except sqlite3.IntegrityError:
        return False, "Error: This phone number is already registered."
    finally:
        conn.close()

def issue_loan_request(member_id, loan_type, amount, collateral, duration_months):
    conn = get_db_connection()
    cursor = conn.cursor()
    due_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO loans (member_id, loan_type, amount_disbursed, amount_owed, status, risk_level, collateral_details, due_date) VALUES (?, ?, ?, ?, 'Pending', 'Low', ?, ?)", (member_id, loan_type, amount, amount, collateral, due_date))
    conn.commit()
    conn.close()
    return True

def update_loan_status(loan_id, new_status):
    conn = get_db_connection()
    cursor = conn.cursor()
    date_str = datetime.now().strftime("%Y-%m-%d")
    if new_status == "Approved":
        cursor.execute("UPDATE loans SET status = 'Active', date_issued = ? WHERE id = ?", (date_str, loan_id))
    else:
        cursor.execute("UPDATE loans SET status = ? WHERE id = ?", (new_status, loan_id))
    conn.commit()
    conn.close()

def process_manual_payment(loan_id, amount, operator):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT amount_owed, amount_paid FROM loans WHERE id = ?", (loan_id,))
    loan = cursor.fetchone()
    if not loan:
        return False, "Loan record not found."
    new_paid = loan['amount_paid'] + amount
    new_owed = max(0.0, loan['amount_owed'] - amount)
    new_status = 'Cleared' if new_owed <= 0 else 'Active'
    cursor.execute("UPDATE loans SET amount_paid = ?, amount_owed = ?, status = ? WHERE id = ?", (new_paid, new_owed, new_status, loan_id))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO ledger (timestamp, loan_id, account_debit, account_credit, amount, narration, operator_name) VALUES (?, ?, 'Cash Account/Vault', 'Loan Assets Outstanding', ?, 'Counter collection payment received', ?)", (timestamp, loan_id, amount, operator))
    conn.commit()
    conn.close()
    return True, "Payment tracked cleanly in system ledger."

# Kick off database creation on launch
init_db()

# 🏛️ WORKSPACE INTERFACE SETUP
st.set_page_config(page_title="SaccoOS Workspace", layout="wide")
st.title("🏛️ SaccoOS Workspace Center")

current_workspace = st.sidebar.radio(
    "Switch Profile Role:",
    ["📝 Office Operations (Staff)", "🏢 Executive Management", "📊 Business Intelligence & Analytics"]
)

# 1. OFFICE OPERATIONS PROFILE
if current_workspace == "📝 Office Operations (Staff)":
    st.header("📝 Front-Office Operations")
    tab1, tab2, tab3 = st.tabs(["👥 Member Registration", "💰 New Loan File", "⚡ Counter Payments"])
    
    with tab1:
        st.subheader("Register New SACCO Member")
        with st.form("new_member_form"):
            m_name = st.text_input("Full Names")
            m_phone = st.text_input("Mobile Phone")
            m_nid = st.text_input("National ID (NIN)")
            m_savings = st.number_input("Opening Savings (UGX)", min_value=0, step=50000)
            if st.form_submit_button("Save Member"):
                if m_name and m_phone:
                    success, message = add_new_member(m_name, m_phone, m_nid, m_savings)
                    if success: st.success(message)
                    else: st.error(message)
                else: st.warning("Name and phone are required fields.")
        
        conn = get_db_connection()
        members_df = pd.read_sql_query("SELECT id, name, phone, national_id, savings_balance FROM members", conn)
        conn.close()
        st.dataframe(members_df, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Record New Loan Application")
        conn = get_db_connection()
        m_list = pd.read_sql_query("SELECT id, name FROM members", conn)
        conn.close()
        if not m_list.empty:
            with st.form("loan_origination_form"):
                selected_member_row = st.selectbox("Select Target Applicant", options=m_list.index, format_func=lambda x: m_list.loc[x, 'name'])
                l_type = st.selectbox("Loan Classification", ["Business Expansion", "Agricultural Input", "Emergency Support Line", "Asset Development"])
                l_amount = st.number_input("Requested Amount (UGX)", min_value=100000, step=100000)
                l_collateral = st.text_area("Itemized Collateral Securities")
                l_duration = st.slider("Term Length (Months)", 1, 24, 6)
                if st.form_submit_button("Route to Management Approval Queue"):
                    issue_loan_request(int(m_list.loc[selected_member_row, 'id']), l_type, l_amount, l_collateral, l_duration)
                    st.success("Loan successfully routed to management.")
        else:
            st.warning("Please register a member first.")

    with tab3:
        st.subheader("Process Over-The-Counter Cash Payments")
        conn = get_db_connection()
        active_loans = pd.read_sql_query("SELECT l.id, m.name, l.amount_owed FROM loans l JOIN members m ON l.member_id = m.id WHERE l.status='Active'", conn)
        conn.close()
        if not active_loans.empty:
            with st.form("manual_payment_form"):
                sel_loan = st.selectbox("Select Paying Borrower Profile", options=active_loans.index, format_func=lambda x: f"{active_loans.loc[x, 'name']} (Owed: {active_loans.loc[x, 'amount_owed']:,})")
                p_amount = st.number_input("Cash Tendered Amount (UGX)", min_value=1000, step=50000)
                p_operator = st.text_input("Acting Staff Sign-off Name")
                if st.form_submit_button("Execute Ledger Entry"):
                    if p_operator:
                        ok, msg = process_manual_payment(int(active_loans.loc[sel_loan, 'id']), p_amount, p_operator)
                        if ok: st.success(msg)
                        else: st.error(msg)
                    else: st.warning("Staff sign-off required.")
        else:
            st.info("No active outstanding loans found.")

# 2. EXECUTIVE MANAGEMENT PROFILE
elif current_workspace == "🏢 Executive Management":
    st.header("🏢 Management Oversight Board")
    conn = get_db_connection()
    total_savings = conn.execute("SELECT SUM(savings_balance) FROM members").fetchone()[0] or 0
    total_shares = conn.execute("SELECT SUM(shares_balance) FROM members").fetchone()[0] or 0
    total_owed = conn.execute("SELECT SUM(amount_owed) FROM loans WHERE status='Active'").fetchone()[0] or 0
    high_risk = conn.execute("SELECT SUM(amount_owed) FROM loans WHERE risk_level='High' AND status='Active'").fetchone()[0] or 0
    conn.close()
    
    par_ratio = (high_risk / total_owed * 100) if total_owed > 0 else 0.0
    
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Total Asset Savings", f"UGX {total_savings:,.0f}")
    with m2: st.metric("Active Outstanding Loan Book", f"UGX {total_owed:,.0f}")
    with m3: st.metric("Portfolio At Risk (PAR %)", f"{par_ratio:.2f}%")
        
    st.markdown("---")
    st.subheader("📋 Pending Credit Approvals Queue")
    conn = get_db_connection()
    pending_loans = pd.read_sql_query("SELECT l.id, m.name, l.loan_type, l.amount_disbursed as [Amount Requested], l.collateral_details FROM loans l JOIN members m ON l.member_id = m.id WHERE l.status='Pending'", conn)
    conn.close()
    
    if not pending_loans.empty:
        st.dataframe(pending_loans, use_container_width=True, hide_index=True)
        col_app1, col_app2 = st.columns(2)
        with col_app1:
            target_id = st.number_input("Target Loan ID to Process", min_value=1, step=1)
        with col_app2:
            decision = st.selectbox("Action Decision", ["Approve", "Reject"])
        if st.button("Authorize Decision Entry"):
            final_status = "Approved" if decision == "Approve" else "Rejected"
            update_loan_status(target_id, final_status)
            st.success(f"Loan record ID {target_id} updated cleanly as: {final_status}")
    else:
        st.success("No pending credit applications waiting in queue.")

# 3. BUSINESS INTELLIGENCE & DATA ANALYTICS
else:
    st.header("📊 Business Intelligence Engine")
    conn = get_db_connection()
    all_loans_df = pd.read_sql_query("SELECT id, loan_type, amount_disbursed, amount_owed, risk_level, status FROM loans", conn)
    conn.close()
    
    if not all_loans_df.empty:
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("### Exposure by Sector")
            fig_sector = px.pie(all_loans_df, values='amount_owed', names='loan_type', hole=0.4)
            st.plotly_chart(fig_sector, use_container_width=True)
        with g2:
            st.markdown("### Risk Level Volume")
            fig_risk = px.bar(all_loans_df, x='risk_level', y='amount_disbursed', color='status', barmode='group')
            st.plotly_chart(fig_risk, use_container_width=True)
            
        st.markdown("### 🔒 Core System Audit Trail Ledger")
        conn = get_db_connection()
        full_ledger = pd.read_sql_query("SELECT timestamp, account_debit, account_credit, amount, narration, operator_name FROM ledger ORDER BY id DESC", conn)
        conn.close()
        st.dataframe(full_ledger, use_container_width=True, hide_index=True)
    else:
        st.caption("No core transaction data available inside ledger matrices yet.")

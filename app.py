import streamlit as st
from modules.auth import check_password

# 1. GATEKEEPER: Stop execution if not logged in
if not check_password():
    st.stop()

# 2. IF LOGGED IN, proceed with the rest of the application
from database import init_db
from modules.dashboard import render_dashboard
from modules.customers import render_customers
from modules.loans import render_loans
from modules.collections import render_collections
from modules.accounting import render_accounting
from modules.reporting import render_reporting

# Initialize database tables
init_db()

# 3. Page Configuration
st.set_page_config(
    layout="wide", 
    page_title="CommunityFinanceOS",
    page_icon="🏛️"
)

# 4. Sidebar Navigation Controller
st.sidebar.title("🏛️ CommunityFinanceOS")
st.sidebar.write(f"Logged in as: **{st.session_state.user}**")

menu = ["Dashboard", "Customers", "Savings", "Loans", "Collections", "Accounting", "Reporting"]
choice = st.sidebar.selectbox("Select Workspace", menu)

# Add logout button
if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()

# 5. Main Application Router
st.header(f"💼 {choice}")

if choice == "Dashboard":
    render_dashboard()

elif choice == "Customers":
    render_customers()

elif choice == "Savings":
    st.info("Savings module is currently under development.")

elif choice == "Loans":
    render_loans()

elif choice == "Collections":
    render_collections()

elif choice == "Accounting":
    render_accounting()

elif choice == "Reporting":
    render_reporting()

else:
    st.warning("Workspace not yet implemented.")

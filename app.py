import streamlit as st
from auth import check_password
from database import init_db

# 1. Page Configuration (Must be first)
st.set_page_config(layout="wide", page_title="CommunityFinanceOS", page_icon="🏛️")

# 2. Initialize Database
init_db()

# 3. Gatekeeper: Stop execution if not logged in
if not check_password():
    st.stop()

# 4. Imports for other modules
from dashboard import render_dashboard
from customers import render_customers
from loans import render_loans
from collections import render_collections
from accounting import render_accounting
from reporting import render_reporting

# 5. Sidebar Navigation
st.sidebar.title("🏛️ CommunityFinanceOS")
st.sidebar.write(f"Logged in as: **{st.session_state.user}**")

menu = ["Dashboard", "Customers", "Savings", "Loans", "Collections", "Accounting", "Reporting"]
choice = st.sidebar.selectbox("Select Workspace", menu)

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()

# 6. Router
st.header(f"💼 {choice}")

if choice == "Dashboard": render_dashboard()
elif choice == "Customers": render_customers()
elif choice == "Savings": st.info("Savings module under development.")
elif choice == "Loans": render_loans()
elif choice == "Collections": render_collections()
elif choice == "Accounting": render_accounting()
elif choice == "Reporting": render_reporting()

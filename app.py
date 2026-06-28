import streamlit as st
from database import init_db
from modules.dashboard import render_dashboard
from modules.customers import render_customers
# We will uncomment these as we finish building the modules
# from modules.loans import render_loans
# from modules.accounting import render_accounting

# 1. Initialize the system
init_db()

# 2. Page Setup
st.set_page_config(layout="wide", page_title="CommunityFinanceOS")
st.sidebar.title("🏛️ CommunityFinanceOS")

# 3. Sidebar Navigation
menu = ["Dashboard", "Customers", "Savings", "Loans", "Collections", "Accounting"]
choice = st.sidebar.selectbox("Select Workspace", menu)

# 4. Routing logic
st.header(f"💼 {choice}")

if choice == "Dashboard":
    render_dashboard()
elif choice == "Customers":
    render_customers()
elif choice == "Loans":
    st.info("Loan Engine active. Module under final integration.")
elif choice == "Accounting":
    st.info("Accounting module under construction.")
else:
    st.warning("Workspace not yet implemented.")

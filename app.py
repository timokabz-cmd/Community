import streamlit as st
from database import init_db
from modules.dashboard import render_dashboard
from modules.customers import render_customers
from modules.loans import render_loans
from modules.accounting import render_accounting

# 1. Initialize the system database once
init_db()

# 2. Page Configuration
st.set_page_config(
    layout="wide", 
    page_title="CommunityFinanceOS",
    page_icon="🏛️"
)

# 3. Sidebar Navigation Controller
st.sidebar.title("🏛️ CommunityFinanceOS")
menu = ["Dashboard", "Customers", "Savings", "Loans", "Collections", "Accounting"]
choice = st.sidebar.selectbox("Select Workspace", menu)

# 4. Main Application Router
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
    st.info("Collections module is currently under development.")

elif choice == "Accounting":
    render_accounting()

else:
    st.warning("Workspace not yet implemented.")

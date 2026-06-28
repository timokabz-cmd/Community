import streamlit as st
# Importing core database logic
from database import init_db
# Importing modularized interface components
from modules.dashboard import render_dashboard
from modules.customers import render_customers

# 1. Initialize the system database once
init_db()

# 2. Main Page Configuration
st.set_page_config(
    layout="wide", 
    page_title="CommunityFinanceOS",
    page_icon="🏛️"
)

# 3. Sidebar Navigation Controller
st.sidebar.title("Navigation")
menu = ["Dashboard", "Customers", "Accounting"]
choice = st.sidebar.selectbox("Select Workspace", menu)

# 4. Main Application Router
st.title(f"🏛️ CommunityFinanceOS - {choice}")

if choice == "Dashboard":
    render_dashboard()

elif choice == "Customers":
    render_customers()

elif choice == "Accounting":
    st.info("Accounting module is currently being mapped.")
    # render_accounting()  <-- Add this when you build the module

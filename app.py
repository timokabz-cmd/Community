import streamlit as st
from database import init_db, get_db_connection

# Initialize the database
init_db()

# Main Application Layout
st.set_page_config(layout="wide", page_title="SaccoOS")
st.title("🏛️ CommunityFinanceOS")

# Navigation
menu = ["Dashboard", "Customers", "Accounting"]
choice = st.sidebar.selectbox("Select Workspace", menu)

if choice == "Dashboard":
    st.subheader("Executive Management Overview")
    # Example of using the connection
    conn = get_db_connection()
    # Add your dashboard display logic here
    st.write("System initialized and ready.")
    conn.close()

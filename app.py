import streamlit as st
from database import init_db
from modules.customers import render_customers

init_db()
st.title("🏛️ CommunityFinanceOS")
choice = st.sidebar.selectbox("Workspace", ["Dashboard", "Customers"])

if choice == "Customers":
    render_customers()
else:
    st.write("Dashboard loading...")

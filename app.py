import streamlit as st
from database.connection import init_db
from auth.login import check_password
from modules import dashboard, customers

# 1. Setup Database
init_db()

# 2. Authentication Gate
if not check_password():
    st.stop()

# 3. Router
st.sidebar.title("🏛️ CommunityFinanceOS")
st.sidebar.write(f"Logged in as: **{st.session_state.user}**")
page = st.sidebar.selectbox("Workspace", ["Dashboard", "Customers"])

if page == "Dashboard":
    dashboard.render()
elif page == "Customers":
    customers.render()


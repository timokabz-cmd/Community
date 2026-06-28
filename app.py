import streamlit as st
from database.connection import init_db
from auth.login import verify_user, check_session # We will build these next
from modules import dashboard, customers, loans, collections, accounting

# 1. Database Init
init_db()

# 2. Page Config & Session
st.set_page_config(layout="wide", page_title="CommunityFinanceOS", page_icon="🏛️")

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# 3. Authentication Gate
if not st.session_state.authenticated:
    st.subheader("🔒 Login Required")
    user_input = st.text_input("Username")
    pwd_input  = st.text_input("Password", type="password")
    if st.button("Login"):
        user = verify_user(user_input, pwd_input)
        if user:
            st.session_state.authenticated = True
            st.session_state.user = user['username']
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.stop()

# 4. Router
st.sidebar.title("🏛️ CommunityFinanceOS")
st.sidebar.write(f"Logged in as: **{st.session_state.user}**")
menu = ["Dashboard", "Customers", "Loans", "Collections", "Accounting", "Reporting"]
choice = st.sidebar.selectbox("Select Workspace", menu)

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

st.header(f"💼 {choice}")
if   choice == "Dashboard":   dashboard.render()
elif choice == "Customers":   customers.render()
elif choice == "Loans":       loans.render()
elif choice == "Collections": collections.render()
elif choice == "Accounting":  accounting.render()

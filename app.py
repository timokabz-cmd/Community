import streamlit as st
from database import init_db
from auth import ensure_admin_account, verify_user, update_password
from modules import (
    dashboard, customers, savings, loans, guarantors, collateral,
    collections, accounting, reports, analytics, administration, ai_insights
)

st.set_page_config(layout="wide", page_title="CommunityFinanceOS", page_icon="🏛️")
init_db()
ensure_admin_account()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.subheader("🔒 Login Required")
    user_input = st.text_input("Username")
    pwd_input = st.text_input("Password", type="password")
    if st.button("Login"):
        user = verify_user(user_input, pwd_input)
        if user:
            st.session_state.authenticated = True
            st.session_state.user = user['username']
            st.rerun()
        else:
            st.error("Invalid username or password")
    st.caption("Default login: admin / admin123 — change it after your first login.")
    st.stop()

def render_account_settings():
    st.write("#### Change Password")
    new_pwd = st.text_input("New password", type="password")
    confirm_pwd = st.text_input("Confirm new password", type="password")
    if st.button("Update password"):
        if not new_pwd:
            st.error("Password cannot be empty.")
        elif new_pwd != confirm_pwd:
            st.error("Passwords don't match.")
        else:
            update_password(st.session_state.user, new_pwd)
            st.success("Password updated. Use it next time you log in.")

st.sidebar.title("🏛️ CommunityFinanceOS")
st.sidebar.write(f"Logged in as: **{st.session_state.user}**")

PAGES = {
    "🏠 Dashboard": dashboard.render,
    "👤 Customers": customers.render,
    "🏦 Savings": savings.render,
    "💰 Loans": loans.render,
    "📅 Collections": collections.render,
    "🛡 Guarantors": guarantors.render,
    "📂 Collateral": collateral.render,
    "💼 Accounting": accounting.render,
    "📈 Reports": reports.render,
    "📊 Analytics": analytics.render,
    "🤖 AI Insights": ai_insights.render,
    "⚙ Administration": administration.render,
    "🔑 Account Settings": render_account_settings,
}

choice = st.sidebar.radio("Navigate", list(PAGES.keys()))

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

st.header(choice)
PAGES[choice]()

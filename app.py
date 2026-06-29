import streamlit as st
from database import init_db
from auth import ensure_admin_account, verify_user, update_password
from modules import (
    dashboard, customers, savings, loans, guarantors, collateral,
    collections, accounting, reports, analytics, administration, ai_insights
)
from seed_data import seed_demo_data

st.set_page_config(layout="wide", page_title="CommunityFinanceOS", page_icon="🏛️")

# --- Added for Modern UI Theme ---
from style import apply_styles
apply_styles()
# ---------------------------------

init_db()
ensure_admin_account()
seed_demo_data()

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
    st.caption("Default login: admin / admin123. For a permanent custom admin password, set ADMIN_PASSWORD in this app's Secrets instead of changing it in-app.")
    st.stop()

def render_account_settings():
    st.write("#### Change Password")
    if st.session_state.user == 'admin':
        st.warning(
            "The 'admin' account always syncs to the ADMIN_PASSWORD secret when the app restarts "
            "(Streamlit Cloud → Manage app → Settings → Secrets). Changing it here will work until "
            "the next restart, then it reverts. For a permanent change, update the secret instead."
        )
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

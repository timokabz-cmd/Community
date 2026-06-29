import streamlit as st
from database import init_db
from auth import ensure_admin_account, verify_user, update_password
from modules import (
    dashboard, customers, savings, loans, guarantors, collateral,
    collections, accounting, reports, analytics, administration, ai_insights
)
from seed_data import seed_demo_data

# 1. Page config must run first
st.set_page_config(layout="wide", page_title="CommunityFinanceOS", page_icon="🏛️")

# 2. Inject the custom modern UI styles immediately after page config
from style import apply_styles
apply_styles()

# 3. Initialize database and core settings
init_db()
ensure_admin_account()
seed_demo_data()

# 4. Authentication Gateway
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

    # Removed default login credentials
    st.caption("Please log in to continue.")
    st.stop()

# 5. Account Settings Rendering Function
def render_account_settings():
    st.write("#### Change Password")

    if st.session_state.user == 'admin':
        st.info(
            "The admin password is hardcoded in auth.py. "
            "To change it permanently, edit auth.py and redeploy the app."
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

# 6. Sidebar Navigation Setup
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

# 7. Main Page Content Render
st.header(choice)
PAGES[choice]()

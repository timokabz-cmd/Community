import streamlit as st
from database import init_db
from auth import ensure_admin_account, verify_user, update_password
from seed_data import run_seed
from modules import (
    dashboard, customers, savings, loans,
    collections, accounting, reports, analytics, administration, ai_insights, sacco_profile, theme, qr_login
)
from modules.sacco_profile import get_all_saccos, get_profile

st.set_page_config(layout="wide", page_title="CommunityFinanceOS", page_icon="🏛️")
theme.inject_css()
init_db()
ensure_admin_account()

# Auto-seed the 2 demo SACCOs + 20 members on first boot, so there's nothing to
# manually upload — seed_data.py is plain text and pastes fine into GitHub's editor,
# unlike the finance.db binary file this replaces. run_seed() checks each SACCO by
# name before creating it, so this is safe to leave here permanently: once the demo
# SACCOs exist, every later boot just does a couple of quick "already exists" checks
# and does nothing else. It also means if Streamlit Cloud's storage ever gets wiped
# on a redeploy, the app repopulates itself instead of coming up empty.
try:
    run_seed()
except Exception as e:
    print(f"Seed step skipped due to an error (app still starts normally): {e}")

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.subheader("🔒 Login Required")

    # If this page was opened via a per-SACCO QR code (a ?sacco_id=X link), show
    # which SACCO it is so the person knows they're in the right place. This is
    # purely a label — it does not grant access. Access is still determined
    # entirely by the sacco_id on the authenticated user's own account, checked
    # after login, exactly as before.
    qr_sacco_id = st.query_params.get('sacco_id')
    if qr_sacco_id:
        try:
            qr_sacco = get_profile(int(qr_sacco_id))
            if qr_sacco:
                st.caption(f"📘 Logging into: **{qr_sacco['sacco_name']}**")
        except (ValueError, TypeError):
            pass  # malformed or unrecognized sacco_id in the URL — just skip the caption

    user_input = st.text_input("Username")
    pwd_input = st.text_input("Password", type="password")
    if st.button("Login"):
        user = verify_user(user_input, pwd_input)
        if user:
            st.session_state.authenticated = True
            st.session_state.user = user['username']
            st.session_state.user_role = user['role']
            st.session_state.user_sacco_id = user['sacco_id']  # None for super-admins
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

theme.render_brand_header()
st.sidebar.write(f"Logged in as: **{st.session_state.user}** ({st.session_state.user_role})")

saccos = get_all_saccos()
is_super_admin = st.session_state.user_role == 'admin'

if not saccos:
    # Nothing exists yet — restrict the whole app to creating the first SACCO.
    st.session_state.current_sacco_id = None
    st.sidebar.warning("No SACCOs yet.")
    PAGES = {
        "🏢 SACCO Profile": sacco_profile.render,
        "🔑 Account Settings": render_account_settings,
    }
elif is_super_admin:
    # Super-admin can switch between every SACCO in the system.
    sacco_map = {(s['sacco_name'] or f"SACCO #{s['id']}"): s['id'] for s in saccos}
    labels = list(sacco_map.keys())
    current = st.session_state.get('current_sacco_id')
    default_label = next((lbl for lbl, sid in sacco_map.items() if sid == current), labels[0])
    picked_label = st.sidebar.selectbox("🏢 Current SACCO", labels, index=labels.index(default_label))
    st.session_state.current_sacco_id = sacco_map[picked_label]

    PAGES = {
        "🏠 Dashboard": dashboard.render,
        "🏢 SACCO Profile": sacco_profile.render,
        "👤 Customers": customers.render,
        "🏦 Savings": savings.render,
        "💰 Loans": loans.render,
        "📅 Collections": collections.render,
        "💼 Accounting": accounting.render,
        "📈 Reports": reports.render,
        "📊 Analytics": analytics.render,
        "🤖 AI Insights": ai_insights.render,
        "⚙ Administration": administration.render,
        "📱 Login QR Codes": qr_login.render,
        "🔑 Account Settings": render_account_settings,
    }
else:
    # Staff are locked to the one SACCO they're assigned to — no switcher.
    st.session_state.current_sacco_id = st.session_state.user_sacco_id
    assigned = next((s for s in saccos if s['id'] == st.session_state.user_sacco_id), None)
    st.sidebar.info(f"🏢 {assigned['sacco_name'] if assigned else 'No SACCO assigned'}")

    PAGES = {
        "🏠 Dashboard": dashboard.render,
        "🏢 SACCO Profile": sacco_profile.render,
        "👤 Customers": customers.render,
        "🏦 Savings": savings.render,
        "💰 Loans": loans.render,
        "📅 Collections": collections.render,
        "💼 Accounting": accounting.render,
        "📈 Reports": reports.render,
        "📊 Analytics": analytics.render,
        "🤖 AI Insights": ai_insights.render,
        "🔑 Account Settings": render_account_settings,
    }

choice = st.sidebar.radio("Navigate", list(PAGES.keys()))

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

current_id = st.session_state.get('current_sacco_id')
current_sacco = next((s for s in saccos if s['id'] == current_id), None) if current_id else None
theme.render_page_header(choice, sacco_name=current_sacco['sacco_name'] if current_sacco else None)
PAGES[choice]()

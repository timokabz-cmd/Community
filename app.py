import streamlit as st
from database import init_db
from auth import (
    ensure_admin_account, verify_user, update_password,
    ROLE_SUPER_ADMIN, ROLE_SACCO_ADMIN, ROLE_STAFF
)
from seed_data import run_seed
from modules import (
    dashboard, customers, savings, loans,
    collections, accounting, reports, analytics,
    administration, ai_insights, sacco_profile, theme, qr_login,
    gold_points, nssf_admin
)
from modules.sacco_profile import get_all_saccos, get_profile

st.set_page_config(layout="wide", page_title="CommunityFinanceOS", page_icon="🏛️")
theme.inject_css()
init_db()
ensure_admin_account()

try:
    run_seed()
except Exception as e:
    print(f"Seed step skipped: {e}")

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# ── Login ─────────────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    st.subheader("🔒 Login Required")

    qr_sacco_id = st.query_params.get('sacco_id')
    if qr_sacco_id:
        try:
            qr_sacco = get_profile(int(qr_sacco_id))
            if qr_sacco:
                st.caption(f"📘 Logging into: **{qr_sacco['sacco_name']}**")
        except (ValueError, TypeError):
            pass

    user_input = st.text_input("Username")
    pwd_input  = st.text_input("Password", type="password")

    if st.button("Login"):
        user = verify_user(user_input, pwd_input)
        if user:
            st.session_state.authenticated  = True
            st.session_state.user           = user['username']
            st.session_state.user_role      = user['role']
            st.session_state.user_sacco_id  = user['sacco_id']  # None for super_admin
            st.rerun()
        else:
            st.error("Invalid username or password.")
    st.stop()

# ── Account settings page (shared across all roles) ───────────────────────────
def render_account_settings():
    st.write("#### Change Password")
    new_pwd     = st.text_input("New password", type="password")
    confirm_pwd = st.text_input("Confirm new password", type="password")
    if st.button("Update password"):
        if not new_pwd:
            st.error("Password cannot be empty.")
        elif new_pwd != confirm_pwd:
            st.error("Passwords do not match.")
        else:
            update_password(st.session_state.user, new_pwd)
            st.success("Password updated successfully.")

theme.render_brand_header()

role      = st.session_state.user_role
saccos    = get_all_saccos()

st.sidebar.write(f"👤 **{st.session_state.user}**")
st.sidebar.caption(
    "🔴 Super Admin" if role == ROLE_SUPER_ADMIN
    else "🟡 SACCO Admin" if role == ROLE_SACCO_ADMIN
    else "🟢 Staff"
)

# ── SACCO context + PAGES per role ───────────────────────────────────────────
if not saccos:
    st.session_state.current_sacco_id = None
    st.sidebar.warning("No SACCOs yet.")
    PAGES = {
        "🏢 SACCO Profile":    sacco_profile.render,
        "🔑 Account Settings": render_account_settings,
    }

elif role == ROLE_SUPER_ADMIN:
    # ── Super Admin: full switcher, every page ────────────────────────────────
    sacco_map   = {(s['sacco_name'] or f"SACCO #{s['id']}"): s['id'] for s in saccos}
    labels      = list(sacco_map.keys())
    current     = st.session_state.get('current_sacco_id')
    default_lbl = next((lbl for lbl, sid in sacco_map.items() if sid == current), labels[0])
    picked      = st.sidebar.selectbox("🏢 Current SACCO", labels, index=labels.index(default_lbl))
    st.session_state.current_sacco_id = sacco_map[picked]

    PAGES = {
        "🏠 Dashboard":        dashboard.render,
        "🏢 SACCO Profile":    sacco_profile.render,
        "👤 Customers":        customers.render,
        "🏦 Savings":          savings.render,
        "💰 Loans":            loans.render,
        "📅 Collections":      collections.render,
        "💼 Accounting":       accounting.render,
        "📈 Reports":          reports.render,
        "📊 Analytics":        analytics.render,
        "🏅 Gold Points":      gold_points.render,
        "🇺🇬 NSSF Compliance": nssf_admin.render,
        "🤖 AI Insights":      ai_insights.render,
        "⚙ Administration":   administration.render,
        "📱 Login QR Codes":   qr_login.render,
        "🔑 Account Settings": render_account_settings,
    }

elif role == ROLE_SACCO_ADMIN:
    # ── SACCO Admin: locked to own SACCO, management pages but no platform admin ──
    st.session_state.current_sacco_id = st.session_state.user_sacco_id
    assigned = next((s for s in saccos if s['id'] == st.session_state.user_sacco_id), None)
    st.sidebar.info(f"🏢 {assigned['sacco_name'] if assigned else 'No SACCO assigned'}")

    PAGES = {
        "🏠 Dashboard":        dashboard.render,
        "🏢 SACCO Profile":    sacco_profile.render,
        "👤 Customers":        customers.render,
        "🏦 Savings":          savings.render,
        "💰 Loans":            loans.render,
        "📅 Collections":      collections.render,
        "💼 Accounting":       accounting.render,
        "📈 Reports":          reports.render,
        "📊 Analytics":        analytics.render,
        "🏅 Gold Points":      gold_points.render,
        "🇺🇬 NSSF Compliance": nssf_admin.render,   # sees own SACCO only
        "🤖 AI Insights":      ai_insights.render,
        "⚙ Administration":   administration.render, # can only create staff
        "🔑 Account Settings": render_account_settings,
    }

else:
    # ── Staff: locked to own SACCO, data entry only ───────────────────────────
    st.session_state.current_sacco_id = st.session_state.user_sacco_id
    assigned = next((s for s in saccos if s['id'] == st.session_state.user_sacco_id), None)
    st.sidebar.info(f"🏢 {assigned['sacco_name'] if assigned else 'No SACCO assigned'}")

    PAGES = {
        "🏠 Dashboard":        dashboard.render,
        "👤 Customers":        customers.render,
        "🏦 Savings":          savings.render,
        "💰 Loans":            loans.render,
        "📅 Collections":      collections.render,
        "💼 Accounting":       accounting.render,
        "📈 Reports":          reports.render,
        "🏅 Gold Points":      gold_points.render,
        "🔑 Account Settings": render_account_settings,
        # No Analytics, No NSSF Compliance, No Administration, No QR Codes
    }

# ── Navigation ────────────────────────────────────────────────────────────────
choice = st.sidebar.radio("Navigate", list(PAGES.keys()))

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

current_id    = st.session_state.get('current_sacco_id')
current_sacco = next((s for s in saccos if s['id'] == current_id), None) if current_id else None
theme.render_page_header(choice, sacco_name=current_sacco['sacco_name'] if current_sacco else None)
PAGES[choice]()

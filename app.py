import streamlit as st
from database import init_db, get_db_connection
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
from modules.i18n import t, language_selector_widget, LANGUAGES, get_language

st.set_page_config(layout="wide", page_title="CommunityFinanceOS", page_icon="🏛️")
theme.inject_css()
init_db()
ensure_admin_account()

# ── Language preference column migration ──────────────────────────────────────
# Adds 'language' column to users table if not already present.
# Safe to run on every boot — checks before altering.
try:
    conn = get_db_connection()
    user_cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    if 'language' not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'")
        conn.commit()
    conn.close()
except Exception as e:
    print(f"Language column migration skipped: {e}")

try:
    run_seed()
except Exception as e:
    print(f"Seed step skipped: {e}")

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# ── Restore saved language from DB on session start ───────────────────────────
if 'language' not in st.session_state:
    st.session_state['language'] = 'en'

# ── Login ─────────────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    st.subheader(t("login_required"))

    # Language selector on login page — choice persists to account after login
    language_selector_widget()

    qr_sacco_id = st.query_params.get('sacco_id')
    if qr_sacco_id:
        try:
            qr_sacco = get_profile(int(qr_sacco_id))
            if qr_sacco:
                st.caption(f"📘 {qr_sacco['sacco_name']}")
        except (ValueError, TypeError):
            pass

    user_input = st.text_input(t("username"))
    pwd_input  = st.text_input(t("password"), type="password")

    if st.button(t("login")):
        user = verify_user(user_input, pwd_input)
        if user:
            st.session_state.authenticated = True
            st.session_state.user          = user['username']
            st.session_state.user_role     = user['role']
            st.session_state.user_sacco_id = user['sacco_id']

            # Load saved language preference from DB
            saved_lang = user['language'] if 'language' in user.keys() else 'en'
            if saved_lang and saved_lang in LANGUAGES:
                st.session_state['language'] = saved_lang
            # If language was changed on login page before login, save it
            elif st.session_state.get('language', 'en') != (saved_lang or 'en'):
                try:
                    conn = get_db_connection()
                    conn.execute(
                        "UPDATE users SET language=? WHERE username=?",
                        (st.session_state['language'], user['username'])
                    )
                    conn.commit()
                    conn.close()
                except Exception:
                    pass

            st.rerun()
        else:
            st.error(t("invalid_login"))
    st.stop()

# ── Save language preference when it changes ──────────────────────────────────
def _persist_language(lang_code):
    """Write language choice to DB so it's remembered next login."""
    try:
        conn = get_db_connection()
        conn.execute(
            "UPDATE users SET language=? WHERE username=?",
            (lang_code, st.session_state.user)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

# ── Account settings ──────────────────────────────────────────────────────────
def render_account_settings():
    st.write(f"#### {t('change_password')}")
    new_pwd     = st.text_input(t("new_password"),     type="password")
    confirm_pwd = st.text_input(t("confirm_password"), type="password")
    if st.button(t("update_password")):
        if not new_pwd:
            st.error(t("error_name_phone_required"))
        elif new_pwd != confirm_pwd:
            st.error(t("passwords_no_match"))
        else:
            update_password(st.session_state.user, new_pwd)
            st.success(t("password_updated"))

theme.render_brand_header()

role   = st.session_state.user_role
saccos = get_all_saccos()

st.sidebar.write(f"👤 **{st.session_state.user}**")
st.sidebar.caption(
    t("super_admin_label") if role == ROLE_SUPER_ADMIN
    else t("sacco_admin_label") if role == ROLE_SACCO_ADMIN
    else t("staff_label")
)

# ── SACCO context + PAGES per role ───────────────────────────────────────────
if not saccos:
    st.session_state.current_sacco_id = None
    st.sidebar.warning(t("no_data_yet"))
    PAGES = {
        t("nav_sacco_profile"):     sacco_profile.render,
        t("nav_account_settings"):  render_account_settings,
    }

elif role == ROLE_SUPER_ADMIN:
    sacco_map   = {(s['sacco_name'] or f"SACCO #{s['id']}"): s['id'] for s in saccos}
    labels      = list(sacco_map.keys())
    current     = st.session_state.get('current_sacco_id')
    default_lbl = next((lbl for lbl, sid in sacco_map.items() if sid == current), labels[0])
    picked      = st.sidebar.selectbox(t("current_sacco"), labels, index=labels.index(default_lbl))
    st.session_state.current_sacco_id = sacco_map[picked]

    PAGES = {
        t("nav_dashboard"):         dashboard.render,
        t("nav_sacco_profile"):     sacco_profile.render,
        t("nav_customers"):         customers.render,
        t("nav_savings"):           savings.render,
        t("nav_loans"):             loans.render,
        t("nav_collections"):       collections.render,
        t("nav_accounting"):        accounting.render,
        t("nav_reports"):           reports.render,
        t("nav_analytics"):         analytics.render,
        t("nav_gold_points"):       gold_points.render,
        t("nav_nssf"):              nssf_admin.render,
        t("nav_ai_insights"):       ai_insights.render,
        t("nav_administration"):    administration.render,
        t("nav_qr_codes"):          qr_login.render,
        t("nav_account_settings"):  render_account_settings,
    }

elif role == ROLE_SACCO_ADMIN:
    st.session_state.current_sacco_id = st.session_state.user_sacco_id
    assigned = next((s for s in saccos if s['id'] == st.session_state.user_sacco_id), None)
    st.sidebar.info(f"🏢 {assigned['sacco_name'] if assigned else '—'}")

    PAGES = {
        t("nav_dashboard"):         dashboard.render,
        t("nav_sacco_profile"):     sacco_profile.render,
        t("nav_customers"):         customers.render,
        t("nav_savings"):           savings.render,
        t("nav_loans"):             loans.render,
        t("nav_collections"):       collections.render,
        t("nav_accounting"):        accounting.render,
        t("nav_reports"):           reports.render,
        t("nav_analytics"):         analytics.render,
        t("nav_gold_points"):       gold_points.render,
        t("nav_nssf"):              nssf_admin.render,
        t("nav_ai_insights"):       ai_insights.render,
        t("nav_administration"):    administration.render,
        t("nav_account_settings"):  render_account_settings,
    }

else:
    st.session_state.current_sacco_id = st.session_state.user_sacco_id
    assigned = next((s for s in saccos if s['id'] == st.session_state.user_sacco_id), None)
    st.sidebar.info(f"🏢 {assigned['sacco_name'] if assigned else '—'}")

    PAGES = {
        t("nav_dashboard"):         dashboard.render,
        t("nav_customers"):         customers.render,
        t("nav_savings"):           savings.render,
        t("nav_loans"):             loans.render,
        t("nav_collections"):       collections.render,
        t("nav_accounting"):        accounting.render,
        t("nav_reports"):           reports.render,
        t("nav_gold_points"):       gold_points.render,
        t("nav_account_settings"):  render_account_settings,
    }

# ── Navigation ────────────────────────────────────────────────────────────────
choice = st.sidebar.radio(t("navigate"), list(PAGES.keys()))

if st.sidebar.button(t("logout")):
    _persist_language(st.session_state.get('language', 'en'))
    st.session_state.authenticated = False
    st.rerun()

current_id    = st.session_state.get('current_sacco_id')
current_sacco = next((s for s in saccos if s['id'] == current_id), None) if current_id else None
theme.render_page_header(choice, sacco_name=current_sacco['sacco_name'] if current_sacco else None)
PAGES[choice]()

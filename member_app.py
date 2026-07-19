"""
member_app.py  —  CommunityFinanceOS Member Portal

Second Streamlit app in the same repo. Deploys alongside app.py on
Streamlit Cloud as a separate app pointing to the same finance.db.

To deploy on Streamlit Cloud:
  1. Go to share.streamlit.io → New app
  2. Same repo, same branch
  3. Main file path: member_app.py
  4. Give it a different subdomain e.g. sacco-member.streamlit.app

Member login: phone number + 4-digit PIN
First-time: member sets their own PIN after phone verification
"""

import streamlit as st
from datetime import date, datetime
from database import init_db
from modules.member_auth import (
    find_member_by_phone, has_pin, is_first_login,
    set_pin, verify_pin, record_login, get_member_data
)
from modules.nssf_engine import get_tier, TIERS
from modules.i18n import t, language_selector_widget, LANGUAGES

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title  = "My SACCO",
    page_icon   = "🏦",
    layout      = "centered",   # centred column — feels like a mobile app
    initial_sidebar_state = "collapsed",
)

init_db()

# ─────────────────────────────────────────────────────────────────────────────
# Design tokens — green + gold on warm paper, mobile-first
# ─────────────────────────────────────────────────────────────────────────────
GREEN_DARK   = "#1E5C35"   # deep forest green — primary brand
GREEN        = "#2E7D4F"   # mid green — buttons, headers
GREEN_SOFT   = "#E8F5EE"   # light green — positive backgrounds
GOLD         = "#C99A3B"   # stamped gold — accent, NSSF, points
GOLD_SOFT    = "#FDF6E3"   # warm gold tint — card backgrounds
PAPER        = "#FAF8F3"   # warm white — page background
INK          = "#1A2E1A"   # near-black with green undertone — body text
BORDER       = "#C8DDD0"   # soft green-grey border
MUTED        = "#6B8C74"   # muted green — captions, secondary text
RED_SOFT     = "#FDF0ED"   # overdue/warning background
RED          = "#B0492E"   # overdue/warning ink

def _inject_member_css():
    st.markdown(f"""
    <style>
    /* Page background */
    .stApp {{ background: {PAPER}; }}

    /* Hide Streamlit chrome on mobile */
    #MainMenu, footer, header {{ visibility: hidden; }}
    .block-container {{ padding: 1rem 1rem 4rem 1rem !important; max-width: 480px; margin: auto; }}

    /* Typography */
    body, p, div, span, label {{
        color: {INK};
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }}

    /* Green primary button */
    .stButton > button[kind="primary"] {{
        background: {GREEN} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        padding: 0.65rem 1.5rem !important;
        width: 100%;
        transition: background 0.2s;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: {GREEN_DARK} !important;
    }}

    /* Secondary button */
    .stButton > button:not([kind="primary"]) {{
        background: transparent !important;
        color: {GREEN} !important;
        border: 1.5px solid {GREEN} !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        width: 100%;
    }}

    /* Inputs */
    .stTextInput > div > div > input {{
        border-radius: 8px !important;
        border: 1.5px solid {BORDER} !important;
        background: #ffffff !important;
        font-size: 1rem !important;
        padding: 0.6rem 0.8rem !important;
    }}
    .stTextInput > div > div > input:focus {{
        border-color: {GREEN} !important;
        box-shadow: 0 0 0 3px {GREEN_SOFT} !important;
    }}

    /* Metric values */
    [data-testid="stMetricValue"] {{
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        font-variant-numeric: tabular-nums;
        color: {INK} !important;
    }}

    /* Dividers */
    hr {{ border-color: {BORDER} !important; margin: 1.2rem 0 !important; }}
    </style>
    """, unsafe_allow_html=True)

def _card(content_html, bg=GOLD_SOFT, border=GOLD, padding="1.1rem 1.2rem"):
    st.markdown(f"""
    <div style="
        background:{bg};
        border:1.5px solid {border};
        border-radius:12px;
        padding:{padding};
        margin-bottom:0.8rem;
    ">{content_html}</div>
    """, unsafe_allow_html=True)

def _section(title, emoji=""):
    st.markdown(f"""
    <div style="
        display:flex;align-items:center;gap:0.5rem;
        margin:1.4rem 0 0.6rem 0;
        padding-bottom:0.4rem;
        border-bottom:2px solid {GREEN};
    ">
      <span style="font-size:1.1rem;">{emoji}</span>
      <span style="font-weight:700;font-size:1rem;color:{GREEN_DARK};">{title}</span>
    </div>
    """, unsafe_allow_html=True)

def _tier_bar(points, next_thresh, color=GOLD):
    pct = min(int(points / next_thresh * 100), 100) if next_thresh > 0 else 100
    st.markdown(f"""
    <div style="background:{BORDER};border-radius:6px;height:10px;margin:0.4rem 0 0.2rem;">
      <div style="background:{color};border-radius:6px;height:10px;width:{pct}%;transition:width 0.4s;"></div>
    </div>
    <div style="font-size:0.73rem;color:{MUTED};">{pct}% to next tier</div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Session state defaults
# ─────────────────────────────────────────────────────────────────────────────
for key, default in [
    ('member_authenticated', False),
    ('member_customer_id',   None),
    ('member_phone',         None),
    ('language',             'en'),
    ('active_tab',           'home'),
]:
    if key not in st.session_state:
        st.session_state[key] = default

_inject_member_css()

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN & PIN SETUP
# ─────────────────────────────────────────────────────────────────────────────
def render_login():
    # Logo / brand
    st.markdown(f"""
    <div style="text-align:center;padding:2rem 0 1.5rem;">
      <div style="
          display:inline-flex;align-items:center;justify-content:center;
          width:3.5rem;height:3.5rem;border-radius:1rem;
          background:{GREEN};margin-bottom:0.7rem;
      ">
        <span style="font-size:1.8rem;">🏦</span>
      </div>
      <div style="font-size:1.4rem;font-weight:700;color:{GREEN_DARK};">My SACCO</div>
      <div style="font-size:0.82rem;color:{MUTED};margin-top:0.2rem;">
        CommunityFinanceOS · Member Portal
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Language selector
    language_selector_widget()
    st.divider()

    st.markdown(f"<div style='font-weight:600;color:{GREEN_DARK};margin-bottom:0.3rem;'>{t('username')} (Phone Number)</div>", unsafe_allow_html=True)
    phone = st.text_input(
        "phone_input",
        placeholder="e.g. 0772123456",
        label_visibility="collapsed"
    )

    if st.button(t("login"), type="primary"):
        if not phone.strip():
            st.error("Please enter your phone number.")
            return
        member = find_member_by_phone(phone.strip())
        if not member:
            st.error("Phone number not found. Contact your SACCO to confirm your registration.")
            return
        st.session_state.member_phone       = phone.strip()
        st.session_state.member_customer_id = member['id']

        if not has_pin(member['id']):
            st.session_state.active_tab = 'set_pin'
        else:
            st.session_state.active_tab = 'verify_pin'
        st.rerun()

    st.markdown(f"""
    <div style="text-align:center;margin-top:2rem;font-size:0.78rem;color:{MUTED};">
      🔒 Your data is protected under Uganda's Data Protection and Privacy Act 2019.<br>
      🇺🇬 NSSF-registered members earn Gold Points on every deposit.
    </div>
    """, unsafe_allow_html=True)


def render_set_pin():
    customer_id = st.session_state.member_customer_id
    conn_check  = find_member_by_phone(st.session_state.member_phone)
    name        = conn_check['name'].split()[0] if conn_check else "there"

    st.markdown(f"""
    <div style="text-align:center;padding:1.5rem 0 1rem;">
      <div style="font-size:2rem;">🔐</div>
      <div style="font-size:1.2rem;font-weight:700;color:{GREEN_DARK};">
        Welcome, {name}!
      </div>
      <div style="font-size:0.85rem;color:{MUTED};margin-top:0.3rem;">
        Set your 4-digit PIN to secure your account.
      </div>
    </div>
    """, unsafe_allow_html=True)

    pin1 = st.text_input("Choose a 4-digit PIN",    type="password", max_chars=4, placeholder="• • • •")
    pin2 = st.text_input("Confirm your PIN",         type="password", max_chars=4, placeholder="• • • •")

    if st.button("Set PIN & Continue", type="primary"):
        if not pin1.isdigit() or len(pin1) != 4:
            st.error("PIN must be exactly 4 digits.")
        elif pin1 != pin2:
            st.error("PINs do not match. Try again.")
        else:
            set_pin(customer_id, pin1)
            record_login(customer_id)
            st.session_state.member_authenticated = True
            st.session_state.active_tab           = 'home'
            st.rerun()

    if st.button("← Back"):
        st.session_state.active_tab = None
        st.session_state.member_customer_id = None
        st.rerun()


def render_verify_pin():
    customer_id = st.session_state.member_customer_id

    st.markdown(f"""
    <div style="text-align:center;padding:1.5rem 0 1rem;">
      <div style="font-size:2rem;">🔑</div>
      <div style="font-size:1.1rem;font-weight:700;color:{GREEN_DARK};">Enter your PIN</div>
      <div style="font-size:0.82rem;color:{MUTED};margin-top:0.2rem;">
        Phone: {st.session_state.member_phone}
      </div>
    </div>
    """, unsafe_allow_html=True)

    pin = st.text_input("4-digit PIN", type="password", max_chars=4, placeholder="• • • •", label_visibility="collapsed")

    if st.button(t("login"), type="primary"):
        if verify_pin(customer_id, pin):
            record_login(customer_id)
            st.session_state.member_authenticated = True
            st.session_state.active_tab           = 'home'
            st.rerun()
        else:
            st.error("Incorrect PIN. Try again.")

    if st.button("← Use a different phone number"):
        st.session_state.active_tab          = None
        st.session_state.member_customer_id = None
        st.session_state.member_phone        = None
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MEMBER PORTAL PAGES
# ─────────────────────────────────────────────────────────────────────────────

def render_home(d):
    customer    = d['customer']
    savings     = d['savings']
    gold_points = d['gold_points']
    nssf_total  = d['nssf_total']
    loan        = d['loan']
    sacco       = d['sacco']

    first_name  = customer['name'].split()[0]
    tier        = get_tier(gold_points)
    now_hour    = datetime.now().hour
    greeting    = "Good morning" if now_hour < 12 else "Good afternoon" if now_hour < 17 else "Good evening"

    # Greeting header
    st.markdown(f"""
    <div style="padding:0.5rem 0 1rem;">
      <div style="font-size:0.85rem;color:{MUTED};">{greeting} 👋</div>
      <div style="font-size:1.5rem;font-weight:700;color:{GREEN_DARK};">{first_name}</div>
      <div style="font-size:0.8rem;color:{GOLD};font-weight:600;margin-top:0.1rem;">{tier}</div>
    </div>
    """, unsafe_allow_html=True)

    if sacco:
        st.caption(f"📘 {sacco['sacco_name']} · {sacco['parish'] or ''}, {sacco['district'] or ''}")

    # Savings balance — hero card
    bal = savings['balance'] if savings else 0
    _card(f"""
    <div style="font-size:0.75rem;color:{MUTED};text-transform:uppercase;
                letter-spacing:0.07em;font-weight:600;">Savings Balance</div>
    <div style="font-size:2.2rem;font-weight:800;color:{GREEN_DARK};
                font-variant-numeric:tabular-nums;margin-top:0.2rem;line-height:1.1;">
        UGX {bal:,.0f}
    </div>
    <div style="font-size:0.78rem;color:{MUTED};margin-top:0.4rem;">
        {'Account #' + str(savings['id']) if savings else 'No savings account yet'}
    </div>
    """, bg=GREEN_SOFT, border=GREEN)

    # Quick stats row
    c1, c2 = st.columns(2)
    with c1:
        _card(f"""
        <div style="font-size:0.72rem;color:{MUTED};text-transform:uppercase;
                    letter-spacing:0.06em;font-weight:600;">🇺🇬 NSSF Contributions</div>
        <div style="font-size:1.2rem;font-weight:700;color:{GREEN_DARK};
                    font-variant-numeric:tabular-nums;margin-top:0.3rem;">
            UGX {nssf_total:,.0f}
        </div>
        <div style="font-size:0.72rem;color:{MUTED};margin-top:0.1rem;">all time</div>
        """, bg=GOLD_SOFT, border=GOLD)
    with c2:
        _card(f"""
        <div style="font-size:0.72rem;color:{MUTED};text-transform:uppercase;
                    letter-spacing:0.06em;font-weight:600;">🏅 Gold Points</div>
        <div style="font-size:1.2rem;font-weight:700;color:{GREEN_DARK};
                    font-variant-numeric:tabular-nums;margin-top:0.3rem;">
            {gold_points:,}
        </div>
        <div style="font-size:0.72rem;color:{GOLD};margin-top:0.1rem;font-weight:600;">{tier}</div>
        """, bg=GOLD_SOFT, border=GOLD)

    # Active loan alert
    if loan:
        next_due = None
        for s in d['schedule']:
            if s['status'] != 'Paid':
                next_due = s
                break
        _card(f"""
        <div style="font-size:0.75rem;color:{RED};text-transform:uppercase;
                    letter-spacing:0.06em;font-weight:700;">💰 Active Loan</div>
        <div style="font-size:1.1rem;font-weight:700;color:{INK};
                    font-variant-numeric:tabular-nums;margin-top:0.3rem;">
            Balance: UGX {loan['balance']:,.0f}
        </div>
        {'<div style="font-size:0.78rem;color:'+RED+';margin-top:0.3rem;">Next installment: UGX ' + f"{next_due['due_amount']-next_due['paid_amount']:,.0f} due {next_due['due_date']}" + '</div>' if next_due else ''}
        """, bg=RED_SOFT, border=RED)

    # NSSF compliance nudge
    if not customer['nssf_registered']:
        st.warning(
            "⚠️ You are not yet registered with NSSF. "
            "Register at [nssfug.org](https://www.nssfug.org) to start earning Gold Points on your deposits."
        )

    # Bottom nav hint
    st.markdown(f"""
    <div style="text-align:center;margin-top:1.5rem;
                font-size:0.78rem;color:{MUTED};">
      Use the menu below to view your savings, loan, NSSF, and Gold Points.
    </div>
    """, unsafe_allow_html=True)


def render_savings(d):
    savings  = d['savings']
    txns     = d['transactions']

    _section("My Savings", "🏦")

    if not savings:
        st.info("You don't have a savings account yet. Contact your SACCO admin to open one.")
        return

    _card(f"""
    <div style="font-size:0.75rem;color:{MUTED};text-transform:uppercase;
                letter-spacing:0.07em;font-weight:600;">Current Balance</div>
    <div style="font-size:2rem;font-weight:800;color:{GREEN_DARK};
                font-variant-numeric:tabular-nums;margin-top:0.2rem;">
        UGX {savings['balance']:,.0f}
    </div>
    <div style="font-size:0.78rem;color:{MUTED};margin-top:0.3rem;">
        Account opened: {savings['opened_date'] or '—'}
    </div>
    """, bg=GREEN_SOFT, border=GREEN)

    # Deposit stub — ready for payment gateway
    st.markdown(f"""
    <div style="
        background:#ffffff;border:1.5px dashed {BORDER};
        border-radius:10px;padding:1rem;text-align:center;
        margin-bottom:1rem;
    ">
      <div style="font-size:1.3rem;">📲</div>
      <div style="font-weight:600;color:{GREEN_DARK};margin-top:0.3rem;">Make a Deposit</div>
      <div style="font-size:0.78rem;color:{MUTED};margin-top:0.2rem;">
        Mobile money deposits coming soon.<br>
        For now, visit your SACCO or contact your agent.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Transaction history
    _section("Recent Transactions", "📋")
    if not txns:
        st.caption("No transactions recorded yet.")
        return

    for txn in txns:
        is_deposit  = txn['type'] == 'Deposit'
        color       = GREEN if is_deposit else RED
        arrow       = "↑" if is_deposit else "↓"
        bg          = GREEN_SOFT if is_deposit else RED_SOFT
        border      = GREEN if is_deposit else RED
        _card(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div style="font-weight:600;color:{INK};">{arrow} {txn['type']}</div>
            <div style="font-size:0.75rem;color:{MUTED};">
                {txn['date'] or '—'}
                {' · ' + txn['channel'] if txn['channel'] else ''}
            </div>
          </div>
          <div style="font-weight:700;color:{color};font-variant-numeric:tabular-nums;
                      font-size:1.05rem;">
            UGX {txn['amount']:,.0f}
          </div>
        </div>
        """, bg=bg, border=border, padding="0.75rem 1rem")


def render_loan(d):
    loan     = d['loan']
    schedule = d['schedule']

    _section("My Loan", "💰")

    if not loan:
        st.info("You have no active loan right now.")
        return

    paid_total   = sum(s['paid_amount'] for s in schedule)
    total_due    = loan['total_due']
    pct_paid     = int(paid_total / total_due * 100) if total_due > 0 else 0

    _card(f"""
    <div style="font-size:0.75rem;color:{MUTED};text-transform:uppercase;
                letter-spacing:0.07em;font-weight:600;">Outstanding Balance</div>
    <div style="font-size:2rem;font-weight:800;color:{GREEN_DARK};
                font-variant-numeric:tabular-nums;margin:0.2rem 0;">
        UGX {loan['balance']:,.0f}
    </div>
    <div style="font-size:0.78rem;color:{MUTED};">
        Principal: UGX {loan['principal']:,.0f} ·
        Rate: {loan['interest_rate']}% ·
        Disbursed: {loan['disbursed_date'] or '—'}
    </div>
    <div style="margin-top:0.8rem;">
      <div style="font-size:0.73rem;color:{MUTED};margin-bottom:3px;">
          Repayment progress — {pct_paid}% paid
      </div>
      <div style="background:{BORDER};border-radius:6px;height:8px;">
        <div style="background:{GREEN};border-radius:6px;height:8px;width:{pct_paid}%;"></div>
      </div>
    </div>
    """, bg=GREEN_SOFT, border=GREEN)

    _section("Repayment Schedule", "📅")
    today_str = date.today().strftime('%Y-%m-%d')
    for s in schedule:
        remaining   = s['due_amount'] - s['paid_amount']
        is_paid     = s['status'] == 'Paid'
        is_overdue  = not is_paid and s['due_date'] < today_str
        bg     = GREEN_SOFT if is_paid else RED_SOFT if is_overdue else "#ffffff"
        border = GREEN if is_paid else RED if is_overdue else BORDER
        label  = "✅ Paid" if is_paid else "🔴 Overdue" if is_overdue else "⏳ Pending"
        _card(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div style="font-weight:600;color:{INK};">
                Installment {s['installment_no']}
                <span style="font-size:0.75rem;font-weight:400;color:{MUTED};
                             margin-left:0.4rem;">{label}</span>
            </div>
            <div style="font-size:0.75rem;color:{MUTED};">Due: {s['due_date']}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-weight:700;font-variant-numeric:tabular-nums;color:{INK};">
                UGX {s['due_amount']:,.0f}
            </div>
            {'<div style="font-size:0.72rem;color:'+RED+';">UGX '+f"{remaining:,.0f}"+' remaining</div>' if not is_paid and remaining > 0 else ''}
          </div>
        </div>
        """, bg=bg, border=border, padding="0.75rem 1rem")


def render_nssf(d):
    customer      = d['customer']
    nssf_contribs = d['nssf_contribs']
    nssf_total    = d['nssf_total']

    _section("My NSSF", "🇺🇬")

    if not customer['nssf_registered']:
        _card(f"""
        <div style="font-size:1rem;font-weight:700;color:{RED};">⚠️ Not Yet Registered</div>
        <div style="font-size:0.85rem;color:{INK};margin-top:0.4rem;line-height:1.5;">
            You are not yet registered with the National Social Security Fund (NSSF).
            Registration is free and takes 2 minutes.
        </div>
        <div style="margin-top:0.8rem;">
          <a href="https://www.nssfug.org" target="_blank"
             style="background:{GREEN};color:#fff;padding:0.5rem 1.2rem;
                    border-radius:8px;text-decoration:none;font-weight:600;font-size:0.88rem;">
            Register Now →
          </a>
        </div>
        """, bg=RED_SOFT, border=RED)
        st.caption("Once registered, update your NSSF number with your SACCO admin. "
                   "You'll start earning Gold Points on every deposit automatically.")
        return

    # Registered view
    _card(f"""
    <div style="font-size:0.75rem;color:{MUTED};text-transform:uppercase;
                letter-spacing:0.07em;font-weight:600;">🇺🇬 NSSF Registered</div>
    <div style="font-size:1rem;font-weight:600;color:{GREEN_DARK};margin-top:0.3rem;">
        {customer['nssf_number'] or 'Number not yet captured — contact SACCO admin'}
    </div>
    <div style="margin-top:0.8rem;border-top:1px solid {BORDER};padding-top:0.8rem;">
      <div style="font-size:0.75rem;color:{MUTED};text-transform:uppercase;
                  letter-spacing:0.06em;font-weight:600;">Total Contributed</div>
      <div style="font-size:1.8rem;font-weight:800;color:{GOLD};
                  font-variant-numeric:tabular-nums;margin-top:0.15rem;">
          UGX {nssf_total:,.0f}
      </div>
      <div style="font-size:0.75rem;color:{MUTED};margin-top:0.1rem;">
          all time · {customer['nssf_contribution_rate'] or 5.0}% of each deposit
      </div>
    </div>
    """, bg=GOLD_SOFT, border=GOLD)

    # Consent notice
    st.markdown(f"""
    <div style="font-size:0.72rem;color:{MUTED};background:#ffffff;
                border:1px solid {BORDER};border-radius:8px;padding:0.75rem;
                margin-bottom:1rem;line-height:1.6;">
      🔒 <strong>Your data privacy:</strong> By being a member of this SACCO,
      your NSSF registration status and contribution amounts are shared with
      NSSF Uganda for social security administration purposes only.
      This is governed by Uganda's Data Protection and Privacy Act 2019.
    </div>
    """, unsafe_allow_html=True)

    _section("Contribution History", "📋")
    if not nssf_contribs:
        st.caption("No contributions recorded yet. Make a deposit to start contributing.")
        return

    for c in nssf_contribs:
        remitted = c['remitted']
        _card(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div style="font-weight:600;color:{INK};">Period: {c['period']}</div>
            <div style="font-size:0.74rem;color:{MUTED};">
                Rate: {c['contribution_rate']}% of UGX {c['gross_deposit']:,.0f} deposit ·
                {'✅ Remitted to NSSF' if remitted else '⏳ Pending remittance'}
            </div>
          </div>
          <div style="font-weight:700;color:{GOLD};font-variant-numeric:tabular-nums;">
            UGX {c['nssf_amount']:,.0f}
          </div>
        </div>
        """, bg=GOLD_SOFT, border=GOLD, padding="0.75rem 1rem")


def render_gold_points(d):
    gold_points  = d['gold_points']
    gold_history = d['gold_history']
    tier         = get_tier(gold_points)

    _section("My Gold Points", "🏅")

    # Find next tier threshold
    next_thresh = 0
    for threshold, label in reversed(TIERS):
        if gold_points < threshold:
            next_thresh = threshold

    _card(f"""
    <div style="text-align:center;padding:0.5rem 0;">
      <div style="font-size:2.5rem;font-weight:800;color:{GOLD};
                  font-variant-numeric:tabular-nums;">{gold_points:,}</div>
      <div style="font-size:1rem;font-weight:700;color:{GREEN_DARK};margin-top:0.2rem;">{tier}</div>
      {'<div style="font-size:0.78rem;color:'+MUTED+';margin-top:0.3rem;">' + str(max(next_thresh-gold_points,0)) + ' points to next tier</div>' if next_thresh > gold_points else '<div style="font-size:0.8rem;color:'+GOLD+';margin-top:0.3rem;font-weight:600;">🏆 Maximum tier reached!</div>'}
    </div>
    """, bg=GOLD_SOFT, border=GOLD)

    if next_thresh > gold_points:
        _tier_bar(gold_points, next_thresh)

    # Campaign message
    st.markdown(f"""
    <div style="
        background:linear-gradient(135deg, {GREEN_DARK} 0%, #1E4D6B 100%);
        border-radius:12px;padding:1rem 1.2rem;margin:0.8rem 0;
    ">
      <div style="color:{GOLD};font-size:0.72rem;text-transform:uppercase;
                  letter-spacing:0.1em;font-weight:600;">
          🇺🇬 Uganda National Savings Programme
      </div>
      <div style="color:#ffffff;font-size:0.95rem;font-weight:700;
                  margin:0.3rem 0 0.2rem;line-height:1.3;">
          Save with your SACCO.<br>Build with Uganda.
      </div>
      <div style="color:#B8CCDF;font-size:0.78rem;margin-top:0.3rem;line-height:1.5;">
          Every shilling you save, a piece goes to build the nation.
          Every NSSF contribution earns you Gold Points.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Tier ladder
    _section("Tier Levels", "🏆")
    tier_info = [
        ("🥉 Bronze Saver",    "0–99 pts",   "Just getting started. Every shilling counts."),
        ("🥈 Silver Patriot",  "100–299 pts", "Building momentum. Keep saving consistently."),
        ("🥇 Gold Champion",   "300–599 pts", "A proven saver. NSSF is growing with you."),
        ("🏆 National Builder","600+ pts",    "An exceptional patriot building Uganda's future."),
    ]
    for name, pts, desc in tier_info:
        is_current = tier == name
        _card(f"""
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
          <div>
            <div style="font-weight:{'700' if is_current else '500'};
                        color:{GOLD if is_current else INK};">{name}</div>
            <div style="font-size:0.75rem;color:{MUTED};margin-top:0.15rem;">{desc}</div>
          </div>
          <div style="font-size:0.75rem;font-weight:600;color:{GOLD if is_current else MUTED};
                      white-space:nowrap;margin-left:0.5rem;">{pts}</div>
        </div>
        """,
        bg=GOLD_SOFT if is_current else "#ffffff",
        border=GOLD if is_current else BORDER,
        padding="0.7rem 1rem")

    # Points history
    if gold_history:
        _section("Points History", "📋")
        reason_labels = {
            "nssf_enrolled":        "🇺🇬 Joined NSSF-registered",
            "monthly_contribution": "💰 Monthly NSSF contribution",
            "above_default_rate":   "⬆️ Above-default saving rate",
            "streak_3_months":      "🔥 3-month streak bonus",
            "streak_6_months":      "🔥🔥 6-month Patriot streak",
            "referral":             "🤝 Referral bonus",
        }
        for h in gold_history:
            _card(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <div>
                <div style="font-size:0.85rem;font-weight:500;color:{INK};">
                    {reason_labels.get(h['reason'], h['reason'])}
                </div>
                <div style="font-size:0.72rem;color:{MUTED};">{h['created_at']}</div>
              </div>
              <div style="font-weight:700;color:{GOLD};font-size:0.95rem;">+{h['points']}</div>
            </div>
            """, bg=GOLD_SOFT, border=GOLD, padding="0.65rem 1rem")


def render_profile(d):
    customer = d['customer']
    sacco    = d['sacco']

    _section("My Profile", "👤")

    # Photo
    if customer['photo']:
        st.image(customer['photo'], width=80)

    # Info cards — simple key/value pairs
    fields = [
        ("Full Name",    customer['name']),
        ("Phone",        customer['phone']),
        ("National ID",  customer['national_id'] or '—'),
        ("Gender",       customer['gender'] or '—'),
        ("Village",      customer['village'] or '—'),
        ("Parish",       customer['parish'] or '—'),
        ("Occupation",   customer['occupation'] or '—'),
        ("Member Type",  customer['member_type'] or '—'),
        ("Joined",       customer['created_at'] or '—'),
    ]
    if sacco:
        fields.append(("SACCO", sacco['sacco_name']))

    for label, value in fields:
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;
                    padding:0.6rem 0;border-bottom:1px solid {BORDER};">
          <span style="font-size:0.82rem;color:{MUTED};font-weight:500;">{label}</span>
          <span style="font-size:0.85rem;color:{INK};font-weight:600;
                       text-align:right;max-width:60%;">{value}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

    # NSSF status in profile
    if customer['nssf_registered']:
        st.success(f"🇺🇬 NSSF Registered — {customer['nssf_number'] or 'Number not captured'}")
    else:
        st.warning("⚠️ Not NSSF Registered — visit [nssfug.org](https://www.nssfug.org)")

    st.divider()

    # Change PIN
    _section("Change PIN", "🔐")
    with st.form("change_pin_form", clear_on_submit=True):
        old_pin  = st.text_input("Current PIN",  type="password", max_chars=4, placeholder="• • • •")
        new_pin1 = st.text_input("New PIN",       type="password", max_chars=4, placeholder="• • • •")
        new_pin2 = st.text_input("Confirm New PIN", type="password", max_chars=4, placeholder="• • • •")
        if st.form_submit_button("Update PIN", type="primary"):
            if not verify_pin(customer['id'], old_pin):
                st.error("Current PIN is incorrect.")
            elif not new_pin1.isdigit() or len(new_pin1) != 4:
                st.error("New PIN must be exactly 4 digits.")
            elif new_pin1 != new_pin2:
                st.error("New PINs do not match.")
            else:
                set_pin(customer['id'], new_pin1)
                st.success("✅ PIN updated successfully.")

    st.divider()
    if st.button("🚪 Log Out"):
        for key in ['member_authenticated','member_customer_id','member_phone','active_tab']:
            st.session_state[key] = None if key != 'member_authenticated' else False
        st.session_state.active_tab = None
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# BOTTOM NAVIGATION BAR
# ─────────────────────────────────────────────────────────────────────────────
def render_bottom_nav():
    nav_items = [
        ("home",   "🏠", "Home"),
        ("savings","🏦", "Savings"),
        ("loan",   "💰", "Loan"),
        ("nssf",   "🇺🇬", "NSSF"),
        ("points", "🏅", "Points"),
        ("profile","👤", "Profile"),
    ]
    active = st.session_state.get('active_tab', 'home')
    cols   = st.columns(len(nav_items))
    for col, (key, emoji, label) in zip(cols, nav_items):
        is_active = active == key
        col.markdown(f"""
        <div style="text-align:center;cursor:pointer;padding:0.3rem 0;">
          <div style="font-size:1.3rem;">{emoji}</div>
          <div style="font-size:0.62rem;font-weight:{'700' if is_active else '400'};
                      color:{GREEN if is_active else MUTED};">{label}</div>
          {'<div style="width:18px;height:3px;background:'+GREEN+';border-radius:2px;margin:2px auto 0;"></div>' if is_active else ''}
        </div>
        """, unsafe_allow_html=True)
        if col.button("", key=f"nav_{key}"):
            st.session_state.active_tab = key
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.member_authenticated:
    tab = st.session_state.get('active_tab')
    if tab == 'set_pin':
        render_set_pin()
    elif tab == 'verify_pin':
        render_verify_pin()
    else:
        render_login()
else:
    # Load all member data once per render
    d = get_member_data(st.session_state.member_customer_id)
    if d['customer'] is None:
        st.error("Member record not found. Please log in again.")
        st.session_state.member_authenticated = False
        st.rerun()

    tab = st.session_state.get('active_tab', 'home')

    if   tab == 'home':    render_home(d)
    elif tab == 'savings': render_savings(d)
    elif tab == 'loan':    render_loan(d)
    elif tab == 'nssf':    render_nssf(d)
    elif tab == 'points':  render_gold_points(d)
    elif tab == 'profile': render_profile(d)
    else:                  render_home(d)

    st.divider()
    render_bottom_nav()

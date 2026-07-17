"""
modules/reports.py

Enterprise-grade report suite for CommunityFinanceOS.
Designed for three audiences:
  1. SACCO management — operational health at a glance
  2. Government audit — PDM, Emyooga, NDP IV compliance evidence
  3. NSSF partnership — contribution data, compliance gaps, ROI proof

Sections:
  0. Executive Dashboard        — 8-metric RAG snapshot, print-ready
  1. Portfolio Analysis         — PAR30, repayment rate, gender/youth cuts
  2. Membership Demographics    — growth trend, PDM alignment, occupation
  3. Savings Performance        — monthly trend, channel split, ratios
  4. NSSF Compliance Report     — trajectory, gap analysis, Gold Points ROI
  5. NSSF Monthly Export        — clean CSV for NSSF submission
  6. NSSF Outreach Export       — unregistered members list for NSSF campaigns
  7. Cross-SACCO Aggregate      — platform-wide (super_admin only)
"""

import io
import csv
import streamlit as st
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from database import get_db_connection
from modules.loans import get_loans
from modules.collections import get_messages
from modules.theme import money_column
from auth import ROLE_SUPER_ADMIN

# ─────────────────────────────────────────────────────────────────────────────
# Colour palette — RAG + brand
# ─────────────────────────────────────────────────────────────────────────────
GREEN  = "#3F7A4D"
AMBER  = "#A4732B"
RED    = "#B0492E"
GOLD   = "#C99A3B"
BLUE   = "#2A4F82"
LIGHT  = "#F5F0E8"
BORDER = "#DDD5C4"

def _rag(value, green_threshold, amber_threshold, higher_is_better=True):
    """Return a RAG colour given thresholds."""
    if higher_is_better:
        if value >= green_threshold: return GREEN
        if value >= amber_threshold: return AMBER
        return RED
    else:
        if value <= green_threshold: return GREEN
        if value <= amber_threshold: return AMBER
        return RED

def _rag_label(value, green_threshold, amber_threshold, higher_is_better=True):
    c = _rag(value, green_threshold, amber_threshold, higher_is_better)
    if c == GREEN: return "🟢"
    if c == AMBER: return "🟡"
    return "🔴"

def _stat_card(label, value, sub=None, color=BLUE):
    return f"""
    <div style="background:{LIGHT};border:1.5px solid {BORDER};
                border-top:4px solid {color};border-radius:8px;
                padding:0.9rem 1rem;height:100%;">
      <div style="font-size:0.7rem;color:#7C8A99;text-transform:uppercase;
                  letter-spacing:0.07em;font-weight:600;">{label}</div>
      <div style="font-size:1.5rem;font-weight:700;color:#1A1A2E;
                  font-variant-numeric:tabular-nums;margin-top:0.25rem;">{value}</div>
      {'<div style="font-size:0.78rem;color:#7C8A99;margin-top:0.15rem;">'+sub+'</div>' if sub else ''}
    </div>"""

def _section_header(emoji, title, subtitle=None):
    st.markdown(f"""
    <div style="border-left:4px solid {GOLD};padding:0.4rem 0.8rem;
                margin:1.2rem 0 0.6rem 0;background:linear-gradient(90deg,#FDF6E3,transparent);">
      <div style="font-size:1.05rem;font-weight:700;color:#1A1A2E;">{emoji} {title}</div>
      {'<div style="font-size:0.78rem;color:#7C8A99;margin-top:2px;">'+subtitle+'</div>' if subtitle else ''}
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────────────────────────────────────

def _calculate_age(dob_str):
    if not dob_str:
        return None
    try:
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except ValueError:
        return None

def _last_n_months(n=6):
    """Return list of 'YYYY-MM' strings for the last n months including current."""
    months = []
    for i in range(n - 1, -1, -1):
        d = date.today().replace(day=1) - relativedelta(months=i)
        months.append(d.strftime('%Y-%m'))
    return months

def get_full_sacco_data(sacco_id):
    """Single DB round-trip pulling everything reports needs."""
    conn = get_db_connection()

    members = conn.execute(
        "SELECT * FROM customers WHERE sacco_id = ?", (sacco_id,)
    ).fetchall()

    loans = conn.execute(
        "SELECT * FROM loans WHERE sacco_id = ?", (sacco_id,)
    ).fetchall()

    schedule = conn.execute("""
        SELECT ls.*, l.sacco_id, l.customer_id FROM loan_schedule ls
        JOIN loans l ON ls.loan_id = l.id
        WHERE l.sacco_id = ?
    """, (sacco_id,)).fetchall()

    repayments = conn.execute("""
        SELECT r.* FROM repayments r
        JOIN loans l ON r.loan_id = l.id
        WHERE l.sacco_id = ?
    """, (sacco_id,)).fetchall()

    savings_accounts = conn.execute(
        "SELECT * FROM savings_accounts WHERE sacco_id = ?", (sacco_id,)
    ).fetchall()

    savings_txns = conn.execute("""
        SELECT st.*, sa.sacco_id FROM savings_transactions st
        JOIN savings_accounts sa ON st.account_id = sa.id
        WHERE sa.sacco_id = ?
    """, (sacco_id,)).fetchall()

    nssf = conn.execute(
        "SELECT * FROM nssf_contributions WHERE sacco_id = ?", (sacco_id,)
    ).fetchall()

    gold = conn.execute("""
        SELECT gp.*, c.name FROM gold_points_ledger gp
        JOIN customers c ON gp.customer_id = c.id
        WHERE gp.sacco_id = ?
    """, (sacco_id,)).fetchall()

    sacco_profile = conn.execute(
        "SELECT * FROM sacco_profile WHERE id = ?", (sacco_id,)
    ).fetchone()

    conn.close()
    return dict(
        members=members, loans=loans, schedule=schedule,
        repayments=repayments, savings_accounts=savings_accounts,
        savings_txns=savings_txns, nssf=nssf, gold=gold,
        sacco_profile=sacco_profile
    )

def get_all_sacco_aggregate():
    """Platform-wide data for super_admin cross-SACCO view."""
    conn = get_db_connection()
    saccos      = conn.execute("SELECT id, sacco_name FROM sacco_profile").fetchall()
    total_mem   = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    total_nssf  = conn.execute("SELECT COUNT(*) FROM customers WHERE nssf_registered=1").fetchone()[0]
    total_loans = conn.execute("SELECT COUNT(*) FROM loans").fetchone()[0]
    total_savings = conn.execute("SELECT COALESCE(SUM(balance),0) FROM savings_accounts").fetchone()[0]
    total_contrib = conn.execute("SELECT COALESCE(SUM(nssf_amount),0) FROM nssf_contributions").fetchone()[0]
    unremitted    = conn.execute("SELECT COALESCE(SUM(nssf_amount),0) FROM nssf_contributions WHERE remitted=0").fetchone()[0]

    per_sacco = conn.execute("""
        SELECT s.id, s.sacco_name,
               COUNT(DISTINCT c.id) AS members,
               COUNT(DISTINCT CASE WHEN c.nssf_registered=1 THEN c.id END) AS nssf_reg,
               COALESCE(SUM(sa.balance),0) AS total_savings,
               COALESCE((SELECT SUM(nc.nssf_amount) FROM nssf_contributions nc WHERE nc.sacco_id=s.id),0) AS nssf_contrib
        FROM sacco_profile s
        LEFT JOIN customers c ON c.sacco_id = s.id
        LEFT JOIN savings_accounts sa ON sa.sacco_id = s.id
        GROUP BY s.id
        ORDER BY nssf_contrib DESC
    """).fetchall()

    conn.close()
    return dict(
        saccos=saccos, total_mem=total_mem, total_nssf=total_nssf,
        total_loans=total_loans, total_savings=total_savings,
        total_contrib=total_contrib, unremitted=unremitted,
        per_sacco=per_sacco
    )

def _make_nssf_csv(sacco_name, period, rows):
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["NSSF CONTRIBUTION SUBMISSION"])
    w.writerow(["SACCO Name",        sacco_name])
    w.writerow(["Period",            period])
    w.writerow(["Generated By",      "CommunityFinanceOS — SaccoOS Platform"])
    w.writerow(["Generated On",      datetime.now().strftime("%Y-%m-%d %H:%M")])
    w.writerow(["Total Members",     len(rows)])
    w.writerow(["Total Amount (UGX)",f"{sum(r['nssf_amount'] for r in rows):,.2f}"])
    w.writerow([])
    w.writerow(["Full Name","National ID","NSSF Number","Phone",
                "Contribution (UGX)","Period","Transaction Date","Status"])
    for r in rows:
        conn2 = get_db_connection()
        c = conn2.execute("SELECT name,national_id,nssf_number,phone FROM customers WHERE id=?",
                          (r['customer_id'],)).fetchone()
        conn2.close()
        w.writerow([
            c['name'], c['national_id'] or "", c['nssf_number'] or "PENDING",
            c['phone'], f"{r['nssf_amount']:,.2f}",
            r['period'], r['created_at'],
            "Remitted" if r['remitted'] else "Pending"
        ])
    return output.getvalue().encode('utf-8')

def _make_outreach_csv(sacco_name, rows):
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["NSSF REGISTRATION OUTREACH LIST"])
    w.writerow(["SACCO Name",    sacco_name])
    w.writerow(["Generated By",  "CommunityFinanceOS — SaccoOS Platform"])
    w.writerow(["Generated On",  datetime.now().strftime("%Y-%m-%d %H:%M")])
    w.writerow(["Purpose",       "Members not yet registered with NSSF — for direct outreach"])
    w.writerow(["Total Records", len(rows)])
    w.writerow([])
    w.writerow(["Full Name","National ID","Phone","Gender","Village","Parish","Enrolled Date"])
    for r in rows:
        w.writerow([
            r['name'], r['national_id'] or "", r['phone'],
            r['gender'] or "", r['village'] or "", r['parish'] or "",
            r['created_at']
        ])
    return output.getvalue().encode('utf-8')


# ─────────────────────────────────────────────────────────────────────────────
# Section renderers
# ─────────────────────────────────────────────────────────────────────────────

def _render_executive_dashboard(d, sacco_name):
    _section_header("📋", "Executive Dashboard",
                    f"{sacco_name} — {date.today().strftime('%B %Y')}")

    members      = d['members']
    loans        = d['loans']
    schedule     = d['schedule']
    savings_accs = d['savings_accounts']
    nssf         = d['nssf']
    gold         = d['gold']

    total_mem    = len(members)
    active_loans = [l for l in loans if l['status'] == 'Active']
    outstanding  = sum(l['balance'] for l in active_loans)
    total_savings= sum(a['balance'] for a in savings_accs)
    nssf_reg     = sum(1 for m in members if m['nssf_registered'])
    compliance   = (nssf_reg / total_mem * 100) if total_mem else 0
    total_contrib= sum(r['nssf_amount'] for r in nssf)
    unremitted   = sum(r['nssf_amount'] for r in nssf if not r['remitted'])

    # PAR calculation
    today_str = date.today().strftime('%Y-%m-%d')
    overdue_loan_ids = {r['loan_id'] for r in schedule
                        if r['status'] != 'Paid' and r['due_date'] < today_str}
    par_amount = sum(l['balance'] for l in active_loans if l['id'] in overdue_loan_ids)
    par_rate   = (par_amount / outstanding * 100) if outstanding > 0 else 0

    # Repayment rate
    due_total  = sum(r['due_amount'] for r in schedule)
    paid_total = sum(r['paid_amount'] for r in schedule)
    repay_rate = (paid_total / due_total * 100) if due_total > 0 else 100

    # Gold points members
    gold_earners = len(set(r['customer_id'] for r in gold))
    gold_pct     = (gold_earners / total_mem * 100) if total_mem else 0

    # RAG indicators
    compliance_rag  = _rag_label(compliance,  80, 50)
    par_rag         = _rag_label(par_rate,     5,  15, higher_is_better=False)
    repay_rag       = _rag_label(repay_rate,   85, 70)
    gold_rag        = _rag_label(gold_pct,     60, 30)

    # Render cards
    cols = st.columns(4)
    cards = [
        ("Total Members",         f"{total_mem:,}",                    "enrolled in SACCO",        BLUE),
        ("NSSF Compliance",       f"{compliance:.1f}% {compliance_rag}",f"{nssf_reg} registered",  GREEN if compliance>=80 else AMBER if compliance>=50 else RED),
        ("Net Savings Held",      f"UGX {total_savings:,.0f}",         "current balance",          GOLD),
        ("Active Loan Portfolio", f"UGX {outstanding:,.0f}",           f"{len(active_loans)} loans",BLUE),
    ]
    for col, (label, value, sub, color) in zip(cols, cards):
        col.markdown(_stat_card(label, value, sub, color), unsafe_allow_html=True)

    st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)
    cols2 = st.columns(4)
    cards2 = [
        ("Portfolio at Risk",     f"{par_rate:.1f}% {par_rag}",        f"UGX {par_amount:,.0f}",   RED if par_rate>15 else AMBER if par_rate>5 else GREEN),
        ("Repayment Rate",        f"{repay_rate:.1f}% {repay_rag}",    "of scheduled installments",GREEN if repay_rate>=85 else AMBER if repay_rate>=70 else RED),
        ("NSSF Contributions",    f"UGX {total_contrib:,.0f}",         f"UGX {unremitted:,.0f} pending",GOLD),
        ("Gold Points Members",   f"{gold_pct:.0f}% {gold_rag}",       f"{gold_earners} active earners",GOLD),
    ]
    for col, (label, value, sub, color) in zip(cols2, cards2):
        col.markdown(_stat_card(label, value, sub, color), unsafe_allow_html=True)

    # Health summary bar
    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    health_items = [
        (f"NSSF Compliance: {compliance:.1f}%", GREEN if compliance>=80 else AMBER if compliance>=50 else RED),
        (f"PAR: {par_rate:.1f}%",               GREEN if par_rate<=5 else AMBER if par_rate<=15 else RED),
        (f"Repayment: {repay_rate:.1f}%",        GREEN if repay_rate>=85 else AMBER if repay_rate>=70 else RED),
        (f"Gold Earners: {gold_pct:.0f}%",       GREEN if gold_pct>=60 else AMBER if gold_pct>=30 else RED),
    ]
    badges = " &nbsp;&nbsp; ".join(
        f'<span style="background:{c};color:#fff;padding:3px 10px;border-radius:12px;font-size:0.78rem;font-weight:600;">{t}</span>'
        for t, c in health_items
    )
    st.markdown(f'<div style="margin-top:0.3rem;">{badges}</div>', unsafe_allow_html=True)


def _render_portfolio(d):
    _section_header("💰", "Portfolio Analysis",
                    "Loan book health with PAR30, repayment rates, and demographic cuts")

    loans    = d['loans']
    schedule = d['schedule']
    members  = d['members']

    member_map = {m['id']: m for m in members}
    active     = [l for l in loans if l['status'] == 'Active']
    closed     = [l for l in loans if l['status'] == 'Closed']
    outstanding= sum(l['balance'] for l in active)
    today_str  = date.today().strftime('%Y-%m-%d')
    today_dt   = date.today()

    # PAR buckets
    loan_max_overdue = defaultdict(int)  # loan_id → max days overdue
    for r in schedule:
        if r['status'] != 'Paid' and r['due_date']:
            try:
                due_dt = datetime.strptime(r['due_date'], '%Y-%m-%d').date()
                days_overdue = (today_dt - due_dt).days
                if days_overdue > 0:
                    loan_max_overdue[r['loan_id']] = max(loan_max_overdue[r['loan_id']], days_overdue)
            except ValueError:
                pass

    par1_ids  = {lid for lid, d in loan_max_overdue.items() if d >= 1}
    par30_ids = {lid for lid, d in loan_max_overdue.items() if d >= 30}
    par60_ids = {lid for lid, d in loan_max_overdue.items() if d >= 60}
    par90_ids = {lid for lid, d in loan_max_overdue.items() if d >= 90}

    par1_amt  = sum(l['balance'] for l in active if l['id'] in par1_ids)
    par30_amt = sum(l['balance'] for l in active if l['id'] in par30_ids)
    par90_amt = sum(l['balance'] for l in active if l['id'] in par90_ids)
    par30_rate= (par30_amt / outstanding * 100) if outstanding > 0 else 0

    # Repayment rate
    due_total  = sum(r['due_amount'] or 0 for r in schedule)
    paid_total = sum(r['paid_amount'] or 0 for r in schedule)
    repay_rate = (paid_total / due_total * 100) if due_total > 0 else 100

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Loans", len(loans))
    c2.metric("Active", len(active))
    c3.metric("Closed / Repaid", len(closed))
    c4.metric("PAR30 Rate", f"{par30_rate:.1f}%",
              delta=f"UGX {par30_amt:,.0f}", delta_color="inverse")
    c5.metric("Repayment Rate", f"{repay_rate:.1f}%",
              delta_color="normal")

    # PAR breakdown table
    if outstanding > 0:
        st.write("**Portfolio at Risk — Ageing Buckets:**")
        par_table = [
            {"Bucket":    "PAR1  (1+ days overdue)",
             "Loans":     len([l for l in active if l['id'] in par1_ids]),
             "Amount":    sum(l['balance'] for l in active if l['id'] in par1_ids),
             "% of Port.":f"{sum(l['balance'] for l in active if l['id'] in par1_ids)/outstanding*100:.1f}%"},
            {"Bucket":    "PAR30 (30+ days overdue)",
             "Loans":     len([l for l in active if l['id'] in par30_ids]),
             "Amount":    par30_amt,
             "% of Port.":f"{par30_rate:.1f}%"},
            {"Bucket":    "PAR60 (60+ days overdue)",
             "Loans":     len([l for l in active if l['id'] in par60_ids]),
             "Amount":    sum(l['balance'] for l in active if l['id'] in par60_ids),
             "% of Port.":f"{sum(l['balance'] for l in active if l['id'] in par60_ids)/outstanding*100:.1f}%"},
            {"Bucket":    "PAR90 (90+ days — write-off risk)",
             "Loans":     len([l for l in active if l['id'] in par90_ids]),
             "Amount":    par90_amt,
             "% of Port.":f"{par90_amt/outstanding*100:.1f}%"},
        ]
        st.dataframe(par_table,
                     column_config={"Amount": money_column()},
                     use_container_width=True, hide_index=True)

    # Gender and youth loan cuts
    st.write("**Loan Portfolio — Gender & Youth Breakdown:**")

    def loan_cuts(loan_list):
        female_loans, youth_loans, female_amt, youth_amt = 0, 0, 0.0, 0.0
        for l in loan_list:
            m = member_map.get(l['customer_id'])
            if not m:
                continue
            if (m['gender'] or '').lower() == 'female':
                female_loans += 1
                female_amt   += l['principal']
            age = _calculate_age(m['date_of_birth'])
            if age and 18 <= age <= 35:
                youth_loans += 1
                youth_amt   += l['principal']
        return female_loans, female_amt, youth_loans, youth_amt

    fl, fa, yl, ya = loan_cuts(loans)
    total_principal = sum(l['principal'] for l in loans) or 1

    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Female Borrowers",     fl,
              f"{fl/len(loans)*100:.0f}% of loans" if loans else "0%")
    g2.metric("Female Loan Volume",   f"UGX {fa:,.0f}",
              f"{fa/total_principal*100:.0f}% of principal" if total_principal else "")
    g3.metric("Youth Borrowers (18–35)", yl,
              f"{yl/len(loans)*100:.0f}% of loans" if loans else "0%")
    g4.metric("Youth Loan Volume",    f"UGX {ya:,.0f}",
              f"{ya/total_principal*100:.0f}% of principal" if total_principal else "")


def _render_demographics(d):
    _section_header("👥", "Membership Demographics",
                    "Required for PDM, Emyooga, and NDP IV government programme reporting")

    members = d['members']
    total   = len(members)
    if not total:
        st.info("No members enrolled yet.")
        return

    female      = sum(1 for m in members if (m['gender'] or '').lower() == 'female')
    male        = total - female
    ages        = [_calculate_age(m['date_of_birth']) for m in members]
    youth       = sum(1 for a in ages if a and 18 <= a <= 35)
    pwd         = sum(1 for m in members if (m['pwd_status'] or '').lower() == 'yes')
    subsistence = sum(1 for m in members if (m['subsistence_status'] or '').lower() == 'yes')
    nssf_reg    = sum(1 for m in members if m['nssf_registered'])

    # PDM alignment score — members who are subsistence + female OR youth = core PDM targets
    pdm_core = sum(1 for m in members
                   if (m['subsistence_status'] or '').lower() == 'yes'
                   and ((m['gender'] or '').lower() == 'female'
                        or (_calculate_age(m['date_of_birth']) or 0) <= 35))
    pdm_score = (pdm_core / total * 100) if total else 0

    d1, d2, d3, d4, d5, d6, d7 = st.columns(7)
    d1.metric("Total Members",        total)
    d2.metric("Female",               f"{female}",  f"{female/total*100:.0f}%")
    d3.metric("Male",                 f"{male}",    f"{male/total*100:.0f}%")
    d4.metric("Youth (18–35)",        f"{youth}",   f"{youth/total*100:.0f}%")
    d5.metric("PWD",                  f"{pwd}",     f"{pwd/total*100:.0f}%")
    d6.metric("Subsistence Economy",  f"{subsistence}", f"{subsistence/total*100:.0f}%")
    d7.metric("PDM Core Target",      f"{pdm_core}",f"{pdm_score:.0f}% alignment")

    # Female savings breakdown
    conn = get_db_connection()
    sacco_id = st.session_state.get('current_sacco_id')
    female_ids = [m['id'] for m in members if (m['gender'] or '').lower() == 'female']
    female_savings = 0.0
    if female_ids:
        placeholders = ','.join('?' * len(female_ids))
        row = conn.execute(
            f"SELECT COALESCE(SUM(balance),0) FROM savings_accounts WHERE customer_id IN ({placeholders}) AND sacco_id=?",
            (*female_ids, sacco_id)
        ).fetchone()
        female_savings = row[0] if row else 0.0
    total_savings_bal = sum(a['balance'] for a in d['savings_accounts'])
    conn.close()

    fs1, fs2 = st.columns(2)
    fs1.metric("Female Savings Mobilised",
               f"UGX {female_savings:,.0f}",
               f"{female_savings/total_savings_bal*100:.0f}% of total savings" if total_savings_bal else "")
    fs2.metric("NSSF Registration Rate",
               f"{nssf_reg/total*100:.1f}%",
               f"{nssf_reg} of {total} members")

    # Occupation breakdown
    st.write("**Occupation Breakdown:**")
    occ_counts = Counter(m['occupation'] or 'Not specified' for m in members)
    occ_sorted = sorted(occ_counts.items(), key=lambda x: x[1], reverse=True)
    st.dataframe(
        [{"Occupation": k, "Members": v, "Share": f"{v/total*100:.1f}%"}
         for k, v in occ_sorted],
        use_container_width=True, hide_index=True
    )

    # Monthly membership growth (last 6 months)
    st.write("**Membership Growth — Last 6 Months:**")
    months = _last_n_months(6)
    growth = []
    for mo in months:
        count = sum(1 for m in members
                    if m['created_at'] and m['created_at'][:7] <= mo)
        growth.append({"Month": mo, "Cumulative Members": count})
    st.dataframe(growth, use_container_width=True, hide_index=True)


def _render_savings(d):
    _section_header("🏦", "Savings Performance",
                    "Mobilisation totals, monthly trend, channel split, and member averages")

    accounts = d['savings_accounts']
    txns     = d['savings_txns']
    members  = d['members']

    if not accounts:
        st.info("No savings accounts opened yet.")
        return

    deposits    = [t for t in txns if t['type'] == 'Deposit']
    withdrawals = [t for t in txns if t['type'] == 'Withdrawal']
    total_dep   = sum(t['amount'] for t in deposits)
    total_wdl   = sum(t['amount'] for t in withdrawals)
    net_savings = total_dep - total_wdl
    avg_balance = sum(a['balance'] for a in accounts) / len(accounts)
    total_members = len(members) or 1
    savings_penetration = len(accounts) / total_members * 100

    # Savings-to-loan ratio
    active_loan_bal = sum(l['balance'] for l in d['loans'] if l['status'] == 'Active')
    stl_ratio = (net_savings / active_loan_bal) if active_loan_bal > 0 else None

    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Savings Accounts",      len(accounts))
    s2.metric("Total Mobilised",       f"UGX {total_dep:,.0f}")
    s3.metric("Net Savings Held",      f"UGX {net_savings:,.0f}")
    s4.metric("Avg Balance / Member",  f"UGX {avg_balance:,.0f}")
    s5.metric("Savings Penetration",   f"{savings_penetration:.0f}%",
              "of enrolled members have accounts")

    if stl_ratio is not None:
        st.metric(
            "Savings-to-Loan Ratio",
            f"{stl_ratio:.2f}x",
            help="Ratio of net savings to active loan portfolio. >1.0 = savings-funded lending (ideal)."
        )

    # Monthly savings trend
    st.write("**Monthly Deposit Trend — Last 6 Months:**")
    months = _last_n_months(6)
    trend = []
    for mo in months:
        mo_deposits = sum(t['amount'] for t in deposits
                          if t['date'] and t['date'][:7] == mo)
        mo_wdl      = sum(t['amount'] for t in withdrawals
                          if t['date'] and t['date'][:7] == mo)
        trend.append({
            "Month":       mo,
            "Deposits":    mo_deposits,
            "Withdrawals": mo_wdl,
            "Net":         mo_deposits - mo_wdl
        })
    st.dataframe(
        trend,
        column_config={
            "Deposits":    money_column(),
            "Withdrawals": money_column(),
            "Net":         money_column(),
        },
        use_container_width=True, hide_index=True
    )

    # Channel breakdown
    st.write("**Payment Channel Breakdown:**")
    channels = Counter(t['channel'] or 'Not recorded' for t in deposits)
    ch_total = sum(channels.values()) or 1
    st.dataframe(
        [{"Channel": k, "Transactions": v, "Share": f"{v/ch_total*100:.1f}%"}
         for k, v in sorted(channels.items(), key=lambda x: x[1], reverse=True)],
        use_container_width=True, hide_index=True
    )

    # Top savers
    with st.expander("Top 10 Savers"):
        top = sorted(accounts, key=lambda a: a['balance'], reverse=True)[:10]
        conn = get_db_connection()
        top_data = []
        for a in top:
            c = conn.execute("SELECT name FROM customers WHERE id=?", (a['customer_id'],)).fetchone()
            top_data.append({"Member": c['name'] if c else "—", "Balance": a['balance']})
        conn.close()
        st.dataframe(top_data,
                     column_config={"Balance": money_column()},
                     use_container_width=True, hide_index=True)


def _render_nssf_compliance(d, sacco_name):
    _section_header("🇺🇬", "NSSF Compliance Report",
                    "Contribution trajectory, compliance gap analysis, and Gold Points ROI — for NSSF partnership review")

    members  = d['members']
    nssf     = d['nssf']
    gold     = d['gold']
    total    = len(members)
    reg      = sum(1 for m in members if m['nssf_registered'])
    unreg    = total - reg
    comp_pct = (reg / total * 100) if total else 0

    total_contrib = sum(r['nssf_amount'] for r in nssf)
    unremitted    = sum(r['nssf_amount'] for r in nssf if not r['remitted'])
    avg_contrib   = (total_contrib / reg) if reg else 0

    # Projected annual (based on last 3 months average)
    months         = _last_n_months(3)
    recent_contrib = sum(r['nssf_amount'] for r in nssf if r['period'] in months)
    monthly_avg    = recent_contrib / 3 if recent_contrib else 0
    projected_annual = monthly_avg * 12

    n1, n2, n3, n4, n5 = st.columns(5)
    n1.metric("Compliance Rate",      f"{comp_pct:.1f}%",   f"{reg} of {total} registered")
    n2.metric("Total Contributed",    f"UGX {total_contrib:,.0f}", "all time")
    n3.metric("Avg / Registered Member", f"UGX {avg_contrib:,.0f}", "lifetime average")
    n4.metric("Unremitted",           f"UGX {unremitted:,.0f}", "pending submission to NSSF")
    n5.metric("Projected Annual",     f"UGX {projected_annual:,.0f}", "based on last 3 months")

    # Contribution trajectory — last 12 months
    st.write("**Contribution Trajectory — Last 12 Months:**")
    months12 = _last_n_months(12)
    trajectory = []
    cumulative = 0
    for mo in months12:
        mo_amount  = sum(r['nssf_amount'] for r in nssf if r['period'] == mo)
        mo_members = len(set(r['customer_id'] for r in nssf if r['period'] == mo))
        cumulative += mo_amount
        trajectory.append({
            "Period":              mo,
            "Contributing Members":mo_members,
            "Amount (UGX)":        mo_amount,
            "Cumulative (UGX)":    cumulative,
        })
    st.dataframe(
        trajectory,
        column_config={
            "Amount (UGX)":     money_column(),
            "Cumulative (UGX)": money_column(),
        },
        use_container_width=True, hide_index=True
    )

    # Gold Points ROI — impact on registration behaviour
    st.write("**Gold Points Impact on NSSF Registration:**")
    st.caption(
        "Evidence that the Gold Points incentive programme is driving NSSF uptake — "
        "key ROI metric for NSSF's sponsorship of this platform."
    )

    gold_earner_ids = set(r['customer_id'] for r in gold)
    gold_and_nssf   = sum(1 for m in members
                          if m['nssf_registered'] and m['id'] in gold_earner_ids)
    gold_not_nssf   = len(gold_earner_ids) - gold_and_nssf
    no_gold_nssf    = sum(1 for m in members
                          if m['nssf_registered'] and m['id'] not in gold_earner_ids)

    streak_3  = sum(1 for r in gold if r['reason'] == 'streak_3_months')
    streak_6  = sum(1 for r in gold if r['reason'] == 'streak_6_months')
    total_pts = sum(r['points'] for r in gold)

    gi1, gi2, gi3, gi4 = st.columns(4)
    gi1.metric("Gold Points Members w/ NSSF", gold_and_nssf,
               "registered and earning points")
    gi2.metric("3-Month Streak Badges",        streak_3,
               "consistent contributors")
    gi3.metric("6-Month Patriot Badges",        streak_6,
               "long-term committed savers")
    gi4.metric("Total Gold Points Awarded",     f"{total_pts:,}",
               "across all members")

    # Contribution rate distribution
    st.write("**Contribution Rate Distribution:**")
    rate_buckets = Counter()
    for m in members:
        if m['nssf_registered']:
            rate = m['nssf_contribution_rate'] or 5.0
            if rate <= 5:    rate_buckets['5% (standard)']    += 1
            elif rate <= 10: rate_buckets['6–10% (above avg)'] += 1
            else:            rate_buckets['11–20% (high saver)'] += 1
    if rate_buckets:
        st.dataframe(
            [{"Rate Band": k, "Members": v} for k, v in rate_buckets.items()],
            use_container_width=True, hide_index=True
        )

    # Compliance gap — unregistered members
    if unreg > 0:
        st.warning(f"⚠️ **{unreg} members not yet NSSF registered** — see Section 6 for the outreach export.")
    else:
        st.success("✅ Full NSSF compliance achieved — all members registered.")


def _render_nssf_export(d, sacco_name, sacco_id):
    _section_header("📥", "NSSF Monthly Submission Export",
                    "Clean CSV file formatted for direct submission to NSSF — one file per period")

    nssf = d['nssf']
    if not nssf:
        st.info("No NSSF contributions recorded yet. They appear here automatically once registered members make deposits.")
        return

    periods     = sorted(set(r['period'] for r in nssf), reverse=True)
    sel_period  = st.selectbox("Select period", periods,
                               help="Format: YYYY-MM — e.g. 2026-07")
    period_rows = [r for r in nssf if r['period'] == sel_period]
    total_amt   = sum(r['nssf_amount'] for r in period_rows)
    remitted    = sum(1 for r in period_rows if r['remitted'])

    st.info(
        f"**{len(period_rows)} contributions** | "
        f"**UGX {total_amt:,.0f} total** | "
        f"**{remitted} remitted, {len(period_rows)-remitted} pending**"
    )

    # Preview
    conn = get_db_connection()
    preview = []
    for r in period_rows:
        c = conn.execute(
            "SELECT name, national_id, nssf_number, phone FROM customers WHERE id=?",
            (r['customer_id'],)
        ).fetchone()
        if c:
            preview.append({
                "Name":        c['name'],
                "National ID": c['national_id'] or "—",
                "NSSF No.":   c['nssf_number'] or "PENDING",
                "Phone":       c['phone'],
                "Amount (UGX)":r['nssf_amount'],
                "Status":      "✅ Remitted" if r['remitted'] else "⏳ Pending",
            })
    conn.close()

    st.dataframe(preview,
                 column_config={"Amount (UGX)": money_column()},
                 use_container_width=True, hide_index=True)

    csv_bytes = _make_nssf_csv(sacco_name, sel_period, period_rows)
    st.download_button(
        label=f"⬇️ Download NSSF Submission — {sel_period}",
        data=csv_bytes,
        file_name=f"nssf_submission_{sacco_name.replace(' ','_')}_{sel_period}.csv",
        mime="text/csv",
        type="primary"
    )
    st.caption("After submitting, mark this period as remitted in **🇺🇬 NSSF Compliance** to keep records clean.")


def _render_outreach_export(d, sacco_name, sacco_id):
    _section_header("📋", "NSSF Outreach Export",
                    "Ready-made contact list of unregistered members — give this to NSSF to run registration campaigns directly")

    members = d['members']
    unreg   = [m for m in members if not m['nssf_registered']]

    if not unreg:
        st.success("✅ No unregistered members — nothing to export.")
        return

    st.warning(
        f"**{len(unreg)} members** not yet registered with NSSF. "
        "This export gives NSSF everything they need to contact and register them directly."
    )

    # Preview table
    st.dataframe(
        [{
            "Name":       m['name'],
            "Phone":      m['phone'],
            "National ID":m['national_id'] or "—",
            "Gender":     m['gender'] or "—",
            "Village":    m['village'] or "—",
            "Parish":     m['parish'] or "—",
            "Enrolled":   m['created_at'],
        } for m in unreg],
        use_container_width=True, hide_index=True
    )

    csv_bytes = _make_outreach_csv(sacco_name, unreg)
    st.download_button(
        label=f"⬇️ Download Outreach List ({len(unreg)} members)",
        data=csv_bytes,
        file_name=f"nssf_outreach_{sacco_name.replace(' ','_')}_{date.today()}.csv",
        mime="text/csv",
        type="primary"
    )
    st.caption(
        "💡 Share this file with your NSSF contact. "
        "It contains names, NINs, phone numbers, and locations — "
        "everything needed for a direct registration drive."
    )


def _render_cross_sacco():
    _section_header("🌍", "Cross-SACCO Platform Aggregate",
                    "Platform-wide view — super admin only. Shows total impact across all SACCOs.")

    agg = get_all_sacco_aggregate()
    comp_rate = (agg['total_nssf'] / agg['total_mem'] * 100) if agg['total_mem'] else 0

    a1, a2, a3, a4, a5 = st.columns(5)
    a1.metric("Total Members (Platform)",    f"{agg['total_mem']:,}")
    a2.metric("NSSF Registered (Platform)",  f"{agg['total_nssf']:,}",
              f"{comp_rate:.1f}% compliance")
    a3.metric("Total Loans (Platform)",      f"{agg['total_loans']:,}")
    a4.metric("Total Savings (Platform)",    f"UGX {agg['total_savings']:,.0f}")
    a5.metric("Total NSSF Contributions",    f"UGX {agg['total_contrib']:,.0f}",
              f"UGX {agg['unremitted']:,.0f} unremitted")

    st.write("**Per-SACCO Breakdown:**")
    per_sacco_data = []
    for s in agg['per_sacco']:
        s_comp = (s['nssf_reg'] / s['members'] * 100) if s['members'] else 0
        per_sacco_data.append({
            "SACCO":             s['sacco_name'] or f"SACCO #{s['id']}",
            "Members":           s['members'],
            "NSSF Registered":   s['nssf_reg'],
            "Compliance %":      f"{s_comp:.1f}%",
            "Savings (UGX)":     s['total_savings'],
            "NSSF Contrib (UGX)":s['nssf_contrib'],
        })
    st.dataframe(
        per_sacco_data,
        column_config={
            "Savings (UGX)":      money_column(),
            "NSSF Contrib (UGX)": money_column(),
        },
        use_container_width=True, hide_index=True
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main render
# ─────────────────────────────────────────────────────────────────────────────

def render():
    sacco_id   = st.session_state.get('current_sacco_id')
    user_role  = st.session_state.get('user_role')

    if sacco_id is None:
        st.warning("No SACCO selected. Set up a SACCO Profile first.")
        return

    d = get_full_sacco_data(sacco_id)
    sacco_name = (d['sacco_profile']['sacco_name']
                  if d['sacco_profile'] else f"SACCO #{sacco_id}")

    # Install dateutil quietly if missing
    try:
        from dateutil.relativedelta import relativedelta
    except ImportError:
        st.error("Missing dependency: run `pip install python-dateutil` and redeploy.")
        return

    sections = [
        "📋 Executive Dashboard",
        "💰 Portfolio Analysis",
        "👥 Membership Demographics",
        "🏦 Savings Performance",
        "🇺🇬 NSSF Compliance Report",
        "📥 NSSF Monthly Export",
        "📋 NSSF Outreach Export",
    ]
    if user_role == ROLE_SUPER_ADMIN:
        sections.append("🌍 Cross-SACCO Aggregate")

    section = st.radio("Jump to section", sections, horizontal=True)
    st.divider()

    if section == "📋 Executive Dashboard":
        _render_executive_dashboard(d, sacco_name)
    elif section == "💰 Portfolio Analysis":
        _render_portfolio(d)
    elif section == "👥 Membership Demographics":
        _render_demographics(d)
    elif section == "🏦 Savings Performance":
        _render_savings(d)
    elif section == "🇺🇬 NSSF Compliance Report":
        _render_nssf_compliance(d, sacco_name)
    elif section == "📥 NSSF Monthly Export":
        _render_nssf_export(d, sacco_name, sacco_id)
    elif section == "📋 NSSF Outreach Export":
        _render_outreach_export(d, sacco_name, sacco_id)
    elif section == "🌍 Cross-SACCO Aggregate" and user_role == ROLE_SUPER_ADMIN:
        _render_cross_sacco()

    # Messages log always at the bottom
    st.divider()
    st.write("#### 📨 Client Messages Log")
    messages = get_messages(sacco_id, limit=50)
    if messages:
        st.dataframe(
            [{"Date": m['sent_at'], "Customer": m['customer_name'],
              "Message": m['message']} for m in messages],
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No messages sent yet.")

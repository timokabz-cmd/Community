"""
modules/reports.py — PostgreSQL version
All ? placeholders replaced with %s.
All conn.execute() replaced with cur = conn.cursor(); cur.execute() pattern.
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

GREEN="#3F7A4D"; AMBER="#A4732B"; RED="#B0492E"; GOLD="#C99A3B"; BLUE="#2A4F82"
LIGHT="#F5F0E8"; BORDER="#DDD5C4"

def _rag(v,g,a,h=True):
    if h: return GREEN if v>=g else AMBER if v>=a else RED
    return GREEN if v<=g else AMBER if v<=a else RED

def _rag_label(v,g,a,h=True):
    c=_rag(v,g,a,h)
    return "🟢" if c==GREEN else "🟡" if c==AMBER else "🔴"

def _stat_card(label,value,sub=None,color=BLUE):
    return f"""<div style="background:{LIGHT};border:1.5px solid {BORDER};border-top:4px solid {color};
    border-radius:8px;padding:0.9rem 1rem;height:100%;">
    <div style="font-size:0.7rem;color:#7C8A99;text-transform:uppercase;letter-spacing:0.07em;font-weight:600;">{label}</div>
    <div style="font-size:1.5rem;font-weight:700;color:#1A1A2E;font-variant-numeric:tabular-nums;margin-top:0.25rem;">{value}</div>
    {'<div style="font-size:0.78rem;color:#7C8A99;margin-top:0.15rem;">'+sub+'</div>' if sub else ''}
    </div>"""

def _section_header(emoji,title,subtitle=None):
    st.markdown(f"""<div style="border-left:4px solid {GOLD};padding:0.4rem 0.8rem;
    margin:1.2rem 0 0.6rem 0;background:linear-gradient(90deg,#FDF6E3,transparent);">
    <div style="font-size:1.05rem;font-weight:700;color:#1A1A2E;">{emoji} {title}</div>
    {'<div style="font-size:0.78rem;color:#7C8A99;margin-top:2px;">'+subtitle+'</div>' if subtitle else ''}
    </div>""", unsafe_allow_html=True)

def _calculate_age(dob_str):
    if not dob_str: return None
    try:
        dob=datetime.strptime(dob_str,'%Y-%m-%d').date(); today=date.today()
        return today.year-dob.year-((today.month,today.day)<(dob.month,dob.day))
    except: return None

def _last_n_months(n=6):
    months=[]
    for i in range(n-1,-1,-1):
        d=date.today().replace(day=1)-relativedelta(months=i)
        months.append(d.strftime('%Y-%m'))
    return months

def get_full_sacco_data(sacco_id):
    conn=get_db_connection(); cur=conn.cursor()
    cur.execute("SELECT * FROM customers WHERE sacco_id=%s",(sacco_id,)); members=cur.fetchall()
    cur.execute("SELECT * FROM loans WHERE sacco_id=%s",(sacco_id,)); loans=cur.fetchall()
    cur.execute("""SELECT ls.*,l.sacco_id,l.customer_id FROM loan_schedule ls
        JOIN loans l ON ls.loan_id=l.id WHERE l.sacco_id=%s""",(sacco_id,)); schedule=cur.fetchall()
    cur.execute("""SELECT r.* FROM repayments r JOIN loans l ON r.loan_id=l.id
        WHERE l.sacco_id=%s""",(sacco_id,)); repayments=cur.fetchall()
    cur.execute("SELECT * FROM savings_accounts WHERE sacco_id=%s",(sacco_id,)); savings_accounts=cur.fetchall()
    cur.execute("""SELECT st.*,sa.sacco_id FROM savings_transactions st
        JOIN savings_accounts sa ON st.account_id=sa.id WHERE sa.sacco_id=%s""",(sacco_id,)); savings_txns=cur.fetchall()
    cur.execute("SELECT * FROM nssf_contributions WHERE sacco_id=%s",(sacco_id,)); nssf=cur.fetchall()
    cur.execute("""SELECT gp.*,c.name FROM gold_points_ledger gp
        JOIN customers c ON gp.customer_id=c.id WHERE gp.sacco_id=%s""",(sacco_id,)); gold=cur.fetchall()
    cur.execute("SELECT * FROM sacco_profile WHERE id=%s",(sacco_id,)); sacco_profile=cur.fetchone()
    cur.close(); conn.close()
    return dict(members=members,loans=loans,schedule=schedule,repayments=repayments,
                savings_accounts=savings_accounts,savings_txns=savings_txns,
                nssf=nssf,gold=gold,sacco_profile=sacco_profile)

def get_all_sacco_aggregate():
    conn=get_db_connection(); cur=conn.cursor()
    cur.execute("SELECT id,sacco_name FROM sacco_profile"); saccos=cur.fetchall()
    cur.execute("SELECT COUNT(*) AS c FROM customers"); total_mem=list(cur.fetchone().values())[0]
    cur.execute("SELECT COUNT(*) AS c FROM customers WHERE nssf_registered=1"); total_nssf=list(cur.fetchone().values())[0]
    cur.execute("SELECT COUNT(*) AS c FROM loans"); total_loans=list(cur.fetchone().values())[0]
    cur.execute("SELECT COALESCE(SUM(balance),0) AS s FROM savings_accounts"); total_savings=list(cur.fetchone().values())[0]
    cur.execute("SELECT COALESCE(SUM(nssf_amount),0) AS s FROM nssf_contributions"); total_contrib=list(cur.fetchone().values())[0]
    cur.execute("SELECT COALESCE(SUM(nssf_amount),0) AS s FROM nssf_contributions WHERE remitted=0"); unremitted=list(cur.fetchone().values())[0]
    cur.execute("""SELECT s.id,s.sacco_name,COUNT(DISTINCT c.id) AS members,
        COUNT(DISTINCT CASE WHEN c.nssf_registered=1 THEN c.id END) AS nssf_reg,
        COALESCE(SUM(sa.balance),0) AS total_savings,
        COALESCE((SELECT SUM(nc.nssf_amount) FROM nssf_contributions nc WHERE nc.sacco_id=s.id),0) AS nssf_contrib
        FROM sacco_profile s LEFT JOIN customers c ON c.sacco_id=s.id
        LEFT JOIN savings_accounts sa ON sa.sacco_id=s.id
        GROUP BY s.id,s.sacco_name ORDER BY nssf_contrib DESC"""); per_sacco=cur.fetchall()
    cur.close(); conn.close()
    return dict(saccos=saccos,total_mem=total_mem,total_nssf=total_nssf,total_loans=total_loans,
                total_savings=total_savings,total_contrib=total_contrib,unremitted=unremitted,per_sacco=per_sacco)

def _make_nssf_csv(sacco_name,period,rows,sacco_id):
    conn=get_db_connection(); cur=conn.cursor()
    output=io.StringIO(); w=csv.writer(output)
    w.writerow(["NSSF CONTRIBUTION SUBMISSION"])
    w.writerow(["SACCO Name",sacco_name])
    w.writerow(["Period",period])
    w.writerow(["Generated By","CommunityFinanceOS — SaccoOS Platform"])
    w.writerow(["Generated On",datetime.now().strftime("%Y-%m-%d %H:%M")])
    w.writerow(["Total Members",len(rows)])
    w.writerow(["Total Amount (UGX)",f"{sum(r['nssf_amount'] for r in rows):,.2f}"])
    w.writerow([])
    w.writerow(["Full Name","National ID","NSSF Number","Phone","Contribution (UGX)","Period","Transaction Date","Status"])
    for r in rows:
        cur.execute("SELECT name,national_id,nssf_number,phone FROM customers WHERE id=%s",(r['customer_id'],))
        c=cur.fetchone()
        if c:
            w.writerow([c['name'],c['national_id'] or "",c['nssf_number'] or "PENDING",
                        c['phone'],f"{r['nssf_amount']:,.2f}",r['period'],r['created_at'],
                        "Remitted" if r['remitted'] else "Pending"])
    cur.close(); conn.close()
    return output.getvalue().encode('utf-8')

def _make_outreach_csv(sacco_name,rows):
    output=io.StringIO(); w=csv.writer(output)
    w.writerow(["NSSF REGISTRATION OUTREACH LIST"])
    w.writerow(["SACCO Name",sacco_name])
    w.writerow(["Generated By","CommunityFinanceOS — SaccoOS Platform"])
    w.writerow(["Generated On",datetime.now().strftime("%Y-%m-%d %H:%M")])
    w.writerow(["Purpose","Members not yet registered with NSSF — for direct outreach"])
    w.writerow(["Total Records",len(rows)])
    w.writerow([])
    w.writerow(["Full Name","National ID","Phone","Gender","Village","Parish","Enrolled Date"])
    for r in rows:
        w.writerow([r['name'],r['national_id'] or "",r['phone'],r['gender'] or "",
                    r['village'] or "",r['parish'] or "",r['created_at']])
    return output.getvalue().encode('utf-8')

def _render_executive_dashboard(d,sacco_name):
    _section_header("📋","Executive Dashboard",f"{sacco_name} — {date.today().strftime('%B %Y')}")
    members=d['members']; loans=d['loans']; schedule=d['schedule']
    savings_accs=d['savings_accounts']; nssf=d['nssf']; gold=d['gold']
    total_mem=len(members)
    active_loans=[l for l in loans if l['status']=='Active']
    outstanding=sum(l['balance'] for l in active_loans)
    total_savings=sum(a['balance'] for a in savings_accs)
    nssf_reg=sum(1 for m in members if m['nssf_registered'])
    compliance=(nssf_reg/total_mem*100) if total_mem else 0
    total_contrib=sum(r['nssf_amount'] for r in nssf)
    unremitted=sum(r['nssf_amount'] for r in nssf if not r['remitted'])
    today_str=date.today().strftime('%Y-%m-%d')
    overdue_ids={r['loan_id'] for r in schedule if r['status']!='Paid' and r['due_date'] < today_str}
    par_amount=sum(l['balance'] for l in active_loans if l['id'] in overdue_ids)
    par_rate=(par_amount/outstanding*100) if outstanding>0 else 0
    due_total=sum(r['due_amount'] for r in schedule)
    paid_total=sum(r['paid_amount'] for r in schedule)
    repay_rate=(paid_total/due_total*100) if due_total>0 else 100
    gold_earners=len(set(r['customer_id'] for r in gold))
    gold_pct=(gold_earners/total_mem*100) if total_mem else 0

    cols=st.columns(4)
    cards=[("Total Members",f"{total_mem:,}","enrolled in SACCO",BLUE),
           ("NSSF Compliance",f"{compliance:.1f}% {_rag_label(compliance,80,50)}",f"{nssf_reg} registered",GREEN if compliance>=80 else AMBER if compliance>=50 else RED),
           ("Net Savings Held",f"UGX {total_savings:,.0f}","current balance",GOLD),
           ("Active Loan Portfolio",f"UGX {outstanding:,.0f}",f"{len(active_loans)} loans",BLUE)]
    for col,(label,value,sub,color) in zip(cols,cards):
        col.markdown(_stat_card(label,value,sub,color),unsafe_allow_html=True)

    st.markdown("<div style='margin-top:0.8rem;'></div>",unsafe_allow_html=True)
    cols2=st.columns(4)
    cards2=[("Portfolio at Risk",f"{par_rate:.1f}% {_rag_label(par_rate,5,15,False)}",f"UGX {par_amount:,.0f}",RED if par_rate>15 else AMBER if par_rate>5 else GREEN),
            ("Repayment Rate",f"{repay_rate:.1f}% {_rag_label(repay_rate,85,70)}","of scheduled installments",GREEN if repay_rate>=85 else AMBER if repay_rate>=70 else RED),
            ("NSSF Contributions",f"UGX {total_contrib:,.0f}",f"UGX {unremitted:,.0f} pending",GOLD),
            ("Gold Points Members",f"{gold_pct:.0f}% {_rag_label(gold_pct,60,30)}",f"{gold_earners} active earners",GOLD)]
    for col,(label,value,sub,color) in zip(cols2,cards2):
        col.markdown(_stat_card(label,value,sub,color),unsafe_allow_html=True)

    health=[
        (f"NSSF: {compliance:.1f}%",GREEN if compliance>=80 else AMBER if compliance>=50 else RED),
        (f"PAR: {par_rate:.1f}%",GREEN if par_rate<=5 else AMBER if par_rate<=15 else RED),
        (f"Repayment: {repay_rate:.1f}%",GREEN if repay_rate>=85 else AMBER if repay_rate>=70 else RED),
        (f"Gold: {gold_pct:.0f}%",GREEN if gold_pct>=60 else AMBER if gold_pct>=30 else RED),
    ]
    badges=" &nbsp;&nbsp; ".join(f'<span style="background:{c};color:#fff;padding:3px 10px;border-radius:12px;font-size:0.78rem;font-weight:600;">{t}</span>' for t,c in health)
    st.markdown(f'<div style="margin-top:0.8rem;">{badges}</div>',unsafe_allow_html=True)

def _render_portfolio(d):
    _section_header("💰","Portfolio Analysis","PAR30, repayment rates, gender/youth cuts")
    loans=d['loans']; schedule=d['schedule']; members=d['members']
    member_map={m['id']:m for m in members}
    active=[l for l in loans if l['status']=='Active']
    closed=[l for l in loans if l['status']=='Closed']
    outstanding=sum(l['balance'] for l in active)
    today_str=date.today().strftime('%Y-%m-%d'); today_dt=date.today()
    loan_max_overdue=defaultdict(int)
    for r in schedule:
        if r['status']!='Paid' and r['due_date']:
            try:
                days=(today_dt-datetime.strptime(r['due_date'],'%Y-%m-%d').date()).days
                if days>0: loan_max_overdue[r['loan_id']]=max(loan_max_overdue[r['loan_id']],days)
            except: pass
    par30_ids={lid for lid,d in loan_max_overdue.items() if d>=30}
    par90_ids={lid for lid,d in loan_max_overdue.items() if d>=90}
    par30_amt=sum(l['balance'] for l in active if l['id'] in par30_ids)
    par90_amt=sum(l['balance'] for l in active if l['id'] in par90_ids)
    par30_rate=(par30_amt/outstanding*100) if outstanding>0 else 0
    due_total=sum(r['due_amount'] or 0 for r in schedule)
    paid_total=sum(r['paid_amount'] or 0 for r in schedule)
    repay_rate=(paid_total/due_total*100) if due_total>0 else 100

    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Total Loans",len(loans)); c2.metric("Active",len(active))
    c3.metric("Closed",len(closed))
    c4.metric("PAR30 Rate",f"{par30_rate:.1f}%",delta=f"UGX {par30_amt:,.0f}",delta_color="inverse")
    c5.metric("Repayment Rate",f"{repay_rate:.1f}%")

    if outstanding>0:
        st.write("**PAR Ageing Buckets:**")
        def par_amt(days): return sum(l['balance'] for l in active if l['id'] in {lid for lid,d in loan_max_overdue.items() if d>=days})
        def par_cnt(days): return len([l for l in active if l['id'] in {lid for lid,d in loan_max_overdue.items() if d>=days}])
        st.dataframe([
            {"Bucket":"PAR1 (1+ days)","Loans":par_cnt(1),"Amount":par_amt(1),"% Port.":f"{par_amt(1)/outstanding*100:.1f}%"},
            {"Bucket":"PAR30 (30+ days)","Loans":par_cnt(30),"Amount":par30_amt,"% Port.":f"{par30_rate:.1f}%"},
            {"Bucket":"PAR60 (60+ days)","Loans":par_cnt(60),"Amount":par_amt(60),"% Port.":f"{par_amt(60)/outstanding*100:.1f}%"},
            {"Bucket":"PAR90 (90+ days)","Loans":par_cnt(90),"Amount":par90_amt,"% Port.":f"{par90_amt/outstanding*100:.1f}%"},
        ],column_config={"Amount":money_column()},use_container_width=True,hide_index=True)

    fl=sum(1 for l in loans if (l.get('customer_gender') or (member_map.get(l['customer_id'],{}) or {}).get('gender','') or '').lower()=='female')
    fa=sum(l['principal'] for l in loans if (l.get('customer_gender') or (member_map.get(l['customer_id'],{}) or {}).get('gender','') or '').lower()=='female')
    total_p=sum(l['principal'] for l in loans) or 1
    g1,g2=st.columns(2)
    g1.metric("Female Borrowers",fl,f"{fl/len(loans)*100:.0f}% of loans" if loans else "0%")
    g2.metric("Female Loan Volume",f"UGX {fa:,.0f}",f"{fa/total_p*100:.0f}% of principal")

def _render_demographics(d):
    _section_header("👥","Membership Demographics","Required for PDM, Emyooga, and NDP IV government programme reporting")
    members=d['members']; total=len(members)
    if not total: st.info("No members enrolled yet."); return
    female=sum(1 for m in members if (m['gender'] or '').lower()=='female')
    youth=sum(1 for m in members if (_calculate_age(m['date_of_birth']) or 0) in range(18,36))
    pwd=sum(1 for m in members if (m['pwd_status'] or '').lower()=='yes')
    subsistence=sum(1 for m in members if (m['subsistence_status'] or '').lower()=='yes')
    nssf_reg=sum(1 for m in members if m['nssf_registered'])
    pdm_core=sum(1 for m in members if (m['subsistence_status'] or '').lower()=='yes'
                 and ((m['gender'] or '').lower()=='female' or (_calculate_age(m['date_of_birth']) or 0)<=35))

    d1,d2,d3,d4,d5,d6,d7=st.columns(7)
    d1.metric("Total Members",total)
    d2.metric("Female",female,f"{female/total*100:.0f}%")
    d3.metric("Male",total-female,f"{(total-female)/total*100:.0f}%")
    d4.metric("Youth (18–35)",youth,f"{youth/total*100:.0f}%")
    d5.metric("PWD",pwd,f"{pwd/total*100:.0f}%")
    d6.metric("Subsistence",subsistence,f"{subsistence/total*100:.0f}%")
    d7.metric("PDM Core",pdm_core,f"{pdm_core/total*100:.0f}%")

    st.write("**Occupation Breakdown:**")
    occ_counts=Counter(m['occupation'] or 'Unknown' for m in members)
    st.dataframe([{"Occupation":k,"Members":v,"Share":f"{v/total*100:.1f}%"}
                  for k,v in sorted(occ_counts.items(),key=lambda x:x[1],reverse=True)],
                 use_container_width=True,hide_index=True)

    st.write("**Membership Growth — Last 6 Months:**")
    months=_last_n_months(6)
    st.dataframe([{"Month":mo,"Cumulative Members":sum(1 for m in members if m['created_at'] and m['created_at'][:7]<=mo)} for mo in months],
                 use_container_width=True,hide_index=True)

def _render_savings(d):
    _section_header("🏦","Savings Performance","Mobilisation totals, monthly trend, channel split")
    accounts=d['savings_accounts']; txns=d['savings_txns']; members=d['members']
    if not accounts: st.info("No savings accounts opened yet."); return
    deposits=[t for t in txns if t['type']=='Deposit']
    withdrawals=[t for t in txns if t['type']=='Withdrawal']
    total_dep=sum(t['amount'] for t in deposits)
    total_wdl=sum(t['amount'] for t in withdrawals)
    net=total_dep-total_wdl
    avg=sum(a['balance'] for a in accounts)/len(accounts)
    pen=len(accounts)/len(members)*100 if members else 0
    active_bal=sum(l['balance'] for l in d['loans'] if l['status']=='Active')
    stl=(net/active_bal) if active_bal>0 else None

    s1,s2,s3,s4,s5=st.columns(5)
    s1.metric("Accounts",len(accounts)); s2.metric("Total Mobilised",f"UGX {total_dep:,.0f}")
    s3.metric("Net Savings",f"UGX {net:,.0f}"); s4.metric("Avg Balance",f"UGX {avg:,.0f}")
    s5.metric("Penetration",f"{pen:.0f}%")
    if stl: st.metric("Savings-to-Loan Ratio",f"{stl:.2f}x")

    st.write("**Monthly Deposit Trend — Last 6 Months:**")
    months=_last_n_months(6)
    st.dataframe([{"Month":mo,
                   "Deposits":sum(t['amount'] for t in deposits if t['date'] and t['date'][:7]==mo),
                   "Withdrawals":sum(t['amount'] for t in withdrawals if t['date'] and t['date'][:7]==mo),
                   "Net":sum(t['amount'] for t in deposits if t['date'] and t['date'][:7]==mo)-sum(t['amount'] for t in withdrawals if t['date'] and t['date'][:7]==mo)}
                  for mo in months],
                 column_config={"Deposits":money_column(),"Withdrawals":money_column(),"Net":money_column()},
                 use_container_width=True,hide_index=True)

    channels=Counter(t['channel'] or 'Not recorded' for t in deposits)
    ch_total=sum(channels.values()) or 1
    st.write("**Payment Channel Breakdown:**")
    st.dataframe([{"Channel":k,"Transactions":v,"Share":f"{v/ch_total*100:.1f}%"}
                  for k,v in sorted(channels.items(),key=lambda x:x[1],reverse=True)],
                 use_container_width=True,hide_index=True)

def _render_nssf_compliance(d,sacco_name):
    _section_header("🇺🇬","NSSF Compliance Report","Contribution trajectory, gap analysis, Gold Points ROI")
    members=d['members']; nssf=d['nssf']; gold=d['gold']
    total=len(members); reg=sum(1 for m in members if m['nssf_registered'])
    comp_pct=(reg/total*100) if total else 0
    total_contrib=sum(r['nssf_amount'] for r in nssf)
    unremitted=sum(r['nssf_amount'] for r in nssf if not r['remitted'])
    avg_contrib=(total_contrib/reg) if reg else 0
    months3=_last_n_months(3)
    recent=sum(r['nssf_amount'] for r in nssf if r['period'] in months3)
    projected=recent/3*12 if recent else 0

    n1,n2,n3,n4,n5=st.columns(5)
    n1.metric("Compliance",f"{comp_pct:.1f}%",f"{reg} of {total}")
    n2.metric("Total Contributed",f"UGX {total_contrib:,.0f}","all time")
    n3.metric("Avg / Member",f"UGX {avg_contrib:,.0f}","lifetime")
    n4.metric("Unremitted",f"UGX {unremitted:,.0f}","pending")
    n5.metric("Projected Annual",f"UGX {projected:,.0f}","last 3 months basis")

    st.write("**Contribution Trajectory — Last 12 Months:**")
    months12=_last_n_months(12); cumulative=0
    rows=[]
    for mo in months12:
        mo_amt=sum(r['nssf_amount'] for r in nssf if r['period']==mo)
        mo_mem=len(set(r['customer_id'] for r in nssf if r['period']==mo))
        cumulative+=mo_amt
        rows.append({"Period":mo,"Contributing Members":mo_mem,"Amount (UGX)":mo_amt,"Cumulative (UGX)":cumulative})
    st.dataframe(rows,column_config={"Amount (UGX)":money_column(),"Cumulative (UGX)":money_column()},
                 use_container_width=True,hide_index=True)

    gold_earner_ids=set(r['customer_id'] for r in gold)
    gold_and_nssf=sum(1 for m in members if m['nssf_registered'] and m['id'] in gold_earner_ids)
    streak_3=sum(1 for r in gold if r['reason']=='streak_3_months')
    streak_6=sum(1 for r in gold if r['reason']=='streak_6_months')
    total_pts=sum(r['points'] for r in gold)

    st.write("**Gold Points Impact:**")
    gi1,gi2,gi3,gi4=st.columns(4)
    gi1.metric("Gold+NSSF Members",gold_and_nssf); gi2.metric("3-Month Streaks",streak_3)
    gi3.metric("6-Month Patriot Streaks",streak_6); gi4.metric("Total Points Awarded",f"{total_pts:,}")

def _render_nssf_export(d,sacco_name,sacco_id):
    _section_header("📥","NSSF Monthly Submission Export","Clean CSV for NSSF submission")
    nssf=d['nssf']
    if not nssf: st.info("No NSSF contributions yet."); return
    periods=sorted(set(r['period'] for r in nssf),reverse=True)
    sel=st.selectbox("Select period",periods)
    period_rows=[r for r in nssf if r['period']==sel]
    total_amt=sum(r['nssf_amount'] for r in period_rows)
    remitted=sum(1 for r in period_rows if r['remitted'])
    st.info(f"**{len(period_rows)} contributions** | **UGX {total_amt:,.0f}** | {remitted} remitted, {len(period_rows)-remitted} pending")

    conn=get_db_connection(); cur=conn.cursor()
    preview=[]
    for r in period_rows:
        cur.execute("SELECT name,national_id,nssf_number,phone FROM customers WHERE id=%s",(r['customer_id'],))
        c=cur.fetchone()
        if c:
            preview.append({"Name":c['name'],"National ID":c['national_id'] or "—",
                            "NSSF No.":c['nssf_number'] or "PENDING","Phone":c['phone'],
                            "Amount (UGX)":r['nssf_amount'],"Status":"✅ Remitted" if r['remitted'] else "⏳ Pending"})
    cur.close(); conn.close()
    st.dataframe(preview,column_config={"Amount (UGX)":money_column()},use_container_width=True,hide_index=True)
    csv_bytes=_make_nssf_csv(sacco_name,sel,period_rows,sacco_id)
    st.download_button(label=f"⬇️ Download NSSF Submission — {sel}",data=csv_bytes,
                       file_name=f"nssf_submission_{sacco_name.replace(' ','_')}_{sel}.csv",
                       mime="text/csv",type="primary")

def _render_outreach_export(d,sacco_name,sacco_id):
    _section_header("📋","NSSF Outreach Export","Unregistered members list for NSSF registration campaigns")
    members=d['members']
    unreg=[m for m in members if not m['nssf_registered']]
    if not unreg: st.success("✅ No unregistered members."); return
    st.warning(f"**{len(unreg)} members** not yet registered with NSSF.")
    st.dataframe([{"Name":m['name'],"Phone":m['phone'],"National ID":m['national_id'] or "—",
                   "Gender":m['gender'] or "—","Village":m['village'] or "—",
                   "Parish":m['parish'] or "—","Enrolled":m['created_at']} for m in unreg],
                 use_container_width=True,hide_index=True)
    st.download_button(label=f"⬇️ Download Outreach List ({len(unreg)} members)",
                       data=_make_outreach_csv(sacco_name,unreg),
                       file_name=f"nssf_outreach_{sacco_name.replace(' ','_')}_{date.today()}.csv",
                       mime="text/csv",type="primary")

def _render_cross_sacco():
    _section_header("🌍","Cross-SACCO Platform Aggregate","Platform-wide view — super admin only")
    agg=get_all_sacco_aggregate()
    comp_rate=(agg['total_nssf']/agg['total_mem']*100) if agg['total_mem'] else 0
    a1,a2,a3,a4,a5=st.columns(5)
    a1.metric("Total Members",f"{agg['total_mem']:,}"); a2.metric("NSSF Registered",f"{agg['total_nssf']:,}",f"{comp_rate:.1f}%")
    a3.metric("Total Loans",f"{agg['total_loans']:,}"); a4.metric("Total Savings",f"UGX {agg['total_savings']:,.0f}")
    a5.metric("Total NSSF Contrib.",f"UGX {agg['total_contrib']:,.0f}",f"UGX {agg['unremitted']:,.0f} unremitted")
    st.write("**Per-SACCO Breakdown:**")
    st.dataframe([{"SACCO":s['sacco_name'] or f"SACCO #{s['id']}","Members":s['members'],
                   "NSSF Reg.":s['nssf_reg'],
                   "Compliance":f"{s['nssf_reg']/s['members']*100:.1f}%" if s['members'] else "0%",
                   "Savings (UGX)":s['total_savings'],"NSSF Contrib (UGX)":s['nssf_contrib']}
                  for s in agg['per_sacco']],
                 column_config={"Savings (UGX)":money_column(),"NSSF Contrib (UGX)":money_column()},
                 use_container_width=True,hide_index=True)

def render():
    sacco_id  = st.session_state.get('current_sacco_id')
    user_role = st.session_state.get('user_role')
    if sacco_id is None:
        st.warning("No SACCO selected.")
        return

    try:
        from dateutil.relativedelta import relativedelta
    except ImportError:
        st.error("Missing dependency: python-dateutil. Check requirements.txt.")
        return

    d=get_full_sacco_data(sacco_id)
    sacco_name=(d['sacco_profile']['sacco_name'] if d['sacco_profile'] else f"SACCO #{sacco_id}")

    sections=["📋 Executive Dashboard","💰 Portfolio Analysis","👥 Membership Demographics",
              "🏦 Savings Performance","🇺🇬 NSSF Compliance Report",
              "📥 NSSF Monthly Export","📋 NSSF Outreach Export"]
    if user_role==ROLE_SUPER_ADMIN:
        sections.append("🌍 Cross-SACCO Aggregate")

    section=st.radio("Jump to section",sections,horizontal=True)
    st.divider()

    if   section=="📋 Executive Dashboard":       _render_executive_dashboard(d,sacco_name)
    elif section=="💰 Portfolio Analysis":         _render_portfolio(d)
    elif section=="👥 Membership Demographics":    _render_demographics(d)
    elif section=="🏦 Savings Performance":        _render_savings(d)
    elif section=="🇺🇬 NSSF Compliance Report":   _render_nssf_compliance(d,sacco_name)
    elif section=="📥 NSSF Monthly Export":        _render_nssf_export(d,sacco_name,sacco_id)
    elif section=="📋 NSSF Outreach Export":       _render_outreach_export(d,sacco_name,sacco_id)
    elif section=="🌍 Cross-SACCO Aggregate" and user_role==ROLE_SUPER_ADMIN: _render_cross_sacco()

    st.divider()
    st.write("#### 📨 Client Messages Log")
    messages=get_messages(sacco_id,limit=50)
    if messages:
        st.dataframe([{"Date":m['sent_at'],"Customer":m['customer_name'],"Message":m['message']} for m in messages],
                     use_container_width=True,hide_index=True)
    else:
        st.info("No messages sent yet.")

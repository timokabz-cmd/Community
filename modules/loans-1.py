import streamlit as st
import calendar
from datetime import datetime, date, timedelta
from database import get_db_connection
from modules.accounting import post_double_entry
from modules.customers import get_customers, get_customer
from modules.theme import status_badge_html, money_column

def add_months(source_date, months):
    month = source_date.month - 1 + months
    year  = source_date.year + month // 12
    month = month % 12 + 1
    day   = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

def _calculate_age(dob_str):
    if not dob_str:
        return None
    try:
        dob   = datetime.strptime(dob_str, '%Y-%m-%d').date()
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except ValueError:
        return None

def issue_loan(customer_id, principal, interest_rate, term_months, sacco_id):
    total_due = round(principal * (1 + interest_rate / 100), 2)
    conn      = get_db_connection()
    cur       = conn.cursor()
    today_str = datetime.now().strftime('%Y-%m-%d')
    cur.execute("""
        INSERT INTO loans
            (customer_id, principal, interest_rate, term_months,
             total_due, balance, status, disbursed_date, sacco_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """, (customer_id, principal, interest_rate, term_months,
          total_due, total_due, 'Active', today_str, sacco_id))
    loan_id = cur.fetchone()['id']

    installment   = round(total_due / term_months, 2)
    disbursed     = datetime.now().date()
    running_total = 0
    for i in range(1, term_months + 1):
        due_date = add_months(disbursed, i)
        amount   = installment
        if i == term_months:
            amount = round(total_due - running_total, 2)
        running_total += amount
        cur.execute(
            "INSERT INTO loan_schedule (loan_id, installment_no, due_date, due_amount) VALUES (%s,%s,%s,%s)",
            (loan_id, i, due_date.strftime('%Y-%m-%d'), amount)
        )
    conn.commit()
    cur.close()
    conn.close()
    post_double_entry(
        "Loans Receivable", "Cash/Bank", principal,
        f"Loan #{loan_id} disbursed", f"LOAN-{loan_id}", sacco_id=sacco_id
    )
    return loan_id

def get_loans(sacco_id, status=None):
    conn = get_db_connection()
    cur  = conn.cursor()
    base = """
        SELECT loans.*, customers.name AS customer_name,
               customers.phone AS customer_phone,
               customers.gender AS customer_gender,
               customers.date_of_birth AS customer_dob,
               customers.nssf_registered AS customer_nssf
        FROM loans
        JOIN customers ON loans.customer_id = customers.id
        WHERE loans.sacco_id = %s
    """
    if status:
        cur.execute(base + " AND loans.status = %s ORDER BY loans.id DESC", (sacco_id, status))
    else:
        cur.execute(base + " ORDER BY loans.id DESC", (sacco_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_loan(loan_id):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT loans.*, customers.name AS customer_name,
               customers.phone AS customer_phone,
               customers.nssf_registered AS customer_nssf
        FROM loans
        JOIN customers ON loans.customer_id = customers.id
        WHERE loans.id = %s
    """, (loan_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def get_schedule(loan_id):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM loan_schedule WHERE loan_id = %s ORDER BY installment_no", (loan_id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_upcoming_installments(sacco_id, days=7):
    conn  = get_db_connection()
    cur   = conn.cursor()
    today = date.today()
    end   = today + timedelta(days=days)
    cur.execute("""
        SELECT loan_schedule.*, customers.name AS customer_name,
               customers.phone AS customer_phone
        FROM loan_schedule
        JOIN loans     ON loan_schedule.loan_id   = loans.id
        JOIN customers ON loans.customer_id = customers.id
        WHERE loan_schedule.status  != 'Paid'
          AND loan_schedule.due_date BETWEEN %s AND %s
          AND loans.status   = 'Active'
          AND loans.sacco_id = %s
        ORDER BY loan_schedule.due_date
    """, (today.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), sacco_id))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def allocate_payment(loan_id, amount):
    conn         = get_db_connection()
    cur          = conn.cursor()
    cur.execute(
        "SELECT * FROM loan_schedule WHERE loan_id = %s AND status != 'Paid' ORDER BY installment_no",
        (loan_id,)
    )
    installments = cur.fetchall()
    remaining    = amount
    for inst in installments:
        if remaining <= 0:
            break
        outstanding = inst['due_amount'] - inst['paid_amount']
        pay         = min(outstanding, remaining)
        new_paid    = round(inst['paid_amount'] + pay, 2)
        new_status  = 'Paid' if new_paid >= inst['due_amount'] - 0.01 else 'Partial'
        cur.execute(
            "UPDATE loan_schedule SET paid_amount = %s, status = %s WHERE id = %s",
            (new_paid, new_status, inst['id'])
        )
        remaining -= pay
    conn.commit()
    cur.close()
    conn.close()

def close_loan_manually(loan_id, sacco_id):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("UPDATE loans SET status = 'Closed', balance = 0 WHERE id = %s", (loan_id,))
    conn.commit()
    cur.close()
    conn.close()
    post_double_entry(
        "Loan Write-Off Expense", "Loans Receivable", 0,
        f"Loan #{loan_id} manually closed by admin", f"CLOSE-{loan_id}", sacco_id=sacco_id
    )

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected. Set up a SACCO Profile first.")
        return

    from modules.guarantors import add_guarantor, get_guarantors
    from modules.collateral  import add_collateral, get_collateral

    loans        = get_loans(sacco_id)
    active_loans = [l for l in loans if l['status'] == 'Active']
    closed_loans = [l for l in loans if l['status'] == 'Closed']
    outstanding  = sum(l['balance'] for l in active_loans)
    female_loans = [l for l in loans if (l['customer_gender'] or '').lower() == 'female']
    youth_loans  = [l for l in loans if (_calculate_age(l['customer_dob']) or 0) in range(18, 36)]
    nssf_loans   = [l for l in loans if l['customer_nssf'] == 1]

    st.write("#### Portfolio Overview")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Loans",    len(loans))
    c2.metric("Active",         len(active_loans))
    c3.metric("Closed",         len(closed_loans))
    c4.metric("Outstanding",    f"UGX {outstanding:,.0f}")
    c5.metric("NSSF Borrowers", f"{len(nssf_loans)}",
              f"{len(nssf_loans)/len(loans)*100:.0f}% of loans" if loans else "0%")

    g1, g2, g3 = st.columns(3)
    g1.metric("Female Borrowers",     f"{len(female_loans)}",
              f"{len(female_loans)/len(loans)*100:.0f}%" if loans else "0%")
    g2.metric("Youth Borrowers (18–35)", f"{len(youth_loans)}",
              f"{len(youth_loans)/len(loans)*100:.0f}%" if loans else "0%")
    g3.metric("Avg Loan Size",
              f"UGX {sum(l['principal'] for l in loans)/len(loans):,.0f}" if loans else "UGX 0")

    st.divider()
    st.write("#### Issue a New Loan")
    customers = get_customers(sacco_id)
    if not customers:
        st.warning("Add a customer first before issuing a loan.")
    else:
        with st.form("issue_loan_form", clear_on_submit=True):
            customer_map    = {f"{c['name']} ({c['phone']})": c for c in customers}
            customer_choice = st.selectbox("Customer", list(customer_map.keys()))
            selected_cust   = customer_map[customer_choice]
            if not selected_cust['nssf_registered']:
                st.warning("⚠️ This customer is not NSSF registered. Encourage them to register at nssfug.org.")
            principal     = st.number_input("Principal amount (UGX)", min_value=0.0, step=10000.0)
            interest_rate = st.number_input("Flat interest rate (%)", min_value=0.0, step=1.0, value=10.0)
            term_months   = st.number_input("Term (months)", min_value=1, step=1, value=3)
            if principal > 0:
                total_p   = round(principal * (1 + interest_rate / 100), 2)
                install_p = round(total_p / term_months, 2)
                st.info(f"Total repayable: **UGX {total_p:,.0f}** | Monthly installment: **UGX {install_p:,.0f}**")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                g_name         = st.text_input("Guarantor full name")
                g_nid          = st.text_input("Guarantor National ID")
            with col_g2:
                g_phone        = st.text_input("Guarantor phone number")
                g_relationship = st.text_input("Relationship to borrower")
            col_c1, col_c2 = st.columns(2)
            with col_c1: c_description = st.text_input("Collateral description")
            with col_c2: c_value       = st.number_input("Collateral value (UGX)", min_value=0.0, step=10000.0, key="cval")
            submitted = st.form_submit_button("Disburse Loan", type="primary")
            if submitted:
                if principal <= 0:
                    st.error("Principal must be greater than zero.")
                else:
                    loan_id = issue_loan(selected_cust['id'], principal, interest_rate, int(term_months), sacco_id)
                    st.success(f"✅ Loan #{loan_id} disbursed to **{customer_choice}**.")
                    if g_name and g_phone:
                        add_guarantor(loan_id, g_name, g_phone, g_nid, g_relationship)
                    if c_description:
                        add_collateral(loan_id, c_description, c_value)

    st.divider()
    st.write("#### All Loans")
    if not loans:
        st.info("No loans issued yet.")
        return

    today_str = date.today().strftime('%Y-%m-%d')
    st.dataframe(
        [{"Loan ID": l['id'], "Customer": l['customer_name'],
          "Principal": l['principal'], "Balance": l['balance'],
          "Status": l['status'], "NSSF": "✅" if l['customer_nssf'] else "⚠️",
          "Disbursed": l['disbursed_date']} for l in loans],
        column_config={"Principal": money_column(), "Balance": money_column()},
        use_container_width=True
    )

    st.divider()
    st.write("#### Loan Detail View")
    loan_map    = {f"Loan #{l['id']} — {l['customer_name']} ({l['status']})": l['id'] for l in loans}
    choice      = st.selectbox("Select a loan", list(loan_map.keys()))
    sel_loan_id = loan_map[choice]
    sel_loan    = next(l for l in loans if l['id'] == sel_loan_id)

    col_h1, col_h2 = st.columns([2,1])
    with col_h1:
        st.markdown(
            f"**{sel_loan['customer_name']}** — UGX {sel_loan['balance']:,.0f} outstanding",
            unsafe_allow_html=True
        )
        st.caption(f"Loan #{sel_loan['id']} | Principal: UGX {sel_loan['principal']:,.0f} | Rate: {sel_loan['interest_rate']}% | Disbursed: {sel_loan['disbursed_date']}")
        if not sel_loan['customer_nssf']:
            st.caption("⚠️ Borrower not NSSF registered.")
    with col_h2:
        if sel_loan['status'] == 'Active':
            if st.button("🔒 Close Loan Manually", type="secondary"):
                close_loan_manually(sel_loan_id, sacco_id)
                st.success(f"Loan #{sel_loan_id} closed.")
                st.rerun()

    schedule = get_schedule(sel_loan_id)
    if schedule:
        today_s = date.today().strftime('%Y-%m-%d')
        st.dataframe(
            [{"No.": s['installment_no'],
              "Due Date": s['due_date'] + (" 🔴" if s['status'] != 'Paid' and s['due_date'] < today_s else ""),
              "Due": s['due_amount'], "Paid": s['paid_amount'],
              "Remaining": round(s['due_amount'] - s['paid_amount'], 2),
              "Status": s['status']} for s in schedule],
            column_config={"Due": money_column(), "Paid": money_column(), "Remaining": money_column()},
            use_container_width=True, hide_index=True
        )

    col_guar, col_coll = st.columns(2)
    with col_guar:
        st.write("**Guarantor(s):**")
        glist = get_guarantors(sel_loan_id)
        if glist:
            st.dataframe([{"Name": g['name'], "Phone": g['phone'], "NID": g['national_id'], "Relationship": g['relationship']} for g in glist], use_container_width=True, hide_index=True)
        else:
            st.caption("No guarantor on file.")
    with col_coll:
        st.write("**Collateral:**")
        clist = get_collateral(sel_loan_id)
        if clist:
            st.dataframe([{"Description": c['description'], "Est. Value": c['estimated_value'], "Status": c['status']} for c in clist], column_config={"Est. Value": money_column()}, use_container_width=True, hide_index=True)
        else:
            st.caption("No collateral on file.")

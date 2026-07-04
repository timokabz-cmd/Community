import streamlit as st
import calendar
from datetime import datetime, date, timedelta
from database import get_db_connection
from modules.accounting import post_double_entry
from modules.customers import get_customers
from modules.theme import status_badge_html, money_column

def add_months(source_date, months):
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

def issue_loan(customer_id, principal, interest_rate, term_months, sacco_id):
    total_due = round(principal * (1 + interest_rate / 100), 2)
    conn = get_db_connection()
    today_str = datetime.now().strftime('%Y-%m-%d')
    cursor = conn.execute(
        """INSERT INTO loans (customer_id, principal, interest_rate, term_months, total_due, balance, status, disbursed_date, sacco_id) VALUES (?,?,?,?,?,?,?,?,?)""",
        (customer_id, principal, interest_rate, term_months, total_due, total_due, 'Active', today_str, sacco_id)
    )
    loan_id = cursor.lastrowid

    # Generate an equal-installment repayment schedule
    installment = round(total_due / term_months, 2)
    disbursed = datetime.now().date()
    running_total = 0
    for i in range(1, term_months + 1):
        due_date = add_months(disbursed, i)
        amount = installment
        if i == term_months:
            amount = round(total_due - running_total, 2)  # absorb rounding on the last installment
        running_total += amount
        conn.execute(
            "INSERT INTO loan_schedule (loan_id, installment_no, due_date, due_amount) VALUES (?,?,?,?)",
            (loan_id, i, due_date.strftime('%Y-%m-%d'), amount)
        )

    conn.commit()
    conn.close()

    post_double_entry("Loans Receivable", "Cash/Bank", principal, f"Loan #{loan_id} disbursed", f"LOAN-{loan_id}", sacco_id=sacco_id)
    return loan_id

def get_loans(sacco_id, status=None):
    conn = get_db_connection()
    query = """SELECT loans.*, customers.name as customer_name, customers.phone as customer_phone FROM loans JOIN customers ON loans.customer_id = customers.id WHERE loans.sacco_id = ?"""
    if status:
        rows = conn.execute(query + " AND loans.status = ? ORDER BY loans.id DESC", (sacco_id, status)).fetchall()
    else:
        rows = conn.execute(query + " ORDER BY loans.id DESC", (sacco_id,)).fetchall()
    conn.close()
    return rows

def get_loan(loan_id):
    conn = get_db_connection()
    row = conn.execute(
        """SELECT loans.*, customers.name as customer_name, customers.phone as customer_phone FROM loans JOIN customers ON loans.customer_id = customers.id WHERE loans.id = ?""",
        (loan_id,)
    ).fetchone()
    conn.close()
    return row

def get_schedule(loan_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM loan_schedule WHERE loan_id = ? ORDER BY installment_no", (loan_id,)
    ).fetchall()
    conn.close()
    return rows

def get_upcoming_installments(sacco_id, days=7):
    """Installments due within the next N days — for dashboard notifications."""
    conn = get_db_connection()
    today = date.today()
    end = today + timedelta(days=days)
    rows = conn.execute(
        """SELECT loan_schedule.*, customers.name as customer_name, customers.phone as customer_phone FROM loan_schedule JOIN loans ON loan_schedule.loan_id = loans.id JOIN customers ON loans.customer_id = customers.id WHERE loan_schedule.status != 'Paid' AND loan_schedule.due_date BETWEEN ? AND ? AND loans.status = 'Active' AND loans.sacco_id = ? ORDER BY loan_schedule.due_date""",
        (today.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), sacco_id)
    ).fetchall()
    conn.close()
    return rows

def allocate_payment(loan_id, amount):
    """Applies a payment against the earliest outstanding installments, in order."""
    conn = get_db_connection()
    installments = conn.execute(
        "SELECT * FROM loan_schedule WHERE loan_id = ? AND status != 'Paid' ORDER BY installment_no",
        (loan_id,)
    ).fetchall()
    remaining = amount
    for inst in installments:
        if remaining <= 0:
            break
        outstanding = inst['due_amount'] - inst['paid_amount']
        pay = min(outstanding, remaining)
        new_paid = round(inst['paid_amount'] + pay, 2)
        new_status = 'Paid' if new_paid >= inst['due_amount'] - 0.01 else 'Partial'
        conn.execute(
            "UPDATE loan_schedule SET paid_amount = ?, status = ? WHERE id = ?",
            (new_paid, new_status, inst['id'])
        )
        remaining -= pay
    conn.commit()
    conn.close()

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected. Set up a SACCO Profile first.")
        return

    # Imported here (not at module top) to avoid a circular import: guarantors.py and
    # collateral.py both import get_loans from this module.
    from modules.guarantors import add_guarantor, get_guarantors
    from modules.collateral import add_collateral, get_collateral

    customers = get_customers(sacco_id)
    st.write("#### Issue a New Loan")
    if not customers:
        st.warning("Add a customer first before issuing a loan.")
    else:
        with st.form("issue_loan_form", clear_on_submit=True):
            customer_map = {f"{c['name']} ({c['phone']})": c['id'] for c in customers}
            customer_choice = st.selectbox("Customer", list(customer_map.keys()))
            principal = st.number_input("Principal amount (UGX)", min_value=0.0, step=10000.0)
            interest_rate = st.number_input("Flat interest rate (%)", min_value=0.0, step=1.0, value=10.0)
            term_months = st.number_input("Term (months)", min_value=1, step=1, value=3)

            st.write("**Guarantor (optional)**")
            g_name = st.text_input("Guarantor full name")
            g_phone = st.text_input("Guarantor phone number")
            g_nid = st.text_input("Guarantor National ID")
            g_relationship = st.text_input("Relationship to borrower")

            st.write("**Collateral (optional)**")
            c_description = st.text_input("Collateral description (e.g. 'Land title, Plot 12, Mukono')")
            c_value = st.number_input("Estimated value (UGX)", min_value=0.0, step=10000.0, key="collateral_value")

            submitted = st.form_submit_button("Disburse Loan")
            if submitted:
                if principal <= 0:
                    st.error("Principal must be greater than zero.")
                else:
                    loan_id = issue_loan(customer_map[customer_choice], principal, interest_rate, int(term_months), sacco_id)
                    st.success(f"Loan #{loan_id} disbursed for {customer_choice}, with a {int(term_months)}-month repayment schedule.")
                    if g_name and g_phone:
                        add_guarantor(loan_id, g_name, g_phone, g_nid, g_relationship)
                        st.success(f"Guarantor '{g_name}' attached to Loan #{loan_id}.")
                    if c_description:
                        add_collateral(loan_id, c_description, c_value)
                        st.success(f"Collateral registered against Loan #{loan_id}.")

    st.write("#### All Loans")
    loans = get_loans(sacco_id)
    if not loans:
        st.info("No loans issued yet.")
        return

    st.dataframe(
        [{"Loan ID": l['id'], "Customer": l['customer_name'], "Principal": l['principal'],
          "Rate %": l['interest_rate'], "Total Due": l['total_due'], "Balance": l['balance'],
          "Status": l['status'], "Disbursed": l['disbursed_date']} for l in loans],
        column_config={"Principal": money_column(), "Total Due": money_column(), "Balance": money_column()},
        use_container_width=True
    )

    st.write("#### View Loan Details")
    loan_map = {f"Loan #{l['id']} — {l['customer_name']}": l['id'] for l in loans}
    choice = st.selectbox("Select a loan", list(loan_map.keys()))
    selected_loan_id = loan_map[choice]
    selected_loan = next(l for l in loans if l['id'] == selected_loan_id)
    st.markdown(
        f"**{selected_loan['customer_name']}** — UGX {selected_loan['balance']:,.0f} outstanding &nbsp; "
        + status_badge_html(selected_loan['status'], kind=selected_loan['status']),
        unsafe_allow_html=True
    )

    schedule = get_schedule(selected_loan_id)
    st.write("**Repayment Schedule**")
    if schedule:
        st.dataframe(
            [{"Installment": s['installment_no'], "Due Date": s['due_date'], "Due Amount": s['due_amount'],
              "Paid": s['paid_amount'], "Status": s['status']} for s in schedule],
            column_config={"Due Amount": money_column(), "Paid": money_column()},
            use_container_width=True
        )
    else:
        st.info("No schedule found for this loan.")

    st.write("**Guarantor(s)**")
    guarantors = get_guarantors(selected_loan_id)
    if guarantors:
        st.dataframe(
            [{"Name": g['name'], "Phone": g['phone'], "National ID": g['national_id'],
              "Relationship": g['relationship']} for g in guarantors],
            use_container_width=True
        )
    else:
        st.caption("No guarantor on file for this loan.")

    st.write("**Collateral**")
    collateral_items = get_collateral(selected_loan_id)
    if collateral_items:
        st.dataframe(
            [{"Description": c['description'], "Estimated Value": c['estimated_value'],
              "Status": c['status']} for c in collateral_items],
            column_config={"Estimated Value": money_column()},
            use_container_width=True
        )
    else:
        st.caption("No collateral on file for this loan.")

    with st.expander("➕ Add a guarantor or collateral to this loan"):
        st.caption("For a guarantor or collateral that wasn't captured when the loan was issued.")
        with st.form(f"add_extra_{selected_loan_id}", clear_on_submit=True):
            st.write("**Guarantor**")
            eg_name = st.text_input("Guarantor full name", key="eg_name")
            eg_phone = st.text_input("Guarantor phone number", key="eg_phone")
            eg_nid = st.text_input("Guarantor National ID", key="eg_nid")
            eg_relationship = st.text_input("Relationship to borrower", key="eg_relationship")
            st.write("**Collateral**")
            ec_description = st.text_input("Collateral description", key="ec_description")
            ec_value = st.number_input("Estimated value (UGX)", min_value=0.0, step=10000.0, key="ec_value")
            submitted_extra = st.form_submit_button("Add to This Loan")
            if submitted_extra:
                added = False
                if eg_name and eg_phone:
                    add_guarantor(selected_loan_id, eg_name, eg_phone, eg_nid, eg_relationship)
                    added = True
                if ec_description:
                    add_collateral(selected_loan_id, ec_description, ec_value)
                    added = True
                if added:
                    st.success("Added to this loan.")
                    st.rerun()
                else:
                    st.warning("Enter a guarantor (name + phone) or a collateral description.")

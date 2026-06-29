import streamlit as st
import calendar
from datetime import datetime, date, timedelta
from database import get_db_connection
from modules.accounting import post_double_entry
from modules.customers import get_customers

def add_months(source_date, months):
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

def issue_loan(customer_id, principal, interest_rate, term_months):
    total_due = round(principal * (1 + interest_rate / 100), 2)
    conn = get_db_connection()
    today_str = datetime.now().strftime('%Y-%m-%d')
    cursor = conn.execute(
        """INSERT INTO loans (customer_id, principal, interest_rate, term_months, total_due, balance, status, disbursed_date) VALUES (?,?,?,?,?,?,?,?)""",
        (customer_id, principal, interest_rate, term_months, total_due, total_due, 'Active', today_str)
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

    post_double_entry("Loans Receivable", "Cash/Bank", principal, f"Loan #{loan_id} disbursed", f"LOAN-{loan_id}")
    return loan_id

def get_loans(status=None):
    conn = get_db_connection()
    query = """SELECT loans.*, customers.name as customer_name, customers.phone as customer_phone FROM loans JOIN customers ON loans.customer_id = customers.id"""
    if status:
        rows = conn.execute(query + " WHERE loans.status = ? ORDER BY loans.id DESC", (status,)).fetchall()
    else:
        rows = conn.execute(query + " ORDER BY loans.id DESC").fetchall()
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

def get_upcoming_installments(days=7):
    """Installments due within the next N days — for dashboard notifications."""
    conn = get_db_connection()
    today = date.today()
    end = today + timedelta(days=days)
    rows = conn.execute(
        """SELECT loan_schedule.*, customers.name as customer_name, customers.phone as customer_phone FROM loan_schedule JOIN loans ON loan_schedule.loan_id = loans.id JOIN customers ON loans.customer_id = customers.id WHERE loan_schedule.status != 'Paid' AND loan_schedule.due_date BETWEEN ? AND ? AND loans.status = 'Active' ORDER BY loan_schedule.due_date""",
        (today.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
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
    customers = get_customers()
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
            submitted = st.form_submit_button("Disburse Loan")
            if submitted:
                if principal <= 0:
                    st.error("Principal must be greater than zero.")
                else:
                    loan_id = issue_loan(customer_map[customer_choice], principal, interest_rate, int(term_months))
                    st.success(f"Loan #{loan_id} disbursed for {customer_choice}, with a {int(term_months)}-month repayment schedule.")

    st.write("#### All Loans")
    loans = get_loans()
    if not loans:
        st.info("No loans issued yet.")
        return

    st.dataframe(
        [{"Loan ID": l['id'], "Customer": l['customer_name'], "Principal": l['principal'],
          "Rate %": l['interest_rate'], "Total Due": l['total_due'], "Balance": l['balance'],
          "Status": l['status'], "Disbursed": l['disbursed_date']} for l in loans],
        use_container_width=True
    )

    st.write("#### View Repayment Schedule")
    loan_map = {f"Loan #{l['id']} — {l['customer_name']}": l['id'] for l in loans}
    choice = st.selectbox("Select a loan", list(loan_map.keys()))
    schedule = get_schedule(loan_map[choice])
    if schedule:
        st.dataframe(
            [{"Installment": s['installment_no'], "Due Date": s['due_date'], "Due Amount": s['due_amount'],
              "Paid": s['paid_amount'], "Status": s['status']} for s in schedule],
            use_container_width=True
        )
    else:
        st.info("No schedule found for this loan.")

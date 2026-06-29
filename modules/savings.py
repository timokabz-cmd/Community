import streamlit as st
from datetime import datetime
from database import get_db_connection
from modules.accounting import post_double_entry
from modules.customers import get_customers

def open_account(customer_id):
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM savings_accounts WHERE customer_id = ?", (customer_id,)).fetchone()
    if existing:
        conn.close()
        return existing['id']
    cursor = conn.execute(
        "INSERT INTO savings_accounts (customer_id, balance, opened_date) VALUES (?,0,?)",
        (customer_id, datetime.now().strftime('%Y-%m-%d'))
    )
    account_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return account_id

def get_accounts():
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT savings_accounts.*, customers.name as customer_name FROM savings_accounts JOIN customers ON savings_accounts.customer_id = customers.id ORDER BY savings_accounts.id DESC"""
    ).fetchall()
    conn.close()
    return rows

def deposit(account_id, amount):
    conn = get_db_connection()
    account = conn.execute("SELECT * FROM savings_accounts WHERE id = ?", (account_id,)).fetchone()
    new_balance = account['balance'] + amount
    conn.execute("UPDATE savings_accounts SET balance = ? WHERE id = ?", (new_balance, account_id))
    conn.execute(
        "INSERT INTO savings_transactions (account_id, type, amount, date) VALUES (?,?,?,?)",
        (account_id, 'Deposit', amount, datetime.now().strftime('%Y-%m-%d %H:%M'))
    )
    conn.commit()
    conn.close()
    post_double_entry("Cash/Bank", "Savings Payable (Members)", amount, f"Savings deposit — account #{account_id}")
    return new_balance

def withdraw(account_id, amount):
    conn = get_db_connection()
    account = conn.execute("SELECT * FROM savings_accounts WHERE id = ?", (account_id,)).fetchone()
    if amount > account['balance']:
        conn.close()
        return None, "Insufficient savings balance."
    new_balance = account['balance'] - amount
    conn.execute("UPDATE savings_accounts SET balance = ? WHERE id = ?", (new_balance, account_id))
    conn.execute(
        "INSERT INTO savings_transactions (account_id, type, amount, date) VALUES (?,?,?,?)",
        (account_id, 'Withdrawal', amount, datetime.now().strftime('%Y-%m-%d %H:%M'))
    )
    conn.commit()
    conn.close()
    post_double_entry("Savings Payable (Members)", "Cash/Bank", amount, f"Savings withdrawal — account #{account_id}")
    return new_balance, None

def render():
    customers = get_customers()
    members = [c for c in customers if c['member_type'] == 'Member']
    st.write("#### Open / Manage Savings Accounts")
    st.caption("Only SACCO members can hold savings accounts. Outsiders are loan-only clients.")
    if not members:
        st.warning("No members yet. Add a customer and mark them as a 'Member' in the Customers tab to open a savings account.")
        return

    customer_map = {f"{c['name']} ({c['phone']})": c['id'] for c in members}
    accounts = get_accounts()
    account_customer_ids = {a['customer_id'] for a in accounts}

    with st.form("open_account_form", clear_on_submit=True):
        choice = st.selectbox("Customer", list(customer_map.keys()))
        submitted = st.form_submit_button("Open Savings Account")
        if submitted:
            cid = customer_map[choice]
            if cid in account_customer_ids:
                st.warning("This customer already has a savings account.")
            else:
                open_account(cid)
                st.success(f"Savings account opened for {choice}.")

    accounts = get_accounts()
    if not accounts:
        st.info("No savings accounts yet.")
        return

    st.write("#### Deposit / Withdraw")
    account_map = {f"#{a['id']} — {a['customer_name']} (Bal: {a['balance']:,.0f})": a['id'] for a in accounts}
    with st.form("txn_form", clear_on_submit=True):
        acc_choice = st.selectbox("Account", list(account_map.keys()))
        txn_type = st.radio("Transaction", ["Deposit", "Withdraw"], horizontal=True)
        amount = st.number_input("Amount (UGX)", min_value=0.0, step=1000.0)
        submitted = st.form_submit_button("Process")
        if submitted:
            account_id = account_map[acc_choice]
            if amount <= 0:
                st.error("Amount must be greater than zero.")
            elif txn_type == "Deposit":
                new_balance = deposit(account_id, amount)
                st.success(f"Deposited UGX {amount:,.0f}. New balance: UGX {new_balance:,.0f}")
            else:
                new_balance, error = withdraw(account_id, amount)
                if error:
                    st.error(error)
                else:
                    st.success(f"Withdrew UGX {amount:,.0f}. New balance: UGX {new_balance:,.0f}")

    st.write("#### All Savings Accounts")
    st.dataframe(
        [{"Account ID": a['id'], "Customer": a['customer_name'], "Balance": a['balance'], "Opened": a['opened_date']} for a in accounts],
        use_container_width=True
    )

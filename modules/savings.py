import streamlit as st
from datetime import datetime
from database import get_db_connection
from modules.accounting import post_double_entry
from modules.customers import get_customers
from modules.theme import money_column

PAYMENT_CHANNELS = ["Cash", "MTN MoMo", "Airtel Money", "Bank Transfer"]

def open_account(customer_id, sacco_id):
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM savings_accounts WHERE customer_id = ?", (customer_id,)).fetchone()
    if existing:
        conn.close()
        return existing['id']
    cursor = conn.execute(
        "INSERT INTO savings_accounts (customer_id, balance, opened_date, sacco_id) VALUES (?,0,?,?)",
        (customer_id, datetime.now().strftime('%Y-%m-%d'), sacco_id)
    )
    account_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return account_id

def get_accounts(sacco_id):
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT savings_accounts.*, customers.name as customer_name FROM savings_accounts
           JOIN customers ON savings_accounts.customer_id = customers.id
           WHERE savings_accounts.sacco_id = ? ORDER BY savings_accounts.id DESC""",
        (sacco_id,)
    ).fetchall()
    conn.close()
    return rows

def get_transactions(sacco_id, limit=20):
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT savings_transactions.*, customers.name as customer_name FROM savings_transactions
           JOIN savings_accounts ON savings_transactions.account_id = savings_accounts.id
           JOIN customers ON savings_accounts.customer_id = customers.id
           WHERE savings_accounts.sacco_id = ?
           ORDER BY savings_transactions.id DESC LIMIT ?""",
        (sacco_id, limit)
    ).fetchall()
    conn.close()
    return rows

def deposit(account_id, amount, sacco_id, channel="Cash"):
    conn = get_db_connection()
    account = conn.execute("SELECT * FROM savings_accounts WHERE id = ?", (account_id,)).fetchone()
    new_balance = account['balance'] + amount
    conn.execute("UPDATE savings_accounts SET balance = ? WHERE id = ?", (new_balance, account_id))
    conn.execute(
        "INSERT INTO savings_transactions (account_id, type, amount, date, channel) VALUES (?,?,?,?,?)",
        (account_id, 'Deposit', amount, datetime.now().strftime('%Y-%m-%d %H:%M'), channel)
    )
    conn.commit()
    conn.close()
    post_double_entry("Cash/Bank", "Savings Payable (Members)", amount, f"Savings deposit — account #{account_id} via {channel}", sacco_id=sacco_id)
    return new_balance

def withdraw(account_id, amount, sacco_id, channel="Cash"):
    conn = get_db_connection()
    account = conn.execute("SELECT * FROM savings_accounts WHERE id = ?", (account_id,)).fetchone()
    if amount > account['balance']:
        conn.close()
        return None, "Insufficient savings balance."
    new_balance = account['balance'] - amount
    conn.execute("UPDATE savings_accounts SET balance = ? WHERE id = ?", (new_balance, account_id))
    conn.execute(
        "INSERT INTO savings_transactions (account_id, type, amount, date, channel) VALUES (?,?,?,?,?)",
        (account_id, 'Withdrawal', amount, datetime.now().strftime('%Y-%m-%d %H:%M'), channel)
    )
    conn.commit()
    conn.close()
    post_double_entry("Savings Payable (Members)", "Cash/Bank", amount, f"Savings withdrawal — account #{account_id} via {channel}", sacco_id=sacco_id)
    return new_balance, None

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected. Set up a SACCO Profile first.")
        return

    customers = get_customers(sacco_id)
    members = [c for c in customers if c['member_type'] == 'Member']
    st.write("#### Open / Manage Savings Accounts")
    st.caption("Only SACCO members can hold savings accounts. Outsiders are loan-only clients.")
    if not members:
        st.warning("No members yet. Add a customer and mark them as a 'Member' in the Customers tab to open a savings account.")
        return

    customer_map = {f"{c['name']} ({c['phone']})": c['id'] for c in members}
    accounts = get_accounts(sacco_id)
    account_customer_ids = {a['customer_id'] for a in accounts}

    with st.form("open_account_form", clear_on_submit=True):
        choice = st.selectbox("Customer", list(customer_map.keys()))
        submitted = st.form_submit_button("Open Savings Account")
        if submitted:
            cid = customer_map[choice]
            if cid in account_customer_ids:
                st.warning("This customer already has a savings account.")
            else:
                open_account(cid, sacco_id)
                st.success(f"Savings account opened for {choice}.")

    accounts = get_accounts(sacco_id)
    if not accounts:
        st.info("No savings accounts yet.")
        return

    st.write("#### Deposit / Withdraw")
    account_map = {f"#{a['id']} — {a['customer_name']} (Bal: {a['balance']:,.0f})": a['id'] for a in accounts}
    with st.form("txn_form", clear_on_submit=True):
        acc_choice = st.selectbox("Account", list(account_map.keys()))
        txn_type = st.radio("Transaction", ["Deposit", "Withdraw"], horizontal=True)
        amount = st.number_input("Amount (UGX)", min_value=0.0, step=1000.0)
        channel = st.selectbox("Mode of Payment (Channel)", PAYMENT_CHANNELS)
        submitted = st.form_submit_button("Process")
        if submitted:
            account_id = account_map[acc_choice]
            if amount <= 0:
                st.error("Amount must be greater than zero.")
            elif txn_type == "Deposit":
                new_balance = deposit(account_id, amount, sacco_id, channel)
                st.success(f"Deposited UGX {amount:,.0f} via {channel}. New balance: UGX {new_balance:,.0f}")
            else:
                new_balance, error = withdraw(account_id, amount, sacco_id, channel)
                if error:
                    st.error(error)
                else:
                    st.success(f"Withdrew UGX {amount:,.0f} via {channel}. New balance: UGX {new_balance:,.0f}")

    st.write("#### All Savings Accounts")
    st.dataframe(
        [{"Account ID": a['id'], "Customer": a['customer_name'], "Balance": a['balance'], "Opened": a['opened_date']} for a in accounts],
        column_config={"Balance": money_column()},
        use_container_width=True
    )

    st.write("#### Recent Savings Transactions")
    transactions = get_transactions(sacco_id, limit=20)
    if transactions:
        st.dataframe(
            [{"Date": t['date'], "Customer": t['customer_name'], "Type": t['type'],
              "Amount": t['amount'], "Channel": t['channel'] or '—'} for t in transactions],
            column_config={"Amount": money_column()},
            use_container_width=True
        )
    else:
        st.info("No savings transactions recorded yet.")

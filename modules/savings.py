import streamlit as st
from datetime import datetime
from database import get_db_connection
from modules.accounting import post_double_entry
from modules.customers import get_customers, get_customer
from modules.theme import money_column
from modules.nssf_engine import record_nssf_contribution

PAYMENT_CHANNELS = ["Cash", "MTN MoMo", "Airtel Money", "Bank Transfer"]

def open_account(customer_id, sacco_id):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM savings_accounts WHERE customer_id = %s", (customer_id,))
    existing = cur.fetchone()
    if existing:
        cur.close()
        conn.close()
        return existing['id']
    cur.execute(
        "INSERT INTO savings_accounts (customer_id, balance, opened_date, sacco_id) VALUES (%s,0,%s,%s) RETURNING id",
        (customer_id, datetime.now().strftime('%Y-%m-%d'), sacco_id)
    )
    account_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()
    return account_id

def get_accounts(sacco_id):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT savings_accounts.*, customers.name AS customer_name
        FROM savings_accounts
        JOIN customers ON savings_accounts.customer_id = customers.id
        WHERE savings_accounts.sacco_id = %s
        ORDER BY savings_accounts.id DESC
    """, (sacco_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_transactions(sacco_id, limit=20):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT savings_transactions.*, customers.name AS customer_name
        FROM savings_transactions
        JOIN savings_accounts ON savings_transactions.account_id = savings_accounts.id
        JOIN customers ON savings_accounts.customer_id = customers.id
        WHERE savings_accounts.sacco_id = %s
        ORDER BY savings_transactions.id DESC LIMIT %s
    """, (sacco_id, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def deposit(account_id, amount, sacco_id, channel="Cash"):
    conn     = get_db_connection()
    cur      = conn.cursor()
    cur.execute("SELECT * FROM savings_accounts WHERE id = %s", (account_id,))
    account  = cur.fetchone()
    cur.execute("SELECT * FROM customers WHERE id = %s", (account['customer_id'],))
    customer = cur.fetchone()

    nssf_amount  = 0.0
    net_to_sacco = amount
    rate         = 0.0

    if customer['nssf_registered'] == 1:
        rate         = customer['nssf_contribution_rate'] or 5.0
        nssf_amount  = round(amount * (rate / 100), 2)
        net_to_sacco = round(amount - nssf_amount, 2)

    new_balance = account['balance'] + net_to_sacco
    cur.execute("UPDATE savings_accounts SET balance = %s WHERE id = %s", (new_balance, account_id))
    cur.execute(
        "INSERT INTO savings_transactions (account_id, type, amount, date, channel) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (account_id, 'Deposit', net_to_sacco, datetime.now().strftime('%Y-%m-%d %H:%M'), channel)
    )
    txn_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()

    post_double_entry(
        "Cash/Bank", "Savings Payable (Members)", amount,
        f"Savings deposit — account #{account_id} via {channel}", sacco_id=sacco_id
    )
    if customer['nssf_registered'] == 1 and nssf_amount > 0:
        record_nssf_contribution(
            customer_id=customer['id'], sacco_id=sacco_id,
            gross_deposit=amount, rate=rate, savings_transaction_id=txn_id
        )
    return new_balance, nssf_amount, net_to_sacco

def withdraw(account_id, amount, sacco_id, channel="Cash"):
    conn    = get_db_connection()
    cur     = conn.cursor()
    cur.execute("SELECT * FROM savings_accounts WHERE id = %s", (account_id,))
    account = cur.fetchone()
    if amount > account['balance']:
        cur.close()
        conn.close()
        return None, "Insufficient savings balance."
    new_balance = account['balance'] - amount
    cur.execute("UPDATE savings_accounts SET balance = %s WHERE id = %s", (new_balance, account_id))
    cur.execute(
        "INSERT INTO savings_transactions (account_id, type, amount, date, channel) VALUES (%s,%s,%s,%s,%s)",
        (account_id, 'Withdrawal', amount, datetime.now().strftime('%Y-%m-%d %H:%M'), channel)
    )
    conn.commit()
    cur.close()
    conn.close()
    post_double_entry(
        "Savings Payable (Members)", "Cash/Bank", amount,
        f"Savings withdrawal — account #{account_id} via {channel}", sacco_id=sacco_id
    )
    return new_balance, None

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected. Set up a SACCO Profile first.")
        return

    customers = get_customers(sacco_id)
    members   = [c for c in customers if c['member_type'] == 'Member']
    st.write("#### Open / Manage Savings Accounts")
    if not members:
        st.warning("No members yet. Add a customer marked as 'Member' to open a savings account.")
        return

    customer_map = {f"{c['name']} ({c['phone']})": c['id'] for c in members}
    accounts     = get_accounts(sacco_id)
    account_cids = {a['customer_id'] for a in accounts}

    with st.form("open_account_form", clear_on_submit=True):
        choice    = st.selectbox("Customer", list(customer_map.keys()))
        submitted = st.form_submit_button("Open Savings Account")
        if submitted:
            cid = customer_map[choice]
            if cid in account_cids:
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
        txn_type   = st.radio("Transaction", ["Deposit","Withdraw"], horizontal=True)
        amount     = st.number_input("Amount (UGX)", min_value=0.0, step=1000.0)
        channel    = st.selectbox("Mode of Payment", PAYMENT_CHANNELS)
        submitted  = st.form_submit_button("Process")
        if submitted:
            account_id = account_map[acc_choice]
            if amount <= 0:
                st.error("Amount must be greater than zero.")
            elif txn_type == "Deposit":
                new_balance, nssf_amount, net_to_sacco = deposit(account_id, amount, sacco_id, channel)
                if nssf_amount > 0:
                    st.success(f"✅ Deposit of UGX {amount:,.0f} processed via {channel}.")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Gross Deposit",         f"UGX {amount:,.0f}")
                    c2.metric("🇺🇬 NSSF Contribution", f"UGX {nssf_amount:,.0f}")
                    c3.metric("Net to SACCO Savings",  f"UGX {net_to_sacco:,.0f}")
                    st.caption("🏅 Gold Points awarded for this NSSF contribution!")
                else:
                    st.success(f"✅ Deposited UGX {amount:,.0f} via {channel}. New balance: UGX {new_balance:,.0f}")
                    st.caption("⚠️ No NSSF contribution — member not yet NSSF registered.")
            else:
                new_balance, error = withdraw(account_id, amount, sacco_id, channel)
                if error:
                    st.error(error)
                else:
                    st.success(f"Withdrew UGX {amount:,.0f} via {channel}. New balance: UGX {new_balance:,.0f}")

    st.write("#### All Savings Accounts")
    st.dataframe(
        [{"Account ID": a['id'], "Customer": a['customer_name'],
          "Balance": a['balance'], "Opened": a['opened_date']} for a in accounts],
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

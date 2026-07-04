import streamlit as st
from database import get_db_connection
from auth import hash_password
from modules.customers import get_customers
from modules.sacco_profile import get_all_saccos
from modules.theme import money_column

def add_user(username, password, role='staff', sacco_id=None):
    salt, pw_hash = hash_password(password)
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        conn.close()
        return False
    conn.execute(
        "INSERT INTO users (username, password_hash, salt, role, sacco_id) VALUES (?, ?, ?, ?, ?)",
        (username, pw_hash, salt, role, sacco_id)
    )
    conn.commit()
    conn.close()
    return True

def get_users():
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT users.username, users.role, users.sacco_id, sacco_profile.sacco_name FROM users
           LEFT JOIN sacco_profile ON users.sacco_id = sacco_profile.id"""
    ).fetchall()
    conn.close()
    return rows

def get_customer_profile(customer_id):
    conn = get_db_connection()
    customer = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
    loans = conn.execute("SELECT * FROM loans WHERE customer_id=?", (customer_id,)).fetchall()
    savings = conn.execute("SELECT * FROM savings_accounts WHERE customer_id=?", (customer_id,)).fetchone()
    guarantors_given = conn.execute(
        """SELECT guarantors.*, loans.id as loan_ref FROM guarantors JOIN loans ON guarantors.loan_id = loans.id WHERE loans.customer_id = ?""",
        (customer_id,)
    ).fetchall()
    collateral_held = conn.execute(
        """SELECT collateral.*, loans.id as loan_ref FROM collateral JOIN loans ON collateral.loan_id = loans.id WHERE loans.customer_id = ?""",
        (customer_id,)
    ).fetchall()
    conn.close()
    return customer, loans, savings, guarantors_given, collateral_held

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    role = st.session_state.get('user_role')

    if role == 'admin':
        st.write("#### 👥 Manage Staff & Admin Users")
        saccos = get_all_saccos()
        sacco_map = {(s['sacco_name'] or f"SACCO #{s['id']}"): s['id'] for s in saccos}
        with st.form("add_user_form", clear_on_submit=True):
            new_username = st.text_input("New username")
            new_password = st.text_input("New password", type="password")
            new_role = st.selectbox("Role", ["staff", "admin"])
            assigned_sacco = None
            if new_role == "staff":
                if sacco_map:
                    sacco_choice = st.selectbox("Assign to SACCO", list(sacco_map.keys()))
                    assigned_sacco = sacco_map[sacco_choice]
                else:
                    st.warning("Create a SACCO first (SACCO Profile page) before adding staff users.")
            submitted = st.form_submit_button("Create User")
            if submitted:
                if new_username and new_password:
                    if new_role == "staff" and assigned_sacco is None:
                        st.error("Staff accounts must be assigned to a SACCO.")
                    else:
                        created = add_user(new_username, new_password, new_role, assigned_sacco)
                        if created:
                            st.success(f"User '{new_username}' created with role '{new_role}'.")
                        else:
                            st.error("That username already exists.")
                else:
                    st.error("Username and password are required.")

        users = get_users()
        if users:
            st.dataframe(
                [{"Username": u['username'], "Role": u['role'],
                  "SACCO": u['sacco_name'] or ("All (super-admin)" if u['role'] == 'admin' else '—')} for u in users],
                use_container_width=True
            )
        st.write("---")

    st.write("#### 🔍 Customer 360 View")
    if sacco_id is None:
        st.warning("No SACCO selected. Set up a SACCO Profile first.")
        return

    customers = get_customers(sacco_id)
    if not customers:
        st.info("No customers yet for this SACCO.")
        return

    customer_map = {f"{c['name']} ({c['phone']})": c['id'] for c in customers}
    choice = st.selectbox("Select customer", list(customer_map.keys()))
    customer, loans, savings, guarantors_given, collateral_held = get_customer_profile(customer_map[choice])

    profile_col1, profile_col2 = st.columns([1, 4])
    with profile_col1:
        if customer['photo']:
            st.image(customer['photo'], width=100)
    with profile_col2:
        st.write(f"**{customer['name']}** — {customer['member_type']} | {customer['occupation'] or 'No occupation set'}")
        st.write(f"📞 {customer['phone']} | 🆔 {customer['national_id'] or 'N/A'} | 📍 {customer['village'] or '—'}, {customer['parish'] or '—'} | Joined {customer['created_at']}")
        st.write(f"Gender: {customer['gender'] or '—'} | PWD: {customer['pwd_status'] or 'No'} | Subsistence economy: {customer['subsistence_status'] or '—'}")

    if savings:
        st.write(f"💰 **Savings Balance:** UGX {savings['balance']:,.0f}")
    else:
        st.write("💰 No savings account (Outsider, or member who hasn't opened one yet)")

    if loans:
        st.write("**Loan History:**")
        st.dataframe(
            [{"Loan ID": l['id'], "Principal": l['principal'], "Balance": l['balance'], "Status": l['status'],
              "Disbursed": l['disbursed_date']} for l in loans],
            column_config={"Principal": money_column(), "Balance": money_column()},
            use_container_width=True
        )
    else:
        st.info("No loans on record for this customer.")

    if guarantors_given:
        st.write("**Guarantors Backing This Customer's Loans:**")
        st.dataframe(
            [{"Loan ID": g['loan_ref'], "Guarantor": g['name'], "Phone": g['phone']} for g in guarantors_given],
            use_container_width=True
        )

    if collateral_held:
        st.write("**Collateral Held Against This Customer's Loans:**")
        st.dataframe(
            [{"Loan ID": c['loan_ref'], "Description": c['description'],
              "Estimated Value": c['estimated_value'], "Status": c['status']} for c in collateral_held],
            column_config={"Estimated Value": money_column()},
            use_container_width=True
        )
    else:
        st.caption("No collateral on record for this customer.")

import streamlit as st
from database import get_db_connection
from auth import (hash_password, create_user, delete_user, get_all_users,
                  ROLE_SUPER_ADMIN, ROLE_SACCO_ADMIN, ROLE_STAFF)
from modules.customers import get_customers
from modules.sacco_profile import get_all_saccos
from modules.theme import money_column

ROLE_LABELS = {
    ROLE_SUPER_ADMIN: "🔴 Super Admin",
    ROLE_SACCO_ADMIN: "🟡 SACCO Admin",
    ROLE_STAFF:       "🟢 Staff",
}
ROLE_DESCRIPTIONS = {
    ROLE_SUPER_ADMIN: "Full platform access. Sees all SACCOs. Can manage all users.",
    ROLE_SACCO_ADMIN: "Manages their own SACCO only. Sees NSSF Compliance and Reports. Cannot create SACCO Admins.",
    ROLE_STAFF:       "Data entry for their own SACCO only. No admin or compliance pages.",
}

def get_customer_profile(customer_id):
    conn     = get_db_connection()
    cur      = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id=%s", (customer_id,))
    customer = cur.fetchone()
    cur.execute("SELECT * FROM loans WHERE customer_id=%s", (customer_id,))
    loans    = cur.fetchall()
    cur.execute("SELECT * FROM savings_accounts WHERE customer_id=%s", (customer_id,))
    savings  = cur.fetchone()
    cur.execute("""
        SELECT guarantors.*, loans.id AS loan_ref FROM guarantors
        JOIN loans ON guarantors.loan_id = loans.id WHERE loans.customer_id = %s
    """, (customer_id,))
    guarantors_given = cur.fetchall()
    cur.execute("""
        SELECT collateral.*, loans.id AS loan_ref FROM collateral
        JOIN loans ON collateral.loan_id = loans.id WHERE loans.customer_id = %s
    """, (customer_id,))
    collateral_held = cur.fetchall()
    cur.close()
    conn.close()
    return customer, loans, savings, guarantors_given, collateral_held

def _render_user_management(caller_role, caller_sacco_id):
    st.write("#### 👥 User Management")
    saccos    = get_all_saccos()
    sacco_map = {(s['sacco_name'] or f"SACCO #{s['id']}"): s['id'] for s in saccos}

    if caller_role == ROLE_SUPER_ADMIN:
        available_roles = [ROLE_STAFF, ROLE_SACCO_ADMIN, ROLE_SUPER_ADMIN]
        role_labels     = [ROLE_LABELS[r] for r in available_roles]
    else:
        available_roles = [ROLE_STAFF]
        role_labels     = [ROLE_LABELS[ROLE_STAFF]]

    with st.form("add_user_form", clear_on_submit=True):
        st.caption("Create a new user account.")
        new_username  = st.text_input("Username")
        new_password  = st.text_input("Password", type="password")
        role_choice   = st.selectbox("Role", role_labels)
        selected_role = available_roles[role_labels.index(role_choice)]
        st.caption(ROLE_DESCRIPTIONS[selected_role])

        assigned_sacco = None
        if selected_role == ROLE_SUPER_ADMIN:
            st.info("Super Admin accounts are not scoped to a SACCO — they see everything.")
        elif caller_role == ROLE_SACCO_ADMIN:
            assigned_sacco = caller_sacco_id
            assigned_name  = next((name for name, sid in sacco_map.items() if sid == caller_sacco_id), f"SACCO #{caller_sacco_id}")
            st.info(f"User will be assigned to: **{assigned_name}**")
        else:
            if sacco_map:
                sacco_choice   = st.selectbox("Assign to SACCO", list(sacco_map.keys()))
                assigned_sacco = sacco_map[sacco_choice]
            else:
                st.warning("Create a SACCO first before adding scoped users.")

        submitted = st.form_submit_button("Create User")
        if submitted:
            if not new_username or not new_password:
                st.error("Username and password are required.")
            elif selected_role != ROLE_SUPER_ADMIN and assigned_sacco is None:
                st.error("This role must be assigned to a SACCO.")
            else:
                ok = create_user(new_username, new_password, selected_role, assigned_sacco)
                if ok:
                    st.success(f"✅ User **{new_username}** created as {ROLE_LABELS[selected_role]}.")
                else:
                    st.error("That username already exists.")

    st.write("#### Current Users")
    users = get_all_users()
    if caller_role == ROLE_SACCO_ADMIN:
        users = [u for u in users if u['sacco_id'] == caller_sacco_id or u['username'] == st.session_state.get('user')]

    if users:
        st.dataframe(
            [{"Username": u['username'], "Role": ROLE_LABELS.get(u['role'], u['role']),
              "Scope": "All SACCOs" if u['role'] == ROLE_SUPER_ADMIN else (u['sacco_name'] or f"SACCO #{u['sacco_id']}" if u['sacco_id'] else "—")}
             for u in users],
            use_container_width=True, hide_index=True
        )
        if caller_role == ROLE_SUPER_ADMIN:
            st.write("#### ❌ Delete User")
            deletable = [u['username'] for u in users if u['username'] != 'timo']
            if deletable:
                to_delete = st.selectbox("Select user to delete", deletable)
                if st.button(f"Delete '{to_delete}'", type="secondary"):
                    ok = delete_user(to_delete)
                    if ok:
                        st.success(f"User '{to_delete}' deleted.")
                        st.rerun()
    else:
        st.info("No users found.")

def render():
    sacco_id   = st.session_state.get('current_sacco_id')
    role       = st.session_state.get('user_role')
    user_sacco = st.session_state.get('user_sacco_id')

    if role in (ROLE_SUPER_ADMIN, ROLE_SACCO_ADMIN):
        _render_user_management(role, user_sacco)
        st.divider()

    st.write("#### 🔍 Customer 360 View")
    if sacco_id is None:
        st.warning("No SACCO selected.")
        return

    customers = get_customers(sacco_id)
    if not customers:
        st.info("No customers yet for this SACCO.")
        return

    customer_map = {f"{c['name']} ({c['phone']})": c['id'] for c in customers}
    choice       = st.selectbox("Select customer", list(customer_map.keys()))
    customer, loans, savings, guarantors_given, collateral_held = get_customer_profile(customer_map[choice])

    profile_col1, profile_col2 = st.columns([1,4])
    with profile_col1:
        if customer['photo']:
            st.image(bytes(customer['photo']), width=100)
        else:
            st.caption("No photo")
    with profile_col2:
        st.write(f"**{customer['name']}** — {customer['member_type']} | {customer['occupation'] or 'No occupation set'}")
        st.write(f"📞 {customer['phone']} | 🆔 {customer['national_id'] or 'N/A'} | 📍 {customer['village'] or '—'}, {customer['parish'] or '—'} | Joined {customer['created_at']}")
        st.write(f"Gender: {customer['gender'] or '—'} | PWD: {customer['pwd_status'] or 'No'} | Subsistence: {customer['subsistence_status'] or '—'}")
        if customer['nssf_registered']:
            st.success(f"🇺🇬 NSSF Registered — {customer['nssf_number'] or 'Number not captured'}")
        else:
            st.warning("⚠️ Not NSSF Registered")

    if savings:
        st.write(f"💰 **Savings Balance:** UGX {savings['balance']:,.0f}")
    else:
        st.write("💰 No savings account")

    if loans:
        st.write("**Loan History:**")
        st.dataframe(
            [{"Loan ID": l['id'], "Principal": l['principal'], "Balance": l['balance'],
              "Status": l['status'], "Disbursed": l['disbursed_date']} for l in loans],
            column_config={"Principal": money_column(), "Balance": money_column()},
            use_container_width=True
        )
    else:
        st.info("No loans on record.")

    if guarantors_given:
        st.write("**Guarantors:**")
        st.dataframe([{"Loan ID": g['loan_ref'], "Guarantor": g['name'], "Phone": g['phone']} for g in guarantors_given], use_container_width=True)

    if collateral_held:
        st.write("**Collateral:**")
        st.dataframe(
            [{"Loan ID": c['loan_ref'], "Description": c['description'],
              "Estimated Value": c['estimated_value'], "Status": c['status']} for c in collateral_held],
            column_config={"Estimated Value": money_column()},
            use_container_width=True
        )

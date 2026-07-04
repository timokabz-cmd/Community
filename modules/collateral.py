import streamlit as st
from database import get_db_connection
from modules.loans import get_loans
from modules.theme import money_column

def add_collateral(loan_id, description, estimated_value):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO collateral (loan_id, description, estimated_value, status) VALUES (?,?,?,?)",
        (loan_id, description, estimated_value, 'Held')
    )
    conn.commit()
    conn.close()

def get_collateral(loan_id=None, sacco_id=None):
    conn = get_db_connection()
    if loan_id:
        rows = conn.execute("SELECT * FROM collateral WHERE loan_id = ?", (loan_id,)).fetchall()
    else:
        rows = conn.execute(
            """SELECT collateral.*, loans.id as loan_ref, customers.name as borrower_name FROM collateral
               JOIN loans ON collateral.loan_id = loans.id JOIN customers ON loans.customer_id = customers.id
               WHERE loans.sacco_id = ? ORDER BY collateral.id DESC""",
            (sacco_id,)
        ).fetchall()
    conn.close()
    return rows

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected. Set up a SACCO Profile first.")
        return

    loans = get_loans(sacco_id)
    st.write("#### Register Collateral for a Loan")
    if not loans:
        st.warning("Issue a loan first before registering collateral.")
    else:
        loan_map = {f"Loan #{l['id']} — {l['customer_name']}": l['id'] for l in loans}
        with st.form("add_collateral_form", clear_on_submit=True):
            loan_choice = st.selectbox("Loan", list(loan_map.keys()))
            description = st.text_input("Description (e.g. 'Land title, Plot 12, Mukono')")
            estimated_value = st.number_input("Estimated value (UGX)", min_value=0.0, step=10000.0)
            submitted = st.form_submit_button("Register Collateral")
            if submitted:
                if description:
                    add_collateral(loan_map[loan_choice], description, estimated_value)
                    st.success(f"Collateral registered against {loan_choice}.")
                else:
                    st.error("A description is required.")

    st.write("#### All Registered Collateral")
    items = get_collateral(sacco_id=sacco_id)
    if items:
        st.dataframe(
            [{"Loan": f"#{c['loan_ref']}", "Borrower": c['borrower_name'], "Description": c['description'],
              "Estimated Value": c['estimated_value'], "Status": c['status']} for c in items],
            column_config={"Estimated Value": money_column()},
            use_container_width=True
        )
    else:
        st.info("No collateral registered yet.")

import streamlit as st
from database import get_db_connection
from modules.loans import get_loans

def add_guarantor(loan_id, name, phone, national_id, relationship):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO guarantors (loan_id, name, phone, national_id, relationship) VALUES (?,?,?,?,?)",
        (loan_id, name, phone, national_id, relationship)
    )
    conn.commit()
    conn.close()

def get_guarantors(loan_id=None):
    conn = get_db_connection()
    if loan_id:
        rows = conn.execute("SELECT * FROM guarantors WHERE loan_id = ?", (loan_id,)).fetchall()
    else:
        rows = conn.execute(
            """SELECT guarantors.*, loans.id as loan_ref, customers.name as borrower_name FROM guarantors JOIN loans ON guarantors.loan_id = loans.id JOIN customers ON loans.customer_id = customers.id ORDER BY guarantors.id DESC"""
        ).fetchall()
    conn.close()
    return rows

def render():
    loans = get_loans()
    st.write("#### Attach a Guarantor to a Loan")
    if not loans:
        st.warning("Issue a loan first before adding guarantors.")
    else:
        loan_map = {f"Loan #{l['id']} — {l['customer_name']}": l['id'] for l in loans}
        with st.form("add_guarantor_form", clear_on_submit=True):
            loan_choice = st.selectbox("Loan", list(loan_map.keys()))
            name = st.text_input("Guarantor full name")
            phone = st.text_input("Guarantor phone number")
            national_id = st.text_input("Guarantor National ID")
            relationship = st.text_input("Relationship to borrower")
            submitted = st.form_submit_button("Add Guarantor")
            if submitted:
                if name and phone:
                    add_guarantor(loan_map[loan_choice], name, phone, national_id, relationship)
                    st.success(f"Guarantor '{name}' added to {loan_choice}.")
                else:
                    st.error("Guarantor name and phone are required.")

    st.write("#### All Guarantors")
    guarantors = get_guarantors()
    if guarantors:
        st.dataframe(
            [{"Loan": f"#{g['loan_ref']}", "Borrower": g['borrower_name'], "Guarantor": g['name'],
              "Phone": g['phone'], "National ID": g['national_id'], "Relationship": g['relationship']} for g in guarantors],
            use_container_width=True
        )
    else:
        st.info("No guarantors recorded yet.")

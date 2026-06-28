import streamlit as st
from database import get_db_connection

def render_collections():
    st.subheader("📥 Daily Collections")
    conn = get_db_connection()
    members = conn.execute("SELECT id, name FROM members").fetchall()
    conn.close()
    
    member_options = {m['name']: m['id'] for m in members}
    selected_name = st.selectbox("Select Member", list(member_options.keys()))
    amount = st.number_input("Amount Collected", min_value=100)
    
    if st.button("Record Collection"):
        conn = get_db_connection()
        # Logging into the ledger we designed earlier
        conn.execute("INSERT INTO ledger (amount, narration, operator_name) VALUES (?, ?, ?)",
                     (amount, f"Collection from {selected_name}", "Admin"))
        conn.commit()
        conn.close()
        st.success("Transaction recorded.")

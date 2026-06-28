import streamlit as st
import pandas as pd
from database import get_db_connection

def render_accounting():
    st.subheader("📊 Transaction Ledger")
    
    conn = get_db_connection()
    # Fetch all records from the ledger table
    query = "SELECT timestamp, amount, narration, operator_name FROM ledger ORDER BY timestamp DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if not df.empty:
        # Display as a dataframe with professional styling
        st.dataframe(df, use_container_width=True)
        
        # Add a summary total for quick verification
        total_balance = df['amount'].sum()
        st.metric("Total Ledger Volume", f"UGX {total_balance:,.0f}")
    else:
        st.info("No transactions recorded yet.")

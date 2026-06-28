import streamlit as st
import pandas as pd
import io
from database import get_db_connection

def render_reporting():
    st.subheader("📄 Export Financial Reports")
    
    conn = get_db_connection()
    # Fetching ledger data
    df = pd.read_sql_query("SELECT * FROM ledger ORDER BY timestamp DESC", conn)
    conn.close()
    
    if not df.empty:
        # Create an Excel buffer
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Ledger', index=False)
        
        st.download_button(
            label="📥 Download Ledger as Excel",
            data=buffer.getvalue(),
            file_name="ledger_report.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.info("No data available to export.")

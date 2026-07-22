import streamlit as st
from database import get_db_connection
from modules.nssf_engine import get_nssf_summary
from modules.theme import money_column

GOLD = "#C99A3B"; INK = "#1A1A2E"; LINE = "#DDD5C4"; PAPER_DIM = "#F5F0E8"

def _stat_card_html(label, value, sub=None, accent=GOLD):
    return f"""
    <div style="background:{PAPER_DIM};border:1.5px solid {LINE};border-top:4px solid {accent};
                border-radius:8px;padding:1rem 1.1rem;height:100%;">
      <div style="font-size:0.75rem;color:#7C8A99;text-transform:uppercase;
                  letter-spacing:0.05em;font-weight:600;">{label}</div>
      <div style="font-size:1.6rem;font-weight:700;color:{INK};
                  font-variant-numeric:tabular-nums;margin-top:0.3rem;">{value}</div>
      {'<div style="font-size:0.8rem;color:#7C8A99;margin-top:0.2rem;">'+sub+'</div>' if sub else ''}
    </div>"""

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected.")
        return

    summary = get_nssf_summary(sacco_id)
    compliance_color = "#3F7A4D" if summary['compliance_pct'] >= 80 else "#A4732B" if summary['compliance_pct'] >= 50 else "#B0492E"

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(_stat_card_html("Total Members",    f"{summary['total_members']:,}", "in this SACCO"), unsafe_allow_html=True)
    with c2: st.markdown(_stat_card_html("NSSF Registered",  f"{summary['nssf_registered']:,}", f"{summary['compliance_pct']}% compliance", accent=compliance_color), unsafe_allow_html=True)
    with c3: st.markdown(_stat_card_html("Total Contributed", f"UGX {summary['total_contributed_ugx']:,.0f}", "all time"), unsafe_allow_html=True)
    with c4: st.markdown(_stat_card_html("Unremitted to NSSF", f"UGX {summary['unremitted_ugx']:,.0f}", "pending remittance", accent="#B0492E" if summary['unremitted_ugx'] > 0 else "#3F7A4D"), unsafe_allow_html=True)

    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    unregistered = summary['total_members'] - summary['nssf_registered']
    if unregistered > 0:
        st.warning(f"⚠️ **{unregistered} member(s) not yet NSSF registered.** Update their profiles once they complete registration at [nssfug.org](https://www.nssfug.org).")
    else:
        st.success("✅ All members in this SACCO are NSSF registered. Full compliance achieved.")

    st.divider()
    st.write("#### 📋 Contributions Ledger")

    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT nc.id, nc.period, c.name AS member_name, c.nssf_number,
               nc.gross_deposit, nc.nssf_amount, nc.net_to_sacco,
               nc.contribution_rate, nc.remitted, nc.created_at
        FROM nssf_contributions nc
        JOIN customers c ON nc.customer_id = c.id
        WHERE nc.sacco_id = %s
        ORDER BY nc.created_at DESC LIMIT 100
    """, (sacco_id,))
    contributions = cur.fetchall()

    if not contributions:
        st.info("No NSSF contributions recorded yet. They appear here automatically when NSSF-registered members make deposits.")
    else:
        st.dataframe(
            [{"Date": r['created_at'], "Period": r['period'], "Member": r['member_name'],
              "NSSF No.": r['nssf_number'] or "—", "Gross Deposit": r['gross_deposit'],
              "NSSF Amount": r['nssf_amount'], "Net to SACCO": r['net_to_sacco'],
              "Rate (%)": r['contribution_rate'],
              "Remitted": "✅ Yes" if r['remitted'] else "⏳ Pending"} for r in contributions],
            column_config={"Gross Deposit": money_column(), "NSSF Amount": money_column(), "Net to SACCO": money_column()},
            use_container_width=True, hide_index=True
        )

    st.divider()
    st.write("#### ✅ Mark Period as Remitted")
    cur.execute("""
        SELECT DISTINCT period FROM nssf_contributions
        WHERE sacco_id = %s AND remitted = 0 ORDER BY period DESC
    """, (sacco_id,))
    pending_periods = cur.fetchall()

    if not pending_periods:
        st.info("No pending periods — all contributions have been marked as remitted.")
    else:
        period_list     = [r['period'] for r in pending_periods]
        selected_period = st.selectbox("Select period to mark as remitted", period_list)
        cur.execute("""
            SELECT COALESCE(SUM(nssf_amount),0) AS total, COUNT(*) AS count
            FROM nssf_contributions
            WHERE sacco_id = %s AND period = %s AND remitted = 0
        """, (sacco_id, selected_period))
        period_total = cur.fetchone()
        st.info(f"Period **{selected_period}**: **{period_total['count']} contribution(s)** totalling **UGX {period_total['total']:,.0f}** pending remittance.")
        if st.button(f"✅ Mark {selected_period} as Remitted", type="primary"):
            cur.execute("""
                UPDATE nssf_contributions SET remitted = 1
                WHERE sacco_id = %s AND period = %s AND remitted = 0
            """, (sacco_id, selected_period))
            conn.commit()
            st.success(f"Period {selected_period} marked as remitted.")
            st.rerun()

    st.divider()
    st.write("#### ⚠️ Members Not Yet NSSF Registered")
    cur.execute("""
        SELECT name, phone, national_id, created_at FROM customers
        WHERE sacco_id = %s AND (nssf_registered = 0 OR nssf_registered IS NULL)
        ORDER BY name
    """, (sacco_id,))
    unregistered_members = cur.fetchall()
    cur.close()
    conn.close()

    if not unregistered_members:
        st.success("✅ No unregistered members — full compliance!")
    else:
        st.dataframe(
            [{"Name": m['name'], "Phone": m['phone'],
              "National ID": m['national_id'] or "—", "Enrolled": m['created_at'],
              "Action": "Register at nssfug.org"} for m in unregistered_members],
            use_container_width=True, hide_index=True
        )

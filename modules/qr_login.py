import streamlit as st
import qrcode
import io
from database import get_db_connection
from modules.sacco_profile import get_all_saccos

def generate_qr(url: str) -> bytes:
    qr  = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def render():
    st.write("#### 📱 SACCO Login QR Codes")
    st.caption(
        "Each QR code links directly to the login page pre-labelled with that SACCO's name. "
        "Print and display at each SACCO meeting point so members and staff can scan to access."
    )

    saccos = get_all_saccos()
    if not saccos:
        st.info("No SACCOs set up yet. Create a SACCO Profile first.")
        return

    # Admin app base URL
    try:
        base_url = st.secrets.get("ADMIN_APP_URL", "https://community-urirqlapshoc3mkqwhjbd3.streamlit.app")
    except Exception:
        base_url = "https://community-urirqlapshoc3mkqwhjbd3.streamlit.app"

    # Member app base URL
    try:
        member_url = st.secrets.get("MEMBER_APP_URL", "https://sacco-members.streamlit.app")
    except Exception:
        member_url = "https://sacco-members.streamlit.app"

    for sacco in saccos:
        sacco_id   = sacco['id']
        sacco_name = sacco['sacco_name'] or f"SACCO #{sacco_id}"

        st.write(f"**{sacco_name}**")
        col1, col2 = st.columns(2)

        with col1:
            st.caption("Staff / Admin Login")
            admin_link = f"{base_url}?sacco_id={sacco_id}"
            qr_bytes   = generate_qr(admin_link)
            st.image(qr_bytes, width=180)
            st.code(admin_link, language=None)

        with col2:
            st.caption("Member Self-Service Login")
            member_link = f"{member_url}?sacco_id={sacco_id}"
            qr_bytes    = generate_qr(member_link)
            st.image(qr_bytes, width=180)
            st.code(member_link, language=None)

        st.divider()

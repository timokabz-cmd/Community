"""
Per-SACCO login QR codes.

Generates a QR code that encodes a deep link like:
    https://your-app.streamlit.app/?sacco_id=3

Scanning it opens the app straight to the login screen, with a caption
confirming which SACCO you're logging into (see app.py's read of
st.query_params near the top of the login block).

IMPORTANT — this is a UX convenience, not a security boundary. The
sacco_id in the URL only controls what's *displayed* before login (a
"you're logging into: X" caption). It never grants access by itself —
a staff account's actual sacco_id in the users table is what the rest
of the app checks after authentication, exactly as before. Someone
editing the URL by hand cannot see another SACCO's data this way; they'd
still need real, valid login credentials scoped to that SACCO.

Streamlit apps can't reliably read their own public URL from Python code,
so the base URL is entered once below rather than auto-detected.
"""

import streamlit as st
import qrcode
from io import BytesIO
from modules.sacco_profile import get_all_saccos

def generate_qr_png(url):
    """Returns PNG image bytes for a QR code encoding the given URL."""
    qr = qrcode.QRCode(border=2, box_size=10)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def build_login_url(base_url, sacco_id):
    base_url = base_url.rstrip('/')
    return f"{base_url}/?sacco_id={sacco_id}"

def render():
    st.write("#### 📱 Login QR Codes")
    st.caption(
        "Generates a scannable QR code per SACCO that opens straight to the login screen, "
        "with a caption confirming which SACCO it is. This doesn't change who can log in or "
        "what they can see — that's still controlled by each staff account's own SACCO "
        "assignment, exactly as before. It just saves typing a URL on a phone."
    )

    saccos = get_all_saccos()
    if not saccos:
        st.info("No SACCOs yet — create one on the SACCO Profile page first.")
        return

    base_url = st.text_input(
        "Your app's live URL",
        value=st.session_state.get('qr_base_url', ''),
        placeholder="https://hjbd3.streamlit.app",
        help="Streamlit apps can't detect their own public URL automatically — paste it here once."
    )
    if base_url:
        st.session_state['qr_base_url'] = base_url

    if not base_url:
        st.warning("Enter your app's URL above to generate QR codes.")
        return

    sacco_map = {(s['sacco_name'] or f"SACCO #{s['id']}"): s['id'] for s in saccos}
    choice = st.selectbox("SACCO", list(sacco_map.keys()))
    sacco_id = sacco_map[choice]

    login_url = build_login_url(base_url, sacco_id)
    png_bytes = generate_qr_png(login_url)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(png_bytes, caption=choice, width=220)
    with col2:
        st.write(f"**Link:** {login_url}")
        st.caption("Print or share the QR code above, or copy the link directly.")
        st.download_button(
            "Download QR code (PNG)",
            data=png_bytes,
            file_name=f"{choice.replace(' ', '_')}_login_qr.png",
            mime="image/png"
        )

"""Simple password authentication for the Streamlit dashboard."""

import streamlit as st
from src.config import get_settings


def check_password() -> bool:
    """
    Display a password input and verify against the configured password.

    Returns True if authenticated, False otherwise.
    """
    settings = get_settings()

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.markdown(
        """
        <div style="display: flex; justify-content: center; align-items: center; 
                    min-height: 60vh; flex-direction: column;">
            <div style="width: 48px; height: 48px; background: #00152a; border-radius: 14px;
                        display: flex; align-items: center; justify-content: center; margin-bottom: 1rem;">
                <span style="font-size: 1.5rem;">🏢</span>
            </div>
            <h1 style="color: #00152a; margin-bottom: 0.2rem; font-family: 'Manrope', sans-serif;
                       font-weight: 900; letter-spacing: -0.03em; font-size: 1.8rem;">GarageLedger</h1>
            <p style="color: #43474d; margin-bottom: 2rem; font-size: 0.85rem;
                      font-family: 'Manrope', sans-serif; font-weight: 600;">
                Sreality.cz monitoring &amp; analytika</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password = st.text_input("Heslo", type="password", key="login_password")
        if st.button("Přihlásit se", use_container_width=True, type="primary"):
            if password == settings.app_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Nesprávné heslo")

    return False

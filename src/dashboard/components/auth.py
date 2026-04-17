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
            <h1 style="color: #6C63FF; margin-bottom: 0.5rem;">🏢 Realitní Tracker</h1>
            <p style="color: #888; margin-bottom: 2rem;">Sreality.cz monitoring & analytika</p>
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

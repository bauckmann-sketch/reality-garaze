"""Reusable filter/sidebar components for the dashboard."""

from __future__ import annotations

from typing import Optional

import streamlit as st
from sqlalchemy.orm import Session

from src.models import Filter


def filter_selector(session: Session) -> Optional[Filter]:
    """
    Render a filter selector in the sidebar.

    Returns the selected Filter object or None.
    """
    filters = session.query(Filter).filter_by(is_active=True).order_by(Filter.name).all()

    if not filters:
        st.sidebar.warning("Žádné aktivní filtry. Přidejte filtr v nastavení.")
        return None

    filter_options = {f.name: f for f in filters}
    selected_name = st.sidebar.selectbox(
        "📍 Filtr / Lokalita",
        options=list(filter_options.keys()),
        key="selected_filter",
    )

    selected = filter_options.get(selected_name)

    if selected:
        st.sidebar.caption(
            f"Poslední scrape: {selected.last_scraped_at.strftime('%d.%m.%Y %H:%M') if selected.last_scraped_at else 'Ještě neproběhl'}"
        )

    return selected


def sidebar_info():
    """Render sidebar branding and info."""
    st.sidebar.markdown(
        """
        <div style="text-align: center; padding: 1.2rem 0 0.8rem 0;">
            <div style="display: inline-flex; align-items: center; gap: 0.6rem;">
                <div style="width: 36px; height: 36px; background: #00152a; border-radius: 10px;
                            display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 1.1rem;">🏢</span>
                </div>
                <div style="text-align: left;">
                    <h2 style="color: #00152a !important; margin: 0; font-size: 1.15rem; 
                               font-family: 'Manrope', sans-serif; font-weight: 900; 
                               letter-spacing: -0.03em; line-height: 1.2;">GarageLedger</h2>
                    <p style="color: #43474d !important; font-size: 0.7rem; margin: 0;
                              font-family: 'Manrope', sans-serif; font-weight: 600;
                              letter-spacing: -0.01em;">Precision Analytics</p>
                </div>
            </div>
        </div>
        <hr style="border-color: #d8eaff; margin: 0.8rem 0;">
        """,
        unsafe_allow_html=True,
    )

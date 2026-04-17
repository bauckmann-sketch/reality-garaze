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
        <div style="text-align: center; padding: 1rem 0;">
            <h2 style="color: #6C63FF !important; margin-bottom: 0.2rem;">🏢 Realitní Tracker</h2>
            <p style="color: #888 !important; font-size: 0.8rem;">Sreality.cz monitoring</p>
        </div>
        <hr style="border-color: #E0E0E0;">
        """,
        unsafe_allow_html=True,
    )

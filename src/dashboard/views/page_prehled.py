"""Přehled inzerátů — tabs for Prodej vs Pronájem."""

import streamlit as st
import pandas as pd
from datetime import datetime

from src.database import get_session_factory
from src.models import Filter, Listing, PriceHistory
from src.dashboard.components.filters import filter_selector
from src.dashboard.components.charts import metric_card_html, COLORS


def _build_metrics(listings):
    """Calculate summary metrics for a group of listings."""
    prices = [float(l.price) for l in listings if l.price]
    areas = [float(l.area_m2) for l in listings if l.area_m2 and l.area_m2 > 0]
    prices_per_m2 = [
        float(l.price / l.area_m2)
        for l in listings
        if l.price and l.area_m2 and l.area_m2 > 0
    ]
    return {
        "count": len(listings),
        "avg_price": sum(prices) / len(prices) if prices else 0,
        "min_price": min(prices) if prices else 0,
        "max_price": max(prices) if prices else 0,
        "avg_area": sum(areas) / len(areas) if areas else 0,
        "avg_ppm2": sum(prices_per_m2) / len(prices_per_m2) if prices_per_m2 else 0,
        "prices": prices,
    }


def _build_table_data(listings, session):
    """Build table rows for a list of listings."""
    table_data = []
    for listing in listings:
        price_changes = session.query(PriceHistory).filter_by(
            listing_id=listing.id
        ).order_by(PriceHistory.recorded_at.asc()).all()

        price_indicator = ""
        if len(price_changes) > 1:
            first_price = float(price_changes[0].price)
            last_price = float(price_changes[-1].price)
            if last_price < first_price:
                pct = ((last_price - first_price) / first_price) * 100
                price_indicator = f" ↓ {pct:.1f}%"
            elif last_price > first_price:
                pct = ((last_price - first_price) / first_price) * 100
                price_indicator = f" ↑ +{pct:.1f}%"

        row = {
            "Status": "🟢" if listing.is_active else "🔴",
            "Název": listing.name or "—",
            "Cena": f"{listing.price:,.0f} Kč{price_indicator}" if listing.price else "—",
            "Výměra": f"{listing.area_m2} m²" if listing.area_m2 else "—",
            "Cena/m²": f"{listing.price_per_m2:,.0f} Kč" if listing.price_per_m2 else "—",
            "Lokalita": listing.locality or "—",
            "Poplatky": listing.ai_fees or "—",
            "DPH": listing.ai_vat_status or "—",
            "Pozn. cena": listing.price_note or "—",
            "Dní": listing.days_on_market or 0,
            "URL": listing.url or listing.sreality_url,
        }
        table_data.append(row)
    return table_data


def _render_tab_content(listings, session, tab_key, price_label="Ø Cena"):
    """Render metrics + filtered table for a tab."""
    if not listings:
        st.info("Žádné inzeráty v této kategorii.")
        return

    metrics = _build_metrics(listings)

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            metric_card_html("Počet inzerátů", str(metrics["count"])),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            metric_card_html(
                price_label,
                f"{metrics['avg_price']:,.0f} Kč",
                f"Min: {metrics['min_price']:,.0f} | Max: {metrics['max_price']:,.0f}",
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            metric_card_html("Ø Výměra", f"{metrics['avg_area']:,.1f} m²"),
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            metric_card_html("Ø Cena/m²", f"{metrics['avg_ppm2']:,.0f} Kč/m²"),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Filters
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        if metrics["prices"]:
            price_range = st.slider(
                "Filtr ceny (Kč)",
                min_value=int(metrics["min_price"]),
                max_value=int(metrics["max_price"]),
                value=(int(metrics["min_price"]), int(metrics["max_price"])),
                format="%d Kč",
                key=f"price_{tab_key}",
            )
        else:
            price_range = None
    with col_f2:
        search_text = st.text_input(
            "🔍 Hledat v názvu/lokalitě",
            "",
            key=f"search_{tab_key}",
        )

    # Apply filters
    filtered = listings
    if price_range:
        filtered = [
            l for l in filtered
            if l.price and price_range[0] <= float(l.price) <= price_range[1]
        ]
    if search_text:
        sl = search_text.lower()
        filtered = [
            l for l in filtered
            if sl in (l.name or "").lower() or sl in (l.locality or "").lower()
        ]

    # Table
    table_data = _build_table_data(filtered, session)
    if not table_data:
        st.info("Žádné inzeráty odpovídající filtrům.")
        return

    df = pd.DataFrame(table_data)
    st.dataframe(
        df,
        use_container_width=True,
        height=500,
        column_config={
            "URL": st.column_config.LinkColumn("Odkaz", display_text="Otevřít →"),
            "Cena": st.column_config.TextColumn("Cena", width="medium"),
            "Dní": st.column_config.NumberColumn("Dní", format="%d"),
        },
    )
    st.caption(f"Celkem: {len(table_data)} inzerátů")


def render():
    st.title("📋 Přehled inzerátů")

    Session = get_session_factory()
    session = Session()

    try:
        selected_filter = filter_selector(session)
        if not selected_filter:
            st.info("Nejprve přidejte filtr v sekci ⚙️ Nastavení.")
            return

        show_inactive = st.sidebar.checkbox("Zobrazit i stažené", value=False)

        query = session.query(Listing).filter_by(filter_id=selected_filter.id)
        if not show_inactive:
            query = query.filter_by(is_active=True)

        all_listings = query.order_by(Listing.price.asc()).all()

        if not all_listings:
            st.warning("Pro tento filtr zatím nejsou žádné inzeráty. Spusťte scraper.")
            return

        # Split by type
        prodej_drazby = [l for l in all_listings if l.category_type in ("prodej", "dražba")]
        pronajem = [l for l in all_listings if l.category_type == "pronájem"]

        # Tabs
        tab_prodej, tab_pronajem = st.tabs([
            f"🏷️ Prodej & Dražby ({len(prodej_drazby)})",
            f"🔑 Pronájem ({len(pronajem)})",
        ])

        with tab_prodej:
            _render_tab_content(prodej_drazby, session, "prodej", "Ø Prodejní cena")

        with tab_pronajem:
            _render_tab_content(pronajem, session, "pronajem", "Ø Měsíční nájem")

    finally:
        session.close()

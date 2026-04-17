"""Srovnání prodej/pronájem — comparison of sale vs rental prices when both filters exist."""

import streamlit as st
import pandas as pd

from src.database import get_session_factory
from src.models import Filter, Listing, PriceHistory
from src.dashboard.components.charts import (
    comparison_chart,
    metric_card_html,
)


def render():
    st.title("⚖️ Srovnání: Prodej vs. Pronájem")

    Session = get_session_factory()
    session = Session()

    try:
        # Get all active filters
        filters = session.query(Filter).filter_by(is_active=True).order_by(Filter.name).all()

        if len(filters) < 2:
            st.info(
                "Pro srovnání potřebujete alespoň 2 filtry (prodej + pronájem) "
                "pro stejnou lokalitu. Přidejte je v ⚙️ Nastavení."
            )
            _show_roi_calculator()
            return

        # Let user pick two filters to compare
        col1, col2 = st.columns(2)
        filter_options = {f.name: f for f in filters}

        with col1:
            sale_name = st.selectbox(
                "🏷️ Filtr PRODEJ",
                options=list(filter_options.keys()),
                key="sale_filter",
            )
        with col2:
            rent_options = [n for n in filter_options.keys() if n != sale_name]
            if not rent_options:
                st.warning("Přidejte druhý filtr pro srovnání.")
                return
            rent_name = st.selectbox(
                "🔑 Filtr PRONÁJEM",
                options=rent_options,
                key="rent_filter",
            )

        sale_filter = filter_options[sale_name]
        rent_filter = filter_options[rent_name]

        # Get listings
        sale_listings = (
            session.query(Listing)
            .filter_by(filter_id=sale_filter.id, is_active=True)
            .all()
        )
        rent_listings = (
            session.query(Listing)
            .filter_by(filter_id=rent_filter.id, is_active=True)
            .all()
        )

        if not sale_listings or not rent_listings:
            st.warning("Jeden z filtrů nemá žádné aktivní inzeráty.")
            return

        # Summary comparison
        sale_prices = [float(l.price) for l in sale_listings if l.price]
        rent_prices = [float(l.price) for l in rent_listings if l.price]

        sale_ppm2 = [
            float(l.price / l.area_m2)
            for l in sale_listings
            if l.price and l.area_m2 and l.area_m2 > 0
        ]
        rent_ppm2 = [
            float(l.price / l.area_m2)
            for l in rent_listings
            if l.price and l.area_m2 and l.area_m2 > 0
        ]

        st.markdown("### Porovnání aktuálního trhu")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            avg_sale = sum(sale_prices) / len(sale_prices) if sale_prices else 0
            st.markdown(
                metric_card_html(
                    "Ø Cena prodej",
                    f"{avg_sale:,.0f} Kč",
                    f"{len(sale_listings)} inzerátů",
                ),
                unsafe_allow_html=True,
            )
        with col2:
            avg_rent = sum(rent_prices) / len(rent_prices) if rent_prices else 0
            st.markdown(
                metric_card_html(
                    "Ø Cena pronájem",
                    f"{avg_rent:,.0f} Kč/měs",
                    f"{len(rent_listings)} inzerátů",
                ),
                unsafe_allow_html=True,
            )
        with col3:
            # ROI calculation: (annual rent / sale price) * 100
            if avg_sale > 0 and avg_rent > 0:
                roi = (avg_rent * 12 / avg_sale) * 100
                st.markdown(
                    metric_card_html(
                        "Hrubý výnos (ROI)",
                        f"{roi:.1f}% p.a.",
                        f"Návratnost: {100/roi:.0f} let" if roi > 0 else "—",
                        "#43E97B" if roi > 5 else "#FFB74D",
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    metric_card_html("Hrubý výnos (ROI)", "—"),
                    unsafe_allow_html=True,
                )
        with col4:
            if sale_ppm2:
                st.markdown(
                    metric_card_html(
                        "Ø Cena/m² prodej",
                        f"{sum(sale_ppm2)/len(sale_ppm2):,.0f} Kč",
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    metric_card_html("Ø Cena/m² prodej", "—"),
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # Aggregate price trends over time
        sale_history = _get_aggregate_history(session, sale_filter.id)
        rent_history = _get_aggregate_history(session, rent_filter.id)

        if not sale_history.empty and not rent_history.empty:
            fig = comparison_chart(
                sale_history,
                rent_history,
                f"Srovnání: {sale_name} vs {rent_name}",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nedostatek historických dat pro srovnávací graf. Data se budou hromadit s opakovanými scrape cykly.")

        # Standalone ROI calculator
        st.markdown("---")
        _show_roi_calculator()

    finally:
        session.close()


def _get_aggregate_history(session, filter_id: int) -> pd.DataFrame:
    """Get daily average prices for a filter."""
    results = (
        session.query(PriceHistory, Listing)
        .join(Listing, PriceHistory.listing_id == Listing.id)
        .filter(Listing.filter_id == filter_id)
        .order_by(PriceHistory.recorded_at.asc())
        .all()
    )

    if not results:
        return pd.DataFrame()

    records = []
    for ph, listing in results:
        records.append({
            "date": ph.recorded_at.date(),
            "avg_price": float(ph.price),
        })

    df = pd.DataFrame(records)
    return df.groupby("date").agg(avg_price=("avg_price", "mean")).reset_index()


def _show_roi_calculator():
    """Interactive ROI calculator widget."""
    st.markdown("### 🧮 Kalkulačka výnosu")

    col1, col2 = st.columns(2)
    with col1:
        purchase_price = st.number_input(
            "Kupní cena (Kč)",
            min_value=0,
            value=500_000,
            step=50_000,
            format="%d",
        )
    with col2:
        monthly_rent = st.number_input(
            "Měsíční nájem (Kč)",
            min_value=0,
            value=3_000,
            step=500,
            format="%d",
        )

    if purchase_price > 0 and monthly_rent > 0:
        annual_rent = monthly_rent * 12
        gross_roi = (annual_rent / purchase_price) * 100
        payback_years = purchase_price / annual_rent

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                metric_card_html(
                    "Roční výnos brutto",
                    f"{annual_rent:,.0f} Kč",
                    f"{gross_roi:.1f}% p.a.",
                    "#43E97B" if gross_roi > 5 else "#FFB74D",
                ),
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                metric_card_html(
                    "Návratnost",
                    f"{payback_years:.1f} let",
                ),
                unsafe_allow_html=True,
            )
        with col3:
            # Rough net estimate (80% of gross)
            net_roi = gross_roi * 0.80
            st.markdown(
                metric_card_html(
                    "Odhad netto výnosu",
                    f"{net_roi:.1f}% p.a.",
                    "po odpočtu ~20% nákladů",
                    "#8B8D97",
                ),
                unsafe_allow_html=True,
            )

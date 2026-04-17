"""Analýza likvidity — how long listings stay active, market turnover trends."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from src.database import get_session_factory
from src.models import Filter, Listing
from src.dashboard.components.filters import filter_selector
from src.dashboard.components.charts import (
    liquidity_histogram,
    liquidity_trend_chart,
    metric_card_html,
)


def render():
    st.title("⏱️ Analýza likvidity")

    Session = get_session_factory()
    session = Session()

    try:
        selected_filter = filter_selector(session)
        if not selected_filter:
            st.info("Nejprve přidejte filtr v sekci ⚙️ Nastavení.")
            return

        # Get all listings (active and inactive)
        all_listings = (
            session.query(Listing)
            .filter_by(filter_id=selected_filter.id)
            .all()
        )

        if not all_listings:
            st.warning("Žádná historická data pro analýzu likvidity.")
            return

        # Calculate days on market for each listing
        dom_data = []
        for listing in all_listings:
            days = listing.days_on_market
            if days is not None:
                dom_data.append({
                    "name": listing.name,
                    "days_on_market": days,
                    "is_active": listing.is_active,
                    "first_seen": listing.first_seen,
                    "last_seen": listing.last_seen,
                    "price": float(listing.price) if listing.price else 0,
                })

        if not dom_data:
            st.info("Nedostatek dat pro analýzu likvidity.")
            return

        df = pd.DataFrame(dom_data)

        # Summary metrics
        active = df[df["is_active"] == True]
        sold = df[df["is_active"] == False]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(
                metric_card_html("Aktivní inzeráty", str(len(active))),
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                metric_card_html(
                    "Stažené / Prodané",
                    str(len(sold)),
                ),
                unsafe_allow_html=True,
            )
        with col3:
            median_days = df["days_on_market"].median()
            st.markdown(
                metric_card_html(
                    "Medián doby na trhu",
                    f"{median_days:.0f} dní",
                ),
                unsafe_allow_html=True,
            )
        with col4:
            avg_days = df["days_on_market"].mean()
            st.markdown(
                metric_card_html(
                    "Průměr doby na trhu",
                    f"{avg_days:.0f} dní",
                    f"{'↑' if avg_days > median_days else '↓'} vs medián",
                ),
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # ─── Histogram: Days on market ───
        tab1, tab2, tab3 = st.tabs(["📊 Histogram", "📈 Trend", "📋 Data"])

        with tab1:
            # Only show sold/removed listings for meaningful liquidity data
            if len(sold) >= 3:
                fig = liquidity_histogram(
                    sold,
                    f"Doba na trhu (stažené/prodané) — {selected_filter.name}",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                # Show all listings if not enough sold
                fig = liquidity_histogram(
                    df,
                    f"Doba na trhu (všechny inzeráty) — {selected_filter.name}",
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption(
                    "ℹ️ Zobrazeny všechny inzeráty — zatím není dostatek stažených "
                    "pro samostatnou analýzu prodaných."
                )

        with tab2:
            # Weekly trend of new vs removed listings
            records = []
            for listing in all_listings:
                if listing.first_seen:
                    records.append({
                        "date": listing.first_seen,
                        "type": "new",
                    })
                if not listing.is_active and listing.last_seen:
                    records.append({
                        "date": listing.last_seen,
                        "type": "removed",
                    })

            if records:
                df_events = pd.DataFrame(records)
                df_events["week"] = pd.to_datetime(df_events["date"]).dt.to_period("W").apply(
                    lambda r: r.start_time
                )

                new_by_week = df_events[df_events["type"] == "new"].groupby("week").size().reset_index(name="new_count")
                removed_by_week = df_events[df_events["type"] == "removed"].groupby("week").size().reset_index(name="removed_count")

                df_trend = pd.merge(new_by_week, removed_by_week, on="week", how="outer").fillna(0)
                df_trend = df_trend.sort_values("week")

                fig = liquidity_trend_chart(
                    df_trend,
                    f"Týdenní přehled — {selected_filter.name}",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nedostatek dat pro trendový graf.")

        with tab3:
            # Detailed table
            df_display = df[["name", "days_on_market", "is_active", "price", "first_seen", "last_seen"]].copy()
            df_display.columns = ["Název", "Dní na trhu", "Aktivní", "Cena", "První výskyt", "Poslední výskyt"]
            df_display["Aktivní"] = df_display["Aktivní"].map({True: "🟢 Ano", False: "🔴 Ne"})
            df_display["Cena"] = df_display["Cena"].apply(lambda x: f"{x:,.0f} Kč" if x > 0 else "—")
            df_display = df_display.sort_values("Dní na trhu", ascending=False)

            st.dataframe(df_display, use_container_width=True, height=500)

    finally:
        session.close()

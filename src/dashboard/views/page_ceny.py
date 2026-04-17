"""Cenové grafy — aggregate first, individual second."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.database import get_session_factory
from src.models import Listing, PriceHistory
from src.dashboard.components.filters import filter_selector
from src.dashboard.components.charts import metric_card_html, COLORS


def _make_chart(df, x_col, y_col, title, y_title, color=None):
    """Simple line+markers chart without CHART_LAYOUT conflicts."""
    color = color or COLORS["primary"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x_col],
        y=df[y_col],
        mode="lines+markers",
        line=dict(color=color, width=3),
        marker=dict(size=6, color=color),
        fill="tozeroy",
        fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.08)",
        hovertemplate="<b>%{x}</b><br>" + y_title + ": %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        yaxis_title=y_title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=COLORS["text"]),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    fig.update_xaxes(gridcolor=COLORS["grid"])
    fig.update_yaxes(gridcolor=COLORS["grid"], tickformat=",")
    return fig


def render():
    st.title("📈 Cenové grafy")

    Session = get_session_factory()
    session = Session()

    try:
        selected_filter = filter_selector(session)
        if not selected_filter:
            st.info("Nejprve přidejte filtr v sekci ⚙️ Nastavení.")
            return

        tab_agg, tab_detail = st.tabs(["📉 Agregovaný přehled", "📊 Konkrétní inzerát"])

        # ─── Tab 1: Aggregate ───
        with tab_agg:
            st.subheader("Průměrná cena za m² v čase")

            all_history = (
                session.query(PriceHistory, Listing.area_m2, Listing.category_type)
                .join(Listing, PriceHistory.listing_id == Listing.id)
                .filter(Listing.filter_id == selected_filter.id)
                .filter(Listing.area_m2 > 0)
                .order_by(PriceHistory.recorded_at.asc())
                .all()
            )

            if not all_history:
                st.info("Zatím nejsou k dispozici cenová data. Spusťte scraper.")
                return

            # Build records grouped by type
            records_prodej = []
            records_pronajem = []
            for ph, area, cat_type in all_history:
                if area and float(area) > 0:
                    entry = {
                        "date": ph.recorded_at.date(),
                        "price_per_m2": float(ph.price) / float(area),
                        "price": float(ph.price),
                    }
                    if cat_type == "pronájem":
                        records_pronajem.append(entry)
                    else:
                        records_prodej.append(entry)

            # Show prodej stats
            if records_prodej:
                df_p = pd.DataFrame(records_prodej)
                df_agg_p = df_p.groupby("date").agg(
                    avg_price_per_m2=("price_per_m2", "mean"),
                    avg_price=("price", "mean"),
                    count=("price", "count"),
                ).reset_index()

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(metric_card_html(
                        "Ø Prodejní cena/m²",
                        f"{df_agg_p['avg_price_per_m2'].iloc[-1]:,.0f} Kč",
                    ), unsafe_allow_html=True)
                with col2:
                    st.markdown(metric_card_html(
                        "Ø Prodejní cena",
                        f"{df_agg_p['avg_price'].iloc[-1]:,.0f} Kč",
                    ), unsafe_allow_html=True)
                with col3:
                    st.markdown(metric_card_html(
                        "Prodejních inzerátů",
                        str(int(df_agg_p['count'].iloc[-1])),
                    ), unsafe_allow_html=True)

                if len(df_agg_p) > 1:
                    fig = _make_chart(df_agg_p, "date", "avg_price_per_m2",
                                      "Prodej — Ø cena/m²", "Kč/m²", COLORS["primary"])
                    st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")

            # Show pronájem stats
            if records_pronajem:
                df_r = pd.DataFrame(records_pronajem)
                df_agg_r = df_r.groupby("date").agg(
                    avg_price_per_m2=("price_per_m2", "mean"),
                    avg_price=("price", "mean"),
                    count=("price", "count"),
                ).reset_index()

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(metric_card_html(
                        "Ø Nájem/m²",
                        f"{df_agg_r['avg_price_per_m2'].iloc[-1]:,.0f} Kč",
                    ), unsafe_allow_html=True)
                with col2:
                    st.markdown(metric_card_html(
                        "Ø Měsíční nájem",
                        f"{df_agg_r['avg_price'].iloc[-1]:,.0f} Kč",
                    ), unsafe_allow_html=True)
                with col3:
                    st.markdown(metric_card_html(
                        "Pronájemních inzerátů",
                        str(int(df_agg_r['count'].iloc[-1])),
                    ), unsafe_allow_html=True)

                if len(df_agg_r) > 1:
                    fig = _make_chart(df_agg_r, "date", "avg_price_per_m2",
                                      "Pronájem — Ø cena/m²", "Kč/m²/měs", COLORS["accent"])
                    st.plotly_chart(fig, use_container_width=True)

            if not records_prodej and not records_pronajem:
                st.info("Zatím nejsou cenová data.")

        # ─── Tab 2: Individual listing ───
        with tab_detail:
            st.subheader("Vývoj ceny vybraného inzerátu")

            listings = (
                session.query(Listing)
                .filter_by(filter_id=selected_filter.id)
                .order_by(Listing.name)
                .all()
            )

            if not listings:
                st.warning("Žádné inzeráty.")
                return

            listing_options = {
                f"{l.name} — {l.locality} ({l.price:,.0f} Kč)" if l.price else f"{l.name} — {l.locality}": l
                for l in listings
            }
            selected_name = st.selectbox("Vyberte inzerát", list(listing_options.keys()))
            selected_listing = listing_options[selected_name]

            history = (
                session.query(PriceHistory)
                .filter_by(listing_id=selected_listing.id)
                .order_by(PriceHistory.recorded_at.asc())
                .all()
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(metric_card_html(
                    "Aktuální cena",
                    f"{selected_listing.price:,.0f} Kč" if selected_listing.price else "—",
                ), unsafe_allow_html=True)
            with col2:
                st.markdown(metric_card_html(
                    "Cena za m²",
                    f"{selected_listing.price_per_m2:,.0f} Kč/m²" if selected_listing.price_per_m2 else "—",
                ), unsafe_allow_html=True)
            with col3:
                st.markdown(metric_card_html(
                    "Dní na trhu",
                    str(selected_listing.days_on_market or 0),
                ), unsafe_allow_html=True)

            if len(history) >= 2:
                df = pd.DataFrame([
                    {"recorded_at": h.recorded_at, "price": float(h.price)}
                    for h in history
                ])
                fig = _make_chart(df, "recorded_at", "price",
                                  f"Vývoj ceny: {selected_listing.name}", "Kč")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📌 Tento inzerát má zatím jen jednu cenovou hodnotu. "
                        "Graf se zobrazí po detekci změny ceny.")

            # Detail expander
            with st.expander("ℹ️ Detail inzerátu"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Název:** {selected_listing.name}")
                    st.markdown(f"**Lokalita:** {selected_listing.locality}")
                    st.markdown(f"**Výměra:** {selected_listing.area_m2} m²")
                    st.markdown(f"**Stavba:** {selected_listing.building_type or '—'}")
                with c2:
                    st.markdown(f"**Prodejce:** {selected_listing.seller_name or '—'}")
                    st.markdown(f"**Telefon:** {selected_listing.seller_phone or '—'}")
                    st.markdown(f"**Poplatky:** {selected_listing.ai_fees or '—'}")
                    st.markdown(f"**DPH:** {selected_listing.ai_vat_status or '—'}")

                if selected_listing.url:
                    st.link_button("🔗 Otevřít na Sreality", selected_listing.url)

    finally:
        session.close()

"""Cenové grafy — clickable metric boxes with historical charts."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from src.database import get_session_factory
from src.models import Listing, PriceHistory
from src.dashboard.components.filters import filter_selector
from src.dashboard.components.charts import COLORS


def _make_chart(df, x_col, y_col, title, y_title, color=None, chart_type="line"):
    """Universal chart builder."""
    color = color or COLORS["primary"]
    fig = go.Figure()

    if chart_type == "bar":
        fig.add_trace(go.Bar(
            x=df[x_col],
            y=df[y_col],
            marker_color=color,
            opacity=0.85,
            hovertemplate="<b>%{x}</b><br>" + y_title + ": %{y:,.0f}<extra></extra>",
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df[x_col],
            y=df[y_col],
            mode="lines+markers",
            line=dict(color=color, width=3),
            marker=dict(size=6, color=COLORS.get("accent", color),
                        line=dict(color=color, width=2)),
            fill="tozeroy",
            fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.06)",
            hovertemplate="<b>%{x}</b><br>" + y_title + ": %{y:,.0f}<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=18, family="Manrope, sans-serif",
                                          color=COLORS["primary"])),
        yaxis_title=y_title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=COLORS["text"]),
        margin=dict(l=20, r=20, t=50, b=20),
        hoverlabel=dict(
            bgcolor=COLORS["primary"],
            font_size=13,
            font_family="Inter, sans-serif",
            font_color="#ffffff",
            bordercolor=COLORS.get("accent", color),
        ),
    )
    fig.update_xaxes(gridcolor=COLORS["grid"])
    fig.update_yaxes(gridcolor=COLORS["grid"], tickformat=",")
    return fig


def _clickable_metric_card(label, value, key, delta=None, is_selected=False):
    """Render a clickable metric card using a Streamlit button with custom styling."""
    border_color = COLORS["primary"] if is_selected else COLORS["grid"]
    border_width = "2px" if is_selected else "1px"
    shadow = "0 4px 20px rgba(0, 21, 42, 0.1)" if is_selected else "0 1px 3px rgba(0, 21, 42, 0.04)"
    accent_bar = f"background: linear-gradient(90deg, {COLORS['accent']}, {COLORS['secondary']});" if is_selected else f"background: {COLORS['grid']};"

    delta_html = ""
    if delta:
        delta_html = f'<p style="color: {COLORS["text_muted"]}; font-size: 0.8rem; margin: 0.3rem 0 0 0;">{delta}</p>'

    st.markdown(f"""
    <div style="background: {COLORS['card_bg']}; 
                padding: 1.5rem 1.8rem; border-radius: 16px; 
                border: {border_width} solid {border_color};
                box-shadow: {shadow};
                cursor: pointer;
                transition: all 0.2s ease;
                margin-bottom: 0.5rem;
                position: relative;
                overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; width: 100%; height: 3px; {accent_bar}"></div>
        <p style="color: {COLORS['text_muted']}; font-size: 0.8rem; margin: 0 0 0.5rem 0;
                  text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;">{label}</p>
        <p style="color: {COLORS['primary']}; font-size: 2rem; font-weight: 900; margin: 0;
                  font-family: 'Manrope', 'Inter', sans-serif; letter-spacing: -0.02em;">{value}</p>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

    return st.button(
        f"📊 {label}",
        key=key,
        use_container_width=True,
        type="secondary" if not is_selected else "primary",
    )


def _compute_daily_snapshots(session, filter_id, category_types):
    """
    Compute daily snapshots of aggregate metrics from listings + price_history.
    
    For each day from the first listing seen to today, we compute:
    - count: how many listings were active on that day (first_seen <= day <= last_seen)
    - avg_price: average price of those listings
    - avg_price_per_m2: average price per m² of those listings
    
    This gives us a true time-series of the market, not just days when price changes happened.
    """
    # Get all listings for this filter/category
    listings = (
        session.query(Listing)
        .filter(Listing.filter_id == filter_id)
        .filter(Listing.category_type.in_(category_types))
        .all()
    )

    if not listings:
        return pd.DataFrame()

    # Find date range
    first_date = min(l.first_seen.date() for l in listings if l.first_seen)
    last_date = datetime.utcnow().date()

    # For each listing, get its price history to know price at each point in time
    listing_data = []
    for l in listings:
        # Get price history sorted by time
        prices = (
            session.query(PriceHistory)
            .filter_by(listing_id=l.id)
            .order_by(PriceHistory.recorded_at.asc())
            .all()
        )
        if not prices:
            continue

        listing_data.append({
            "listing": l,
            "first_seen": l.first_seen.date() if l.first_seen else first_date,
            "last_seen": l.last_seen.date() if l.last_seen else last_date,
            "area_m2": float(l.area_m2) if l.area_m2 and float(l.area_m2) > 0 else None,
            "prices": [(p.recorded_at.date(), float(p.price)) for p in prices],
        })

    if not listing_data:
        return pd.DataFrame()

    # Build daily snapshots
    snapshots = []
    current = first_date
    while current <= last_date:
        day_prices = []
        day_prices_per_m2 = []

        for ld in listing_data:
            # Was this listing active on this day?
            if ld["first_seen"] <= current <= ld["last_seen"]:
                # Find the most recent price on or before this day
                price_on_day = None
                for price_date, price_val in ld["prices"]:
                    if price_date <= current:
                        price_on_day = price_val
                    else:
                        break

                if price_on_day:
                    day_prices.append(price_on_day)
                    if ld["area_m2"]:
                        day_prices_per_m2.append(price_on_day / ld["area_m2"])

        if day_prices:
            snapshots.append({
                "date": current,
                "count": len(day_prices),
                "avg_price": sum(day_prices) / len(day_prices),
                "min_price": min(day_prices),
                "max_price": max(day_prices),
                "avg_price_per_m2": (
                    sum(day_prices_per_m2) / len(day_prices_per_m2)
                    if day_prices_per_m2 else 0
                ),
            })

        current += timedelta(days=1)

    return pd.DataFrame(snapshots)


def render():
    st.title("📈 Cenové grafy")

    Session = get_session_factory()
    session = Session()

    try:
        selected_filter = filter_selector(session)
        if not selected_filter:
            st.info("Nejprve přidejte filtr v sekci ⚙️ Nastavení.")
            return

        # Split into tabs for Prodej and Pronájem
        tab_prodej, tab_pronajem, tab_detail = st.tabs([
            "🏷️ Prodej & Dražby",
            "🔑 Pronájem",
            "📊 Konkrétní inzerát",
        ])

        # ─── Tab 1: Prodej & Dražby ───
        with tab_prodej:
            _render_aggregate_tab(
                session, selected_filter.id,
                category_types=["prodej", "dražba"],
                tab_key="prodej",
                labels={
                    "price_per_m2": "Ø Cena/m²",
                    "avg_price": "Ø Prodejní cena",
                    "count": "Aktivních inzerátů",
                    "chart_title_ppm2": "Průměrná cena za m² v čase",
                    "chart_title_price": "Průměrná prodejní cena v čase",
                    "chart_title_count": "Počet aktivních inzerátů v čase",
                },
            )

        # ─── Tab 2: Pronájem ───
        with tab_pronajem:
            _render_aggregate_tab(
                session, selected_filter.id,
                category_types=["pronájem"],
                tab_key="pronajem",
                labels={
                    "price_per_m2": "Ø Nájem/m²",
                    "avg_price": "Ø Měsíční nájem",
                    "count": "Aktivních inzerátů",
                    "chart_title_ppm2": "Průměrný nájem za m² v čase",
                    "chart_title_price": "Průměrný měsíční nájem v čase",
                    "chart_title_count": "Počet aktivních inzerátů v čase",
                },
            )

        # ─── Tab 3: Konkrétní inzerát ───
        with tab_detail:
            _render_detail_tab(session, selected_filter.id)

    finally:
        session.close()


def _render_aggregate_tab(session, filter_id, category_types, tab_key, labels):
    """Render an aggregate tab with clickable metric boxes and historical chart."""

    df = _compute_daily_snapshots(session, filter_id, category_types)

    if df.empty:
        st.info("Zatím nejsou k dispozici cenová data pro tuto kategorii.")
        return

    # Current values (latest day)
    latest = df.iloc[-1]
    current_ppm2 = latest["avg_price_per_m2"]
    current_avg_price = latest["avg_price"]
    current_count = int(latest["count"])

    # Calculate deltas vs first available day
    first = df.iloc[0]
    delta_ppm2 = ""
    delta_price = ""
    delta_count = ""

    if len(df) > 1:
        if first["avg_price_per_m2"] > 0:
            pct = ((current_ppm2 - first["avg_price_per_m2"]) / first["avg_price_per_m2"]) * 100
            arrow = "↑" if pct >= 0 else "↓"
            delta_ppm2 = f"{arrow} {pct:+.1f}% od začátku"
        if first["avg_price"] > 0:
            pct = ((current_avg_price - first["avg_price"]) / first["avg_price"]) * 100
            arrow = "↑" if pct >= 0 else "↓"
            delta_price = f"{arrow} {pct:+.1f}% od začátku"
        diff = current_count - int(first["count"])
        if diff != 0:
            arrow = "↑" if diff > 0 else "↓"
            delta_count = f"{arrow} {diff:+d} od začátku"

    # Initialize selected chart state
    state_key = f"selected_chart_{tab_key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = "price_per_m2"

    # Metric boxes as buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        clicked = _clickable_metric_card(
            labels["price_per_m2"],
            f"{current_ppm2:,.0f} Kč",
            key=f"btn_ppm2_{tab_key}",
            delta=delta_ppm2,
            is_selected=(st.session_state[state_key] == "price_per_m2"),
        )
        if clicked:
            st.session_state[state_key] = "price_per_m2"
            st.rerun()

    with col2:
        clicked = _clickable_metric_card(
            labels["avg_price"],
            f"{current_avg_price:,.0f} Kč",
            key=f"btn_price_{tab_key}",
            delta=delta_price,
            is_selected=(st.session_state[state_key] == "avg_price"),
        )
        if clicked:
            st.session_state[state_key] = "avg_price"
            st.rerun()

    with col3:
        clicked = _clickable_metric_card(
            labels["count"],
            str(current_count),
            key=f"btn_count_{tab_key}",
            delta=delta_count,
            is_selected=(st.session_state[state_key] == "count"),
        )
        if clicked:
            st.session_state[state_key] = "count"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Show the selected chart
    selected = st.session_state[state_key]

    if selected == "price_per_m2":
        if len(df) > 1:
            fig = _make_chart(df, "date", "avg_price_per_m2",
                              labels["chart_title_ppm2"], "Kč/m²", COLORS["primary"])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📌 Graf se zobrazí po nasbírání dat za alespoň 2 dny.")

    elif selected == "avg_price":
        if len(df) > 1:
            fig = _make_chart(df, "date", "avg_price",
                              labels["chart_title_price"], "Kč", COLORS["accent"])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📌 Graf se zobrazí po nasbírání dat za alespoň 2 dny.")

    elif selected == "count":
        if len(df) > 1:
            fig = _make_chart(df, "date", "count",
                              labels["chart_title_count"], "Počet", COLORS["warning"],
                              chart_type="bar")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📌 Graf se zobrazí po nasbírání dat za alespoň 2 dny.")

    # Additional stats table
    with st.expander("📊 Denní data"):
        display_df = df.copy()
        display_df["date"] = display_df["date"].astype(str)
        display_df = display_df.rename(columns={
            "date": "Datum",
            "count": "Počet",
            "avg_price": "Ø Cena",
            "min_price": "Min cena",
            "max_price": "Max cena",
            "avg_price_per_m2": "Ø Cena/m²",
        })
        for col in ["Ø Cena", "Min cena", "Max cena", "Ø Cena/m²"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f} Kč")
        st.dataframe(display_df, use_container_width=True, hide_index=True)


def _render_detail_tab(session, filter_id):
    """Render individual listing price history tab."""
    st.subheader("Vývoj ceny vybraného inzerátu")

    listings = (
        session.query(Listing)
        .filter_by(filter_id=filter_id)
        .order_by(Listing.name)
        .all()
    )

    if not listings:
        st.warning("Žádné inzeráty.")
        return

    listing_options = {
        f"{'🟢' if l.is_active else '🔴'} {l.name} — {l.locality} ({l.price:,.0f} Kč)" if l.price
        else f"{'🟢' if l.is_active else '🔴'} {l.name} — {l.locality}": l
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

    from src.dashboard.components.charts import metric_card_html
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

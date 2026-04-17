"""Nastavení — filter management, scraper status, and system info."""

import streamlit as st
from datetime import datetime, timedelta

from src.database import get_session_factory
from src.models import Filter, Listing, PriceHistory
from src.scraper.scheduler import run_scrape_for_filter
from src.dashboard.components.charts import metric_card_html, COLORS


def render():
    st.title("⚙️ Nastavení")

    Session = get_session_factory()
    session = Session()

    try:
        tab_status, tab_filters, tab_system = st.tabs([
            "📡 Stav scraperu",
            "📍 Filtry",
            "🔧 Systém",
        ])

        # ─── Tab 1: Scraper Status ───
        with tab_status:
            st.subheader("📡 Stav scraperu")

            filters = session.query(Filter).filter_by(is_active=True).all()

            if not filters:
                st.warning("Žádné aktivní filtry.")
                return

            for f in filters:
                total = session.query(Listing).filter_by(filter_id=f.id).count()
                active = session.query(Listing).filter_by(filter_id=f.id, is_active=True).count()
                prodej = session.query(Listing).filter_by(
                    filter_id=f.id, is_active=True, category_type="prodej"
                ).count()
                pronajem = session.query(Listing).filter_by(
                    filter_id=f.id, is_active=True, category_type="pronájem"
                ).count()

                # Last scrape info
                if f.last_scraped_at:
                    last = f.last_scraped_at
                    ago = datetime.utcnow() - last
                    if ago.total_seconds() < 3600:
                        ago_str = f"před {int(ago.total_seconds() / 60)} min"
                    elif ago.total_seconds() < 86400:
                        ago_str = f"před {int(ago.total_seconds() / 3600)}h"
                    else:
                        ago_str = f"před {ago.days}d"
                    last_str = f"{last.strftime('%d.%m.%Y %H:%M')} ({ago_str})"
                    next_scrape = last + timedelta(hours=f.scrape_interval_hours)
                    next_str = next_scrape.strftime("%d.%m. %H:%M")
                else:
                    last_str = "⏳ Probíhá první scrape..."
                    next_str = "—"

                # Status card
                st.markdown(f"### 🟢 {f.name}")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(metric_card_html(
                        "Aktivních inzerátů", str(active),
                        f"z {total} celkem"
                    ), unsafe_allow_html=True)
                with col2:
                    st.markdown(metric_card_html(
                        "🏷️ Prodej", str(prodej),
                    ), unsafe_allow_html=True)
                with col3:
                    st.markdown(metric_card_html(
                        "🔑 Pronájem", str(pronajem),
                    ), unsafe_allow_html=True)
                with col4:
                    st.markdown(metric_card_html(
                        "Interval", f"{f.scrape_interval_hours}h",
                    ), unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                col_l, col_n = st.columns(2)
                with col_l:
                    st.info(f"**Poslední scrape:** {last_str}")
                with col_n:
                    st.info(f"**Další scrape:** {next_str}")

                # Recent listings
                recent = (
                    session.query(Listing)
                    .filter_by(filter_id=f.id, is_active=True)
                    .order_by(Listing.created_at.desc())
                    .limit(5)
                    .all()
                )
                if recent:
                    st.markdown("**Posledních 5 přidaných:**")
                    for l in recent:
                        created = l.created_at.strftime("%d.%m. %H:%M") if l.created_at else "?"
                        price = f"{l.price:,.0f} Kč" if l.price else "—"
                        st.caption(f"  `{created}` — {l.name} | {l.locality} | {price}")

                st.markdown("---")

            # Auto-refresh toggle
            auto = st.checkbox("🔄 Auto-refresh (každých 30s)", value=False)
            if auto:
                import time
                time.sleep(30)
                st.rerun()

        # ─── Tab 2: Filters ───
        with tab_filters:
            st.subheader("Správa filtrů")

            all_filters = session.query(Filter).order_by(Filter.created_at.desc()).all()

            if not all_filters:
                st.info("Žádné filtry.")
            else:
                for f in all_filters:
                    listing_count = session.query(Listing).filter_by(filter_id=f.id).count()
                    active_count = session.query(Listing).filter_by(filter_id=f.id, is_active=True).count()

                    with st.container():
                        col1, col2, col3 = st.columns([4, 1, 1])

                        with col1:
                            status = "🟢" if f.is_active else "🔴"
                            st.markdown(f"**{status} {f.name}**")
                            st.caption(
                                f"Interval: {f.scrape_interval_hours}h | "
                                f"Inzeráty: {active_count}/{listing_count}"
                            )
                            last_scrape = (
                                f.last_scraped_at.strftime("%d.%m. %H:%M")
                                if f.last_scraped_at
                                else "Nikdy"
                            )
                            st.caption(f"Poslední scrape: {last_scrape}")

                        with col2:
                            if st.button("▶️ Scrape", key=f"run_{f.id}"):
                                with st.spinner(f"Scrapuji '{f.name}'..."):
                                    try:
                                        stats = run_scrape_for_filter(f, session)
                                        st.success(
                                            f"✅ Nové: {stats['new']}, "
                                            f"Akt: {stats['updated']}, "
                                            f"Stažené: {stats['deactivated']}"
                                        )
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ {e}")

                        with col3:
                            label = "🗑️" if f.is_active else "♻️"
                            if st.button(label, key=f"toggle_{f.id}"):
                                f.is_active = not f.is_active
                                session.commit()
                                st.rerun()

                        st.markdown("---")

        # ─── Tab 3: System ───
        with tab_system:
            st.subheader("Systém")

            total_listings = session.query(Listing).count()
            active_listings = session.query(Listing).filter_by(is_active=True).count()
            total_prices = session.query(PriceHistory).count()
            total_filters = session.query(Filter).count()

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(metric_card_html("Celkem inzerátů", str(total_listings)), unsafe_allow_html=True)
            with col2:
                st.markdown(metric_card_html("Aktivních", str(active_listings)), unsafe_allow_html=True)
            with col3:
                st.markdown(metric_card_html("Cenových záznamů", str(total_prices)), unsafe_allow_html=True)
            with col4:
                st.markdown(metric_card_html("Filtrů", str(total_filters)), unsafe_allow_html=True)

    finally:
        session.close()

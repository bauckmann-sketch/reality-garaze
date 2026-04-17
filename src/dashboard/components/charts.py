"""Reusable Plotly chart components for the dashboard."""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


# Shared color palette
COLORS = {
    "primary": "#6C63FF",
    "secondary": "#FF6584",
    "accent": "#43E97B",
    "warning": "#FFB74D",
    "bg_dark": "#0E1117",
    "card_bg": "#1A1D23",
    "text": "#FAFAFA",
    "text_muted": "#8B8D97",
    "grid": "#2A2D35",
    "up": "#43E97B",
    "down": "#FF6584",
}

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=COLORS["text"]),
    margin=dict(l=20, r=20, t=40, b=20),
    hoverlabel=dict(
        bgcolor=COLORS["card_bg"],
        font_size=13,
        font_family="Inter, sans-serif",
    ),
)

def _apply_grid(fig):
    """Apply grid styling to axes after layout."""
    fig.update_xaxes(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"])
    fig.update_yaxes(gridcolor=COLORS["grid"], zerolinecolor=COLORS["grid"])


def price_history_chart(df: pd.DataFrame, title: str = "Vývoj ceny") -> go.Figure:
    """
    Line chart showing price changes over time for a single listing.

    Args:
        df: DataFrame with columns 'recorded_at' and 'price'.
        title: Chart title.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["recorded_at"],
        y=df["price"],
        mode="lines+markers",
        name="Cena",
        line=dict(color=COLORS["primary"], width=3),
        marker=dict(size=8, color=COLORS["primary"]),
        hovertemplate="<b>%{x|%d.%m.%Y}</b><br>Cena: %{y:,.0f} Kč<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        yaxis_title="Cena (Kč)",
        **CHART_LAYOUT,
    )
    fig.update_yaxes(tickformat=",")
    _apply_grid(fig)

    return fig


def avg_price_per_m2_chart(df: pd.DataFrame, title: str = "Průměrná cena za m²") -> go.Figure:
    """
    Aggregated line chart showing average price per m² over time.

    Args:
        df: DataFrame with columns 'date' and 'avg_price_per_m2'.
        title: Chart title.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["avg_price_per_m2"],
        mode="lines+markers",
        name="Ø Cena/m²",
        line=dict(color=COLORS["accent"], width=3),
        marker=dict(size=6, color=COLORS["accent"]),
        fill="tozeroy",
        fillcolor="rgba(67, 233, 123, 0.1)",
        hovertemplate="<b>%{x|%d.%m.%Y}</b><br>Ø cena/m²: %{y:,.0f} Kč<extra></extra>",
    ))

    if "count" in df.columns:
        fig.add_trace(go.Bar(
            x=df["date"],
            y=df["count"],
            name="Počet inzerátů",
            marker_color="rgba(108, 99, 255, 0.3)",
            yaxis="y2",
            hovertemplate="<b>%{x|%d.%m.%Y}</b><br>Počet: %{y}<extra></extra>",
        ))

        fig.update_layout(
            yaxis2=dict(
                title="Počet inzerátů",
                overlaying="y",
                side="right",
                gridcolor="rgba(0,0,0,0)",
            ),
        )

    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        yaxis_title="Cena/m² (Kč)",
        **CHART_LAYOUT,
    )
    fig.update_yaxes(tickformat=",")
    _apply_grid(fig)

    return fig


def liquidity_histogram(df: pd.DataFrame, title: str = "Doba na trhu") -> go.Figure:
    """
    Histogram of days listings stay on market.

    Args:
        df: DataFrame with column 'days_on_market'.
        title: Chart title.
    """
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=df["days_on_market"],
        nbinsx=20,
        marker_color=COLORS["primary"],
        opacity=0.8,
        hovertemplate="<b>%{x} dní</b><br>Počet: %{y}<extra></extra>",
    ))

    # Add median line
    median_days = df["days_on_market"].median()
    fig.add_vline(
        x=median_days,
        line_dash="dash",
        line_color=COLORS["secondary"],
        annotation_text=f"Medián: {median_days:.0f} dní",
        annotation_position="top",
        annotation_font_color=COLORS["secondary"],
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        xaxis_title="Počet dní na trhu",
        yaxis_title="Počet inzerátů",
        **CHART_LAYOUT,
    )
    _apply_grid(fig)

    return fig


def liquidity_trend_chart(df: pd.DataFrame, title: str = "Trend likvidity") -> go.Figure:
    """
    Chart showing new vs removed listings over time.

    Args:
        df: DataFrame with columns 'week', 'new_count', 'removed_count'.
        title: Chart title.
    """
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["week"],
        y=df["new_count"],
        name="Nové inzeráty",
        marker_color=COLORS["accent"],
        opacity=0.8,
    ))

    fig.add_trace(go.Bar(
        x=df["week"],
        y=-df["removed_count"],
        name="Stažené inzeráty",
        marker_color=COLORS["secondary"],
        opacity=0.8,
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        barmode="relative",
        xaxis_title="Týden",
        yaxis_title="Počet inzerátů",
        **CHART_LAYOUT,
    )
    _apply_grid(fig)

    return fig


def comparison_chart(
    df_sale: pd.DataFrame,
    df_rent: pd.DataFrame,
    title: str = "Prodej vs. Pronájem"
) -> go.Figure:
    """
    Dual-axis chart comparing sale and rent prices.

    Args:
        df_sale: DataFrame with 'date' and 'avg_price' for sales.
        df_rent: DataFrame with 'date' and 'avg_price' for rentals.
        title: Chart title.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=df_sale["date"],
            y=df_sale["avg_price"],
            name="Ø Cena prodej",
            line=dict(color=COLORS["primary"], width=3),
            hovertemplate="<b>%{x|%d.%m.%Y}</b><br>Prodej: %{y:,.0f} Kč<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=df_rent["date"],
            y=df_rent["avg_price"],
            name="Ø Cena pronájem",
            line=dict(color=COLORS["accent"], width=3),
            hovertemplate="<b>%{x|%d.%m.%Y}</b><br>Pronájem: %{y:,.0f} Kč/měs<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        **CHART_LAYOUT,
    )
    fig.update_yaxes(title_text="Cena prodej (Kč)", secondary_y=False, tickformat=",")
    fig.update_yaxes(title_text="Cena pronájem (Kč/měs)", secondary_y=True, tickformat=",")
    _apply_grid(fig)

    return fig


def metric_card_html(label: str, value: str, delta: str = None, delta_color: str = None) -> str:
    """Generate HTML for a styled metric card."""
    delta_html = ""
    if delta:
        color = delta_color or COLORS["text_muted"]
        delta_html = f'<p style="color: {color}; font-size: 0.85rem; margin: 0;">{delta}</p>'

    return f"""
    <div style="background: linear-gradient(135deg, {COLORS['card_bg']}, #22252D); 
                padding: 1.2rem 1.5rem; border-radius: 12px; 
                border: 1px solid {COLORS['grid']};">
        <p style="color: {COLORS['text_muted']}; font-size: 0.85rem; margin: 0 0 0.3rem 0;">{label}</p>
        <p style="color: {COLORS['text']}; font-size: 1.8rem; font-weight: 700; margin: 0;">{value}</p>
        {delta_html}
    </div>
    """

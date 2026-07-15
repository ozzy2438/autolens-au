"""Shared chart components for the dashboard."""

import pandas as pd
import plotly.graph_objects as go


def create_valuation_gauge(
    estimate: float,
    lower: float,
    upper: float,
    title: str = "Estimated Value",
) -> go.Figure:
    """Create a gauge chart showing valuation with range."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=estimate,
            number={"prefix": "$", "valueformat": ",.0f"},
            title={"text": title},
            gauge={
                "axis": {"range": [lower * 0.8, upper * 1.2]},
                "bar": {"color": "#1f77b4"},
                "steps": [
                    {"range": [lower, upper], "color": "lightblue"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 2},
                    "thickness": 0.75,
                    "value": estimate,
                },
            },
        )
    )
    fig.update_layout(height=300)
    return fig


def create_depreciation_chart(
    curves: dict[str, pd.DataFrame],
    max_age: int = 15,
) -> go.Figure:
    """Create multi-line depreciation comparison chart."""
    fig = go.Figure()

    for segment, curve_df in curves.items():
        fig.add_trace(
            go.Scatter(
                x=curve_df["age"],
                y=curve_df["retention_pct"],
                mode="lines+markers",
                name=segment,
                line=dict(width=2.5),
            )
        )

    fig.update_layout(
        title="Price Retention Over Time",
        xaxis_title="Vehicle Age (years)",
        yaxis_title="Value Retained (%)",
        yaxis=dict(range=[0, 105]),
        hovermode="x unified",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def create_shap_waterfall(
    drivers: list[dict],
    base_value: float = 0,
) -> go.Figure:
    """Create a waterfall chart from local TreeSHAP contributions."""
    features = [d["feature"] for d in drivers]
    impacts = [d["impact_aud"] for d in drivers]

    fig = go.Figure(
        go.Waterfall(
            x=features,
            y=impacts,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "#2ecc71"}},
            decreasing={"marker": {"color": "#e74c3c"}},
        )
    )

    fig.update_layout(
        title="Price Drivers (Impact on Valuation)",
        yaxis_title="Impact (AUD)",
        template="plotly_white",
        showlegend=False,
    )

    return fig

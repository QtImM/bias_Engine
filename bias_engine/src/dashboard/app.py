"""
Streamlit Dashboard for Multi-Timeframe Bias Engine.

Run: streamlit run src/dashboard/app.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def load_predictions(data_dir: Path) -> pd.DataFrame:
    """Load latest predictions from Parquet."""
    pred_path = data_dir / "predictions" / "predictions.parquet"
    if pred_path.exists():
        return pd.read_parquet(pred_path)
    return pd.DataFrame()


def load_factor_values(data_dir: Path) -> pd.DataFrame:
    """Load factor values from Parquet."""
    fv_path = data_dir / "features" / "factor_values.parquet"
    if fv_path.exists():
        return pd.read_parquet(fv_path)
    return pd.DataFrame()


def load_bars(data_dir: Path) -> pd.DataFrame:
    """Load all bars from raw data."""
    all_bars = []
    raw_dir = data_dir / "raw"
    if raw_dir.exists():
        for parquet_file in raw_dir.rglob("bars.parquet"):
            df = pd.read_parquet(parquet_file)
            all_bars.append(df)
    if all_bars:
        return pd.concat(all_bars, ignore_index=True)
    return pd.DataFrame()


def load_labels(data_dir: Path) -> pd.DataFrame:
    """Load labels."""
    labels_path = data_dir / "labels" / "labels.parquet"
    if labels_path.exists():
        return pd.read_parquet(labels_path)
    return pd.DataFrame()


def bias_color(score: float) -> str:
    """Get color for bias score."""
    if score > 0.3:
        return "#00C853"  # strong green
    elif score > 0.1:
        return "#81C784"  # light green
    elif score > -0.1:
        return "#9E9E9E"  # grey
    elif score > -0.3:
        return "#EF9A9A"  # light red
    else:
        return "#FF1744"  # strong red


def bias_label_cn(score: float) -> str:
    """Get Chinese label for bias score."""
    if score > 0.3:
        return "强偏多"
    elif score > 0.1:
        return "温和偏多"
    elif score > -0.1:
        return "中性"
    elif score > -0.3:
        return "温和偏空"
    else:
        return "强偏空"


# ── Page Config ──
st.set_page_config(
    page_title="Bias Engine Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("Multi-Timeframe Bias Engine")
st.caption("STAR50 / HSI / NDX — D1 / W1 / M1 Bias Dashboard")

# ── Helper: stale data warning ──
def check_stale_data(predictions_df: pd.DataFrame):
    """Warn if latest prediction is more than 3 calendar days old."""
    if predictions_df.empty:
        return
    latest = predictions_df["as_of"].dropna().max()
    if latest:
        try:
            latest_date = pd.to_datetime(latest).date()
            if (dt.date.today() - latest_date).days > 3:
                st.warning(f"Data may be stale. Latest prediction date: {latest_date}")
        except Exception:
            pass

# ── Load Data ──
data_dir = project_root / "data"
predictions = load_predictions(data_dir)
bars = load_bars(data_dir)
factor_values = load_factor_values(data_dir)
labels = load_labels(data_dir)

if predictions.empty:
    st.warning("No predictions found. Run the pipeline first: `python run_pipeline.py`")
    st.stop()

check_stale_data(predictions)

# ── Sidebar ──
st.sidebar.header("Controls")

available_dates = sorted(predictions["as_of"].dropna().unique(), reverse=True)
if available_dates:
    selected_date = st.sidebar.selectbox("As of Date", available_dates, index=0)
else:
    selected_date = None

available_symbols = sorted(predictions["symbol"].unique())

# ── Current Bias Matrix (compact table) ──
st.header("Current Bias Matrix")

if selected_date:
    date_preds = predictions[predictions["as_of"] == selected_date]
else:
    date_preds = predictions

if not date_preds.empty:
    horizons = ["D1", "W1", "M1"]
    matrix_rows = []
    for symbol in available_symbols:
        row = {"Symbol": symbol}
        for h in horizons:
            mask = (date_preds["symbol"] == symbol) & (date_preds["horizon"] == h)
            subset = date_preds[mask]
            if not subset.empty:
                r = subset.iloc[0]
                row[f"{h}_score"] = r["bias_score"]
                row[f"{h}_label"] = r["label"]
            else:
                row[f"{h}_score"] = 0.0
                row[f"{h}_label"] = "neutral"
        matrix_rows.append(row)

    matrix_df = pd.DataFrame(matrix_rows)
    st.dataframe(matrix_df, use_container_width=True, hide_index=True)

# ── Bias Heatmap ──
st.header("Bias Heatmap")

if selected_date:
    date_preds = predictions[predictions["as_of"] == selected_date]
else:
    date_preds = predictions

if not date_preds.empty:
    # Build heatmap data
    horizons = ["D1", "W1", "M1"]
    heatmap_data = []
    for symbol in available_symbols:
        row = {"Symbol": symbol}
        for h in horizons:
            mask = (date_preds["symbol"] == symbol) & (date_preds["horizon"] == h)
            subset = date_preds[mask]
            if not subset.empty:
                row[h] = subset.iloc[0]["bias_score"]
            else:
                row[h] = 0.0
        heatmap_data.append(row)

    heatmap_df = pd.DataFrame(heatmap_data)

    # Display as styled table
    col1, col2, col3 = st.columns(3)
    for i, symbol in enumerate(available_symbols):
        cols = [col1, col2, col3]
        with cols[i % 3]:
            st.subheader(symbol)
            symbol_row = heatmap_df[heatmap_df["Symbol"] == symbol]
            if not symbol_row.empty:
                for h in horizons:
                    score = symbol_row.iloc[0][h]
                    label = bias_label_cn(score)
                    color = bias_color(score)
                    conf_mask = (date_preds["symbol"] == symbol) & (date_preds["horizon"] == h)
                    conf_subset = date_preds[conf_mask]
                    conf = conf_subset.iloc[0]["confidence"] if not conf_subset.empty else 0

                    st.markdown(
                        f"**{h}**: <span style='color:{color}; font-size:1.5em'>"
                        f"{score:+.2f}</span> {label} (置信度: {conf:.2f})",
                        unsafe_allow_html=True,
                    )
            st.divider()

# ── Symbol Detail ──
st.header("Symbol Detail")

selected_symbol = st.selectbox("Select Symbol", available_symbols)

if selected_symbol:
    # Get predictions for this symbol
    sym_preds = date_preds[date_preds["symbol"] == selected_symbol] if not date_preds.empty else pd.DataFrame()

    tab1, tab2, tab3, tab4 = st.tabs(["Bias Overview", "Price Chart", "Factor Contributions", "Factor Details"])

    with tab1:
        if not sym_preds.empty:
            for _, pred in sym_preds.iterrows():
                horizon = pred["horizon"]
                score = pred["bias_score"]
                label = pred["label"]
                conf = pred["confidence"]
                p_up = pred["p_up"]
                p_neutral = pred["p_neutral"]
                p_down = pred["p_down"]

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"### {horizon} Bias")
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=score,
                        domain={"x": [0, 1], "y": [0, 1]},
                        title={"text": f"{label_cn := bias_label_cn(score)}"},
                        gauge={
                            "axis": {"range": [-1, 1]},
                            "bar": {"color": bias_color(score)},
                            "steps": [
                                {"range": [-1, -0.3], "color": "#FFCDD2"},
                                {"range": [-0.3, 0.3], "color": "#E0E0E0"},
                                {"range": [0.3, 1], "color": "#C8E6C9"},
                            ],
                            "threshold": {
                                "line": {"color": "black", "width": 2},
                                "thickness": 0.75,
                                "value": score,
                            },
                        },
                    ))
                    fig.update_layout(height=250)
                    st.plotly_chart(fig, use_container_width=True)

                with col_b:
                    st.markdown(f"**Probabilities**")
                    prob_df = pd.DataFrame({
                        "Direction": ["Up", "Neutral", "Down"],
                        "Probability": [p_up, p_neutral, p_down],
                    })
                    fig_prob = go.Figure(data=[
                        go.Bar(
                            x=prob_df["Direction"],
                            y=prob_df["Probability"],
                            marker_color=["#4CAF50", "#9E9E9E", "#F44336"],
                        )
                    ])
                    fig_prob.update_layout(
                        yaxis_range=[0, 1],
                        height=250,
                        margin=dict(t=20, b=20),
                    )
                    st.plotly_chart(fig_prob, use_container_width=True)

                # Top factors
                top_pos = pred.get("top_positive_factors", [])
                top_neg = pred.get("top_negative_factors", [])
                if isinstance(top_pos, list) and top_pos:
                    st.markdown("**Top Positive Factors:**")
                    for f in top_pos:
                        st.markdown(f"- {f['name']}: {f['contribution']:+.4f} (value: {f['value']:.4f})")
                if isinstance(top_neg, list) and top_neg:
                    st.markdown("**Top Negative Factors:**")
                    for f in top_neg:
                        st.markdown(f"- {f['name']}: {f['contribution']:+.4f} (value: {f['value']:.4f})")
                st.divider()

    with tab2:
        # Price chart
        if not bars.empty:
            sym_bars = bars[bars["symbol"] == selected_symbol].copy()
            if not sym_bars.empty:
                sym_bars = sym_bars.sort_values("session_date")
                fig_price = go.Figure()
                fig_price.add_trace(go.Candlestick(
                    x=sym_bars["session_date"],
                    open=sym_bars["open"],
                    high=sym_bars["high"],
                    low=sym_bars["low"],
                    close=sym_bars["close"],
                    name=selected_symbol,
                ))
                fig_price.update_layout(
                    title=f"{selected_symbol} Price",
                    xaxis_title="Date",
                    yaxis_title="Price",
                    height=500,
                    xaxis_rangeslider_visible=False,
                )
                st.plotly_chart(fig_price, use_container_width=True)

                # Volume chart
                fig_vol = go.Figure()
                fig_vol.add_trace(go.Bar(
                    x=sym_bars["session_date"],
                    y=sym_bars["volume"],
                    name="Volume",
                    marker_color="steelblue",
                ))
                fig_vol.update_layout(
                    title="Volume",
                    height=200,
                    margin=dict(t=30, b=20),
                )
                st.plotly_chart(fig_vol, use_container_width=True)
        else:
            st.info("No price data available. Run data ingestion first.")

    with tab3:
        # Factor contributions bar chart
        if not sym_preds.empty:
            for _, pred in sym_preds.iterrows():
                horizon = pred["horizon"]
                top_pos = pred.get("top_positive_factors", [])
                top_neg = pred.get("top_negative_factors", [])

                if isinstance(top_pos, list) and isinstance(top_neg, list):
                    all_factors = top_pos + top_neg
                    if all_factors:
                        factor_names = [f["name"] for f in all_factors]
                        contributions = [f["contribution"] for f in all_factors]
                        colors = ["#4CAF50" if c > 0 else "#F44336" for c in contributions]

                        fig_factors = go.Figure(data=[
                            go.Bar(
                                x=factor_names,
                                y=contributions,
                                marker_color=colors,
                            )
                        ])
                        fig_factors.update_layout(
                            title=f"{horizon} Factor Contributions",
                            height=350,
                        )
                        st.plotly_chart(fig_factors, use_container_width=True)

    with tab4:
        # Raw factor values table
        if not factor_values.empty:
            sym_factors = factor_values[factor_values["symbol"] == selected_symbol]
            if not sym_factors.empty:
                latest_date = sym_factors["session_date"].max()
                latest_factors = sym_factors[sym_factors["session_date"] == latest_date]
                display_df = latest_factors[["factor_name", "value", "quality_score"]].copy()
                display_df = display_df.sort_values("value", ascending=False)
                display_df.columns = ["Factor", "Value", "Quality"]
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.info("No factor values available for this symbol.")
        else:
            st.info("No factor values computed yet.")

# ── History Tab ──
st.header("Bias History")

if not predictions.empty and available_symbols:
    hist_symbol = st.selectbox("History Symbol", available_symbols, key="hist_symbol")
    hist_horizon = st.selectbox("History Horizon", ["D1", "W1", "M1"], key="hist_horizon")

    hist_data = predictions[
        (predictions["symbol"] == hist_symbol) & (predictions["horizon"] == hist_horizon)
    ].copy()

    if not hist_data.empty:
        hist_data = hist_data.sort_values("as_of")

        fig_hist = go.Figure()
        fig_hist.add_trace(go.Scatter(
            x=hist_data["as_of"],
            y=hist_data["bias_score"],
            mode="lines+markers",
            name="Bias Score",
            line=dict(color="blue", width=2),
        ))

        # Add threshold lines
        fig_hist.add_hline(y=0.3, line_dash="dash", line_color="green", annotation_text="Bullish threshold")
        fig_hist.add_hline(y=-0.3, line_dash="dash", line_color="red", annotation_text="Bearish threshold")
        fig_hist.add_hline(y=0, line_dash="dot", line_color="grey")

        fig_hist.update_layout(
            title=f"{hist_symbol} {hist_horizon} Bias History",
            xaxis_title="Date",
            yaxis_title="Bias Score",
            yaxis_range=[-1.1, 1.1],
            height=400,
        )
        st.plotly_chart(fig_hist, use_container_width=True)

# ── Footer ──
st.divider()
st.caption(f"Data as of: {selected_date or 'N/A'} | Model: rule_model_v1 | Symbols: {', '.join(available_symbols)}")

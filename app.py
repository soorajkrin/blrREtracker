import re
from io import StringIO
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Bengaluru plot investment dashboard", layout="wide")

@st.cache_data
def load_data():
    areas = pd.read_csv("area_master.csv")
    dev = pd.read_csv("development_sources.csv")
    return areas, dev

areas, dev = load_data()

st.title("Bengaluru plotted-development investment dashboard")
st.caption("Directional research tool, not legal, valuation, or financial advice. Use this to shortlist corridors, then validate title, approvals, water, and transaction evidence before buying.")

with st.sidebar:
    st.header("Assumptions")
    horizon_year = st.slider("Projection year", 2027, 2035, 2030)
    water_cutoff = st.slider("Minimum water score", 1, 10, 5)
    max_price = st.number_input("Max current high price / sq ft", min_value=1000, max_value=30000, value=12000, step=500)
    risk_filter = st.multiselect("Exclude water-risk buckets", ["High", "Medium-high", "Medium", "Medium-low", "Low"], default=[])
    show_watchlist = st.checkbox("Show high water-risk corridors", value=True)

work = areas.copy()
# Weighted score: water is the lowest-common-denominator, so it has the highest weight.
work["affordability_score_10"] = (10 - ((work["current_high_psf"] - work["current_high_psf"].min()) / (work["current_high_psf"].max() - work["current_high_psf"].min()) * 7)).round(1)
work["investment_score_100"] = (
    work["water_score_10"] * 3.0
    + work["liquidity_score_10"] * 2.0
    + work["affordability_score_10"] * 1.5
    + work["base_cagr_pct"] * 1.6
).round(1)
work["current_mid_psf"] = ((work["current_low_psf"] + work["current_high_psf"]) / 2).round(0)
work["base_2030_mid_psf"] = ((work["base_2030_low_psf"] + work["base_2030_high_psf"]) / 2).round(0)
years_to_projection = max(horizon_year - 2026, 1)
work["projected_mid_psf"] = (work["current_mid_psf"] * ((1 + work["base_cagr_pct"] / 100) ** years_to_projection)).round(0)
work["projected_range"] = work.apply(lambda r: f"₹{int(r['base_2030_low_psf']):,}–₹{int(r['base_2030_high_psf']):,}", axis=1)
work["current_range"] = work.apply(lambda r: f"₹{int(r['current_low_psf']):,}–₹{int(r['current_high_psf']):,}", axis=1)

filtered = work[(work["water_score_10"] >= water_cutoff) & (work["current_high_psf"] <= max_price)]
if risk_filter:
    filtered = filtered[~filtered["water_risk"].isin(risk_filter)]
if not show_watchlist:
    filtered = filtered[filtered["water_risk"] != "High"]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Corridors shown", len(filtered))
m2.metric("Best score", int(filtered["investment_score_100"].max()) if len(filtered) else 0)
m3.metric("Median current ₹/sq ft", f"₹{int(filtered['current_mid_psf'].median()):,}" if len(filtered) else "—")
m4.metric("Median base CAGR", f"{filtered['base_cagr_pct'].median():.1f}%" if len(filtered) else "—")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Investment table", "Water first", "CAGR & projections", "Development tracker", "Area deep dives", "Refresh & sources"
])

with tab1:
    st.subheader("Corridor shortlist")
    cols = [
        "area", "corridor_zone", "current_range", "base_cagr_pct", "projected_range",
        "water_score_10", "water_risk", "liquidity_score_10", "investment_score_100", "investment_view"
    ]
    display = filtered[cols].sort_values(["investment_score_100", "water_score_10"], ascending=False)
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.download_button("Download filtered table as CSV", display.to_csv(index=False).encode("utf-8"), "bengaluru_filtered_corridors.csv")

with tab2:
    st.subheader("Water as the hard filter")
    st.write("The score intentionally penalizes water risk more heavily than price upside. A cheap plot in a tanker-dependent belt can become a liquidity trap.")
    fig = px.scatter(filtered, x="current_mid_psf", y="water_score_10", size="liquidity_score_10", hover_name="area", text="area", labels={"current_mid_psf":"Current midpoint ₹/sq ft", "water_score_10":"Water score"})
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(filtered[["area", "water_score_10", "water_risk", "key_checks"]].sort_values("water_score_10", ascending=False), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("CAGR scenarios and price projections")
    c = filtered[["area", "current_range", "bear_cagr_pct", "base_cagr_pct", "bull_cagr_pct", "projected_mid_psf", "projected_range"]].sort_values("base_cagr_pct", ascending=False)
    st.dataframe(c, use_container_width=True, hide_index=True)
    fig2 = px.bar(filtered.sort_values("base_cagr_pct"), x="base_cagr_pct", y="area", orientation="h", labels={"base_cagr_pct":"Base CAGR %", "area":"Area"})
    st.plotly_chart(fig2, use_container_width=True)

with tab4:
    st.subheader("Economic and infrastructure development tracker")
    st.dataframe(dev, use_container_width=True, hide_index=True)
    status_counts = dev["status"].value_counts().reset_index()
    status_counts.columns = ["status", "count"]
    st.plotly_chart(px.pie(status_counts, names="status", values="count"), use_container_width=True)

with tab5:
    st.subheader("Area-level thesis")
    selected = st.selectbox("Choose an area", work["area"].tolist())
    row = work[work["area"] == selected].iloc[0]
    left, right = st.columns([1, 1])
    with left:
        st.markdown(f"### {row['area']}")
        st.write(f"**Current plotted range:** {row['current_range']} / sq ft")
        st.write(f"**Base 2030 range:** {row['projected_range']} / sq ft")
        st.write(f"**Base CAGR:** {row['base_cagr_pct']}% | Bear: {row['bear_cagr_pct']}% | Bull: {row['bull_cagr_pct']}%")
        st.write(f"**Water risk:** {row['water_risk']} / score {row['water_score_10']}/10")
        st.write(f"**Investment view:** {row['investment_view']}")
    with right:
        st.write("**Live developments**")
        st.write(row["live_developments"])
        st.write("**In progress**")
        st.write(row["in_progress_developments"])
        st.write("**Planned future**")
        st.write(row["planned_future_developments"])
        st.write("**Economic engine**")
        st.write(row["economic_engine"])
        st.write("**Key checks before buying**")
        st.write(row["key_checks"])

with tab6:
    st.subheader("Refresh logic and source discipline")
    st.write("This version uses curated seed data plus source links. Public listing scraping is fragile because portals change markup and may restrict automated access. Treat scraped prices as listing indicators, not transaction evidence.")
    st.write("For a stronger refresh layer, replace the seed CSV with: verified transaction data, guidance values, RERA project exports, BMRDA/BIAAPA GIS layers, BWSSB/water board maps, and portal listing medians.")
    st.dataframe(dev[["development", "status", "source_url", "last_checked"]], use_container_width=True, hide_index=True)

st.divider()
st.caption("Model logic: Investment score weights water highest, then liquidity, affordability, and base CAGR. Edit area_master.csv to tune assumptions.")

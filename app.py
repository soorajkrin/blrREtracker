
import re, json, time
import pandas as pd
import streamlit as st
import plotly.express as px
from pathlib import Path
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Bengaluru plot investment dashboard", layout="wide")

DATA = Path(__file__).parent / "seed_areas.csv"

SOURCES = {
    "Devanahalli": ["https://www.99acres.com/property-rates-and-price-trends-in-devanahalli-bangalore-north-prffid", "https://housing.com/in/buy/bengaluru/devanahalli-gid/plots-fid/"],
    "Hoskote": ["https://www.99acres.com/residential-land-in-hoskote-bangalore-east-ffid", "https://housing.com/price-trends/property-rates-for-buy-in-hoskote_bengaluru-P702h78x2ynz7vvzq"],
    "Sarjapur-Attibele": ["https://housing.com/price-trends/property-rates-for-buy-in-sarjapura_attibele_road_bengaluru-P6qbbumduai2qbrcm", "https://www.magicbricks.com/residential-plots-land-for-sale-in-sarjapura-attibele-road-bangalore-pppfs"],
    "Kanakapura": ["https://www.99acres.com/residential-land-in-kanakapura-road-bangalore-south-ffid"],
    "Doddaballapur": ["https://housing.com/price-trends/property-rates-for-buy-in-doddaballapura_bengaluru-P4mg63hfly1n5wfo9", "https://www.magicbricks.com/residential-plots-land-for-sale-in-doddaballapur-main-road-bangalore-pppfs"],
    "Nelamangala": ["https://housing.com/price-trends/property-rates-for-buy-in-nelamangala_bengaluru-Pbi5wt608hzvcbwd", "https://www.magicbricks.com/residential-plots-land-for-sale-in-nelamangala-bangalore-pppfs"],
    "Bidadi": ["https://www.99acres.com/property-rates-and-price-trends-in-bidadi-bangalore-west-prffid", "https://housing.com/in/buy/bengaluru/bidadi-gid/plots-fid/"],
    "Jigani": ["https://housing.com/in/buy/bengaluru/jigani-gid/plots-fid/", "https://www.magicbricks.com/residential-plots-land-for-sale-in-jigani-bangalore-pppfs"],
    "Magadi Road": ["https://www.99acres.com/property-rates-and-price-trends-in-magadi-road-bangalore-west-prffid", "https://housing.com/price-trends/property-rates-for-buy-in-magadi_road_bengaluru-P1398zwejzmg9jkve"],
    "IVC Road": ["https://www.99acres.com/property-rates-and-price-trends-in-ivc-road-bangalore-north-prffid", "https://housing.com/price-trends/property-rates-for-buy-in-ivc_road_bengaluru-P5sf8v3t56n5xrjjn"],
}

def extract_prices(text):
    text = text.replace(",", "")
    vals = []
    # rupee price per sqft patterns
    for m in re.finditer(r"(?:Rs\.?|₹)\s*([0-9]{3,6})(?:\s*[-–]\s*(?:Rs\.?|₹)?\s*([0-9]{3,6}))?\s*(?:per\s*)?(?:sq\.?\s*ft|sqft|sft)", text, flags=re.I):
        vals.append(int(m.group(1)))
        if m.group(2):
            vals.append(int(m.group(2)))
    return [v for v in vals if 300 <= v <= 50000]

@st.cache_data(ttl=24*60*60)
def fetch_source_prices():
    rows = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for market, urls in SOURCES.items():
        for url in urls:
            try:
                r = requests.get(url, headers=headers, timeout=12)
                soup = BeautifulSoup(r.text, "html.parser")
                text = soup.get_text(" ", strip=True)
                vals = extract_prices(text)
                rows.append({
                    "market": market,
                    "source_url": url,
                    "status": r.status_code,
                    "min_detected": min(vals) if vals else None,
                    "max_detected": max(vals) if vals else None,
                    "sample_count": len(vals),
                    "fetched_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
                })
            except Exception as e:
                rows.append({"market": market, "source_url": url, "status": "ERR", "min_detected": None, "max_detected": None, "sample_count": 0, "fetched_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")})
            time.sleep(0.5)
    return pd.DataFrame(rows)

st.title("Bengaluru plotted development investment dashboard")
st.caption("Use this as a screener, not a buy/sell recommendation. Listing prices are noisy; legal approval, water, and access checks outrank headline appreciation.")

df = pd.read_csv(DATA)

with st.sidebar:
    st.header("Scoring assumptions")
    water_penalty = st.slider("Water risk penalty strength", 0, 25, 15)
    min_score = st.slider("Minimum score", 0, 100, 70)
    budget = st.number_input("Max current price/sq ft you are comfortable with", value=8000, step=500)
    show_refresh = st.checkbox("Show live source refresh panel", value=True)

def water_numeric(w):
    if "High risk" in w and "Medium" not in w:
        return 3
    if "Medium-High" in w:
        return 2
    if "Medium" in w:
        return 1
    return 0

df["water_risk_level"] = df["water"].apply(water_numeric)
df["adjusted_score"] = df["score"] - (df["water_risk_level"] * water_penalty / 3)
df["mid_price"] = (df["current_min"] + df["current_max"]) / 2
df["pred_mid_3y"] = (df["pred_3y_min"] + df["pred_3y_max"]) / 2
df["implied_3y_upside_pct"] = ((df["pred_mid_3y"] / df["mid_price"]) - 1) * 100

filtered = df[(df["adjusted_score"] >= min_score) & (df["current_min"] <= budget)].sort_values("adjusted_score", ascending=False)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Markets tracked", len(df))
c2.metric("Passing filters", len(filtered))
c3.metric("Best adjusted score", f"{filtered['adjusted_score'].max():.1f}" if len(filtered) else "—")
c4.metric("Median current mid-price", f"₹{df['mid_price'].median():,.0f}/sq ft")

st.subheader("Shortlist by adjusted score")
st.dataframe(filtered[["area","current_min","current_max","pred_3y_min","pred_3y_max","implied_3y_upside_pct","water","adjusted_score","econ","infra","watch"]], use_container_width=True)

st.subheader("Price and upside view")
fig = px.scatter(df, x="mid_price", y="adjusted_score", size="implied_3y_upside_pct", hover_name="area", hover_data=["water","current_min","current_max","pred_3y_min","pred_3y_max"])
st.plotly_chart(fig, use_container_width=True)

st.subheader("Water-first filter")
st.write("Reject or heavily discount any layout that cannot prove a credible water plan: piped supply timeline, functioning borewell yield, recharge structures, STP/reuse plan, and non-dependence on tankers.")
st.dataframe(df[["area","water","watch"]].sort_values(["water","area"]), use_container_width=True)

if show_refresh:
    st.subheader("Source refresh")
    st.write("Click refresh to scrape public listing/price pages. Some portals block scraping or change markup, so use this as an alert layer, not the final price source.")
    if st.button("Refresh public source prices"):
        st.cache_data.clear()
    src = fetch_source_prices()
    st.dataframe(src, use_container_width=True)
    st.download_button("Download refreshed source snapshot", src.to_csv(index=False), file_name="refreshed_source_prices.csv")

st.subheader("Due diligence gate")
st.markdown("""
Before any site visit or token payment:
1. Verify DC conversion / NA status, layout approval authority, e-khata, title chain, encumbrance certificate, RERA where applicable.
2. Check whether the land is green belt, lake-buffer, rajakaluve-buffer, forest-buffer, acquisition-notified, or litigation-prone.
3. Ask for water source proof, not brochure claims: borewell yield, piped-water timeline, recharge structures, STP/reuse, tanker history.
4. Visit during peak traffic and dry season.
5. Compare asking price with three recent transactions, not only listings.
""")

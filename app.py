
import os
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="India plot investment dashboard", layout="wide")

@st.cache_data
def load_data():
    cities = pd.read_csv("city_master.csv")
    dev = pd.read_csv("development_sources.csv")
    guidance = pd.read_csv("guidance_value_overrides.csv") if os.path.exists("guidance_value_overrides.csv") else pd.DataFrame()
    tx = pd.read_csv("transaction_evidence.csv") if os.path.exists("transaction_evidence.csv") else pd.DataFrame()
    registry = pd.read_csv("data_sources_registry.csv") if os.path.exists("data_sources_registry.csv") else pd.DataFrame()
    official_registry = pd.read_csv("official_state_source_registry.csv") if os.path.exists("official_state_source_registry.csv") else pd.DataFrame()
    extraction_tracker = pd.read_csv("state_by_state_extraction_tracker.csv") if os.path.exists("state_by_state_extraction_tracker.csv") else pd.DataFrame()
    return cities, dev, guidance, tx, registry, official_registry, extraction_tracker

cities, dev, guidance, tx, registry, official_registry, extraction_tracker = load_data()

st.title("India plotted-development investment dashboard")
st.caption("Water-first screening + evidence layer. Seed values are directional until replaced by guidance values, sale-deed evidence, RERA/local authority records, and dated listing samples.")

work = cities.copy()
# Optional guidance override aggregation
if not guidance.empty:
    g = guidance.dropna(subset=["state_ut","city_town"]).copy()
    g_agg = g.groupby(["state_ut","city_town"], as_index=False).agg(
        guidance_low_psf=("guidance_low_psf","median"),
        guidance_high_psf=("guidance_high_psf","median"),
        guidance_sources=("source_url","count"),
        latest_guidance_date=("effective_date","max")
    )
    work = work.merge(g_agg, on=["state_ut","city_town"], how="left")
else:
    work["guidance_low_psf"] = pd.NA
    work["guidance_high_psf"] = pd.NA
    work["guidance_sources"] = 0
    work["latest_guidance_date"] = pd.NA

# Optional transaction/listing evidence aggregation
if not tx.empty:
    t = tx.dropna(subset=["state_ut","city_town"]).copy()
    t_agg = t.groupby(["state_ut","city_town"], as_index=False).agg(
        evidence_low_psf=("observed_low_psf","median"),
        evidence_high_psf=("observed_high_psf","median"),
        evidence_count=("source_url","count"),
        evidence_confidence=("confidence_1_5","mean"),
        latest_evidence_date=("transaction_or_listing_date","max")
    )
    work = work.merge(t_agg, on=["state_ut","city_town"], how="left")
else:
    work["evidence_low_psf"] = pd.NA
    work["evidence_high_psf"] = pd.NA
    work["evidence_count"] = 0
    work["evidence_confidence"] = 0
    work["latest_evidence_date"] = pd.NA

# Verified / evidence-adjusted price fields. Priority: transaction/listing evidence > guidance > seed model.
work["adjusted_low_psf"] = work["evidence_low_psf"].fillna(work["guidance_low_psf"]).fillna(work["current_low_psf"])
work["adjusted_high_psf"] = work["evidence_high_psf"].fillna(work["guidance_high_psf"]).fillna(work["current_high_psf"])
work["price_basis"] = "Seed model"
work.loc[work["guidance_low_psf"].notna(), "price_basis"] = "Guidance value"
work.loc[work["evidence_low_psf"].notna(), "price_basis"] = "Market evidence"

work["current_mid_psf"] = ((work["adjusted_low_psf"] + work["adjusted_high_psf"]) / 2).round(0)
work["base_2030_low_psf"] = (work["adjusted_low_psf"] * ((1 + work["base_cagr_pct"]/100) ** 5)).round(0)
work["base_2030_high_psf"] = (work["adjusted_high_psf"] * ((1 + work["base_cagr_pct"]/100) ** 5)).round(0)
work["base_2030_mid_psf"] = ((work["base_2030_low_psf"] + work["base_2030_high_psf"]) / 2).round(0)
work["current_range"] = work.apply(lambda r: f"₹{int(r['adjusted_low_psf']):,}–₹{int(r['adjusted_high_psf']):,}", axis=1)
work["projected_range_2030"] = work.apply(lambda r: f"₹{int(r['base_2030_low_psf']):,}–₹{int(r['base_2030_high_psf']):,}", axis=1)

price_norm = (work["adjusted_high_psf"] - work["adjusted_high_psf"].min()) / max(1, (work["adjusted_high_psf"].max() - work["adjusted_high_psf"].min()))
work["affordability_score_10"] = (10 - price_norm * 7).round(1)
work["evidence_score_10"] = (work["evidence_count"].fillna(0).clip(0,5) * 1.2 + work["guidance_sources"].fillna(0).clip(0,3) * 0.9 + work["evidence_confidence"].fillna(0)).clip(0,10).round(1)
work["investment_score_100"] = (work["water_score_10"]*2.7 + work["affordability_score_10"]*1.3 + work["base_cagr_pct"]*1.4 + (11-work["rank_in_state"])*0.6 + work["evidence_score_10"]*1.2).round(1)

with st.sidebar:
    st.header("Filters")
    selected_states = st.multiselect("State / UT", sorted(work["state_ut"].unique()), default=["Karnataka","Maharashtra","Tamil Nadu","Telangana","Gujarat"])
    tiers = st.multiselect("Market tier", sorted(work["market_tier"].unique()), default=sorted(work["market_tier"].unique()))
    water_cutoff = st.slider("Minimum water score", 1, 10, 5)
    evidence_cutoff = st.slider("Minimum evidence score", 0, 10, 0)
    basis = st.multiselect("Price basis", sorted(work["price_basis"].unique()), default=sorted(work["price_basis"].unique()))
    max_price = st.number_input("Max current high price / sq ft", min_value=500, max_value=50000, value=15000, step=500)
    top_n = st.slider("Show top N per selected state/UT", 1, 10, 10)

filtered = work[(work["state_ut"].isin(selected_states)) & (work["market_tier"].isin(tiers)) & (work["water_score_10"] >= water_cutoff) & (work["evidence_score_10"] >= evidence_cutoff) & (work["price_basis"].isin(basis)) & (work["adjusted_high_psf"] <= max_price) & (work["rank_in_state"] <= top_n)]

m1,m2,m3,m4,m5 = st.columns(5)
m1.metric("Markets shown", len(filtered))
m2.metric("States/UTs", filtered["state_ut"].nunique() if len(filtered) else 0)
m3.metric("Median current ₹/sq ft", f"₹{int(filtered['current_mid_psf'].median()):,}" if len(filtered) else "—")
m4.metric("Median base CAGR", f"{filtered['base_cagr_pct'].median():.1f}%" if len(filtered) else "—")
m5.metric("Median evidence score", f"{filtered['evidence_score_10'].median():.1f}/10" if len(filtered) else "—")

tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8,tab9 = st.tabs(["India screener","Evidence-adjusted pricing","State view","Water-first map","CAGR projections","Development tracker","Market deep dive","Data refresh centre","Official data pipeline"])

with tab1:
    st.subheader("Comparable city/town screener")
    cols=["state_ut","rank_in_state","city_town","market_tier","current_range","price_basis","evidence_score_10","base_cagr_pct","projected_range_2030","water_score_10","water_risk","investment_score_100","investment_view"]
    st.dataframe(filtered[cols].sort_values(["investment_score_100","water_score_10"], ascending=False), use_container_width=True, hide_index=True)
    st.download_button("Download filtered CSV", filtered[cols].to_csv(index=False).encode("utf-8"), "india_plot_screener_filtered.csv")

with tab2:
    st.subheader("Guidance value + transaction/listing evidence layer")
    st.write("Update `guidance_value_overrides.csv` and `transaction_evidence.csv` in GitHub. The app automatically gives priority to market evidence, then guidance value, then the seed model.")
    cols=["state_ut","city_town","current_range","price_basis","guidance_low_psf","guidance_high_psf","guidance_sources","evidence_low_psf","evidence_high_psf","evidence_count","evidence_confidence","latest_evidence_date","evidence_score_10"]
    st.dataframe(filtered[cols].sort_values(["evidence_score_10","state_ut"], ascending=[False,True]), use_container_width=True, hide_index=True)
    st.download_button("Download guidance template", guidance.to_csv(index=False).encode("utf-8"), "guidance_value_overrides.csv")
    st.download_button("Download transaction evidence template", tx.to_csv(index=False).encode("utf-8"), "transaction_evidence.csv")

with tab3:
    st.subheader("State/UT comparison")
    summary = filtered.groupby("state_ut").agg(markets=("city_town","count"), median_price_psf=("current_mid_psf","median"), median_cagr=("base_cagr_pct","median"), median_water=("water_score_10","median"), median_evidence=("evidence_score_10","median"), best_score=("investment_score_100","max")).reset_index()
    st.dataframe(summary.sort_values("best_score", ascending=False), use_container_width=True, hide_index=True)
    if len(summary):
        st.plotly_chart(px.bar(summary.sort_values("best_score"), x="best_score", y="state_ut", orientation="h", labels={"best_score":"Best investment score","state_ut":"State / UT"}), use_container_width=True)

with tab4:
    st.subheader("Water is the lowest-common-denominator")
    st.write("The model gives water the highest weight. A cheap market with poor water security is intentionally penalized.")
    if len(filtered):
        st.plotly_chart(px.scatter(filtered, x="current_mid_psf", y="water_score_10", size="investment_score_100", color="state_ut", hover_name="city_town", labels={"current_mid_psf":"Current midpoint ₹/sq ft","water_score_10":"Water score"}), use_container_width=True)
    st.dataframe(filtered[["state_ut","city_town","water_score_10","water_risk","key_checks"]].sort_values(["water_score_10","state_ut"], ascending=[False,True]), use_container_width=True, hide_index=True)

with tab5:
    st.subheader("CAGR and 2030 scenario ranges")
    cols=["state_ut","city_town","current_range","price_basis","bear_cagr_pct","base_cagr_pct","bull_cagr_pct","projected_range_2030"]
    st.dataframe(filtered[cols].sort_values("base_cagr_pct", ascending=False), use_container_width=True, hide_index=True)
    if len(filtered):
        top=filtered.sort_values("base_cagr_pct", ascending=False).head(40)
        st.plotly_chart(px.bar(top.sort_values("base_cagr_pct"), x="base_cagr_pct", y="city_town", color="state_ut", orientation="h"), use_container_width=True)

with tab6:
    st.subheader("Economic and infrastructure development tracker")
    st.dataframe(dev[dev["state_ut"].isin(selected_states)] if not dev.empty else dev, use_container_width=True, hide_index=True)

with tab7:
    st.subheader("Market deep dive")
    if len(filtered):
        pick = st.selectbox("Choose a city/town", filtered.sort_values(["state_ut","rank_in_state"])["state_ut"].str.cat(filtered["city_town"], sep=" — ").tolist())
        st_name, city = pick.split(" — ",1)
        row = work[(work["state_ut"]==st_name)&(work["city_town"]==city)].iloc[0]
        left,right=st.columns(2)
        with left:
            st.metric("Current range / sq ft", row["current_range"])
            st.metric("2030 base range / sq ft", row["projected_range_2030"])
            st.metric("Base CAGR", f"{row['base_cagr_pct']}%")
            st.metric("Price basis", row["price_basis"])
        with right:
            st.metric("Water score", f"{row['water_score_10']}/10")
            st.metric("Evidence score", f"{row['evidence_score_10']}/10")
            st.metric("Investment score", f"{row['investment_score_100']}/100")
        st.markdown("**Economic engine**")
        st.write(row["economic_engine"])
        st.markdown("**Infrastructure drivers**")
        st.write(row["infra_drivers"])
        st.markdown("**Live / in-progress / planned development**")
        st.write("Live: " + row["live_developments"])
        st.write("In progress: " + row["in_progress_developments"])
        st.write("Planned: " + row["planned_future_developments"])
        st.markdown("**Due diligence checks**")
        st.write(row["key_checks"])
        st.markdown("**Evidence records for this market**")
        if not tx.empty:
            st.dataframe(tx[(tx["state_ut"]==st_name)&(tx["city_town"]==city)], use_container_width=True, hide_index=True)
        else:
            st.info("No transaction/listing evidence uploaded yet.")

with tab8:
    st.subheader("Data refresh centre")
    st.write("This version bakes in the verified-data workflow. It does not pretend to have official verified data for every Indian market by default.")
    st.markdown("""
**Recommended monthly refresh workflow**
1. Pull official guidance values from the state registration/stamps department and update `guidance_value_overrides.csv`.
2. Add sale-deed evidence where available; otherwise add dated listing samples into `transaction_evidence.csv`.
3. Use RERA/local authority records to validate plotted-layout approvals.
4. Update water-source evidence from CGWB, municipal boards, Jal Board / BWSSB equivalents, and local development authority plans.
5. Update live / in-progress / planned infra using official NHAI, metro, airport, industrial authority, and master-plan sources.
6. Commit the CSV changes to GitHub. Streamlit Cloud will redeploy automatically.
""")
    st.markdown("**Source registry**")
    st.dataframe(registry, use_container_width=True, hide_index=True)


with tab9:
    st.subheader("Official state-by-state data pipeline")
    st.write("Use this tab to move the model from seed assumptions to official evidence. Guidance/circle/collector values, RERA checks, groundwater status and infrastructure status should be extracted state by state.")
    if not official_registry.empty:
        st.markdown("**Official source registry**")
        st.dataframe(official_registry[official_registry["state_ut"].isin(selected_states) | (official_registry["state_ut"]=="All India")], use_container_width=True, hide_index=True)
        st.download_button("Download official source registry", official_registry.to_csv(index=False).encode("utf-8"), "official_state_source_registry.csv")
    if not extraction_tracker.empty:
        st.markdown("**Extraction tracker**")
        tr = extraction_tracker[extraction_tracker["state_ut"].isin(selected_states)]
        st.dataframe(tr, use_container_width=True, hide_index=True)
        st.download_button("Download extraction tracker", tr.to_csv(index=False).encode("utf-8"), "state_by_state_extraction_tracker_filtered.csv")
    st.markdown("**How to use this practically**")
    st.write("Start with the states you are actually willing to invest in. For each shortlisted city/town, capture the official guidance/circle/collector value, add 3–5 transaction or listing evidence records, check RERA/layout approval, and validate groundwater/municipal supply. The dashboard will then rank markets using evidence instead of broad seed assumptions.")

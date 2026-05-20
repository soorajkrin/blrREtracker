import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px
from modules.scoring_engine import recompute_scores
from modules.report_engine import generate_report
from modules.area_refresh_engine import rebuild_area_universe

ROOT=Path(__file__).parent
DATA=ROOT/'data'
st.set_page_config(page_title='India Plot Investment Dashboard v10', layout='wide')

@st.cache_data(ttl=300)
def load_data():
    df=pd.read_csv(DATA/'current_area_universe.csv')
    df=recompute_scores(df)
    return df

st.title('India plot investment dashboard v10')
st.caption('Dynamic areas, dynamic reports, evidence hierarchy, and source-aware refresh. Treat this as a screener, not a substitute for legal/title/water due diligence.')

df=load_data()
with st.sidebar:
    st.header('Filters')
    states=sorted(df['state_ut'].dropna().unique())
    state=st.selectbox('State/UT', states, index=states.index('Karnataka') if 'Karnataka' in states else 0)
    cities=sorted(df[df.state_ut==state]['city_town'].dropna().unique())
    city=st.selectbox('City/Town', cities, index=cities.index('Bengaluru') if 'Bengaluru' in cities else 0)
    min_water=st.slider('Minimum water score', 0, 100, 0)
    confidence=st.multiselect('Confidence grades', ['A','B','C','D','E'], default=['A','B','C','D','E'])
    st.divider()
    st.subheader('Refresh controls')
    scope=st.radio('Refresh scope', ['Selected city only','Selected state','All India'], index=0)
    live=st.checkbox('Try live source checks where configured', value=True)
    if st.button('Refresh area universe and reports', type='primary'):
        with st.spinner('Refreshing area universe, source status and report datapoints...'):
            if scope=='Selected city only':
                _, log=rebuild_area_universe(state=state, city=city, use_live_sources=live)
            elif scope=='Selected state':
                _, log=rebuild_area_universe(state=state, use_live_sources=live)
            else:
                _, log=rebuild_area_universe(use_live_sources=live)
            st.cache_data.clear()
            st.success('Refresh complete. Tables and reports now use the refreshed area universe.')
            st.dataframe(log, use_container_width=True)
            st.rerun()

view=df[(df.state_ut==state)&(df.city_town==city)&(df.water_score>=min_water)&(df.confidence_grade.isin(confidence))].copy()
view=view.sort_values(['overall_score','water_score','liquidity_score'], ascending=False)

last_refresh = view['last_refreshed_at'].dropna().astype(str).max() if not view.empty else 'Not available'
st.info(f'Current view: {state} → {city}. Latest refresh timestamp in this view: {last_refresh}')

tab1,tab2,tab3,tab4,tab5=st.tabs(['Area ranking','Water-first view','CAGR and projections','Dynamic report','Refresh logs'])

with tab1:
    st.subheader('Top areas/corridors')
    cols=['rank_in_city','area_name','area_basis','overall_score','confidence_grade','price_low_psf','price_high_psf','base_cagr_pct','water_score','liquidity_score','developer_score','source_type','verification_status']
    st.dataframe(view[cols], use_container_width=True, hide_index=True)
    csv=view.to_csv(index=False).encode('utf-8')
    st.download_button('Download current view CSV', csv, file_name=f'{state}_{city}_areas.csv'.replace(' ','_'))

with tab2:
    st.subheader('Water as the lowest common denominator')
    water_cols=['area_name','water_score','water_risk_label','overall_score','price_low_psf','price_high_psf','risk_1','source_type','confidence_grade']
    st.dataframe(view[water_cols].sort_values('water_score', ascending=False), use_container_width=True, hide_index=True)
    if not view.empty:
        fig=px.bar(view.sort_values('water_score'), x='water_score', y='area_name', orientation='h', title='Water score by area')
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader('CAGR scenarios and 2030 projections')
    proj_cols=['area_name','price_low_psf','price_high_psf','bear_cagr_pct','base_cagr_pct','bull_cagr_pct','projection_2030_low','projection_2030_high','confidence_grade']
    st.dataframe(view[proj_cols], use_container_width=True, hide_index=True)

with tab4:
    st.subheader('On-demand area report')
    if view.empty:
        st.warning('No areas match the filters.')
    else:
        area=st.selectbox('Select area', view['area_name'].tolist())
        row=view[view.area_name==area].iloc[0].to_dict()
        report=generate_report(row)
        st.markdown(report)
        st.download_button('Download this report as Markdown', report.encode('utf-8'), file_name=f"{row['area_id']}_report.md")

with tab5:
    st.subheader('Refresh logs and source status')
    log_path=DATA/'refresh_log.csv'
    if log_path.exists():
        st.dataframe(pd.read_csv(log_path).tail(200), use_container_width=True, hide_index=True)
    else:
        st.write('No refresh log yet.')
    raw_path=DATA/'last_discovery_raw.csv'
    if raw_path.exists():
        st.markdown('Latest raw discovery output')
        st.dataframe(pd.read_csv(raw_path).tail(200), use_container_width=True, hide_index=True)

st.divider()
st.caption('No source = no verified claim. GOV/REG data outranks 3PD. Portal data is treated as asking-price evidence unless transaction proof is available.')

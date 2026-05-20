
INDIA PLOTTED-DEVELOPMENT DASHBOARD V2 — VERIFIED DATA LAYER

Open online using Streamlit Community Cloud:
1. Create or open your GitHub repo.
2. Upload all files from this folder.
3. In Streamlit Cloud, create/update the app.
4. Main file path: app.py
5. Deploy.

What is new in V2:
- Evidence-adjusted pricing layer
- Guidance value override file
- Transaction/listing evidence file
- Evidence score per market
- Price basis tag: Seed model / Guidance value / Market evidence
- Source registry for monthly refresh workflow
- Data refresh centre inside the dashboard

Files:
- app.py: dashboard application
- city_master.csv: seed data for top 10 cities/towns across each Indian state and UT
- development_sources.csv: economic/infrastructure tracker
- guidance_value_overrides.csv: add official guidance value data here
- transaction_evidence.csv: add sale deed / listing samples here
- data_sources_registry.csv: source checklist for guidance, sale deeds, RERA, water and infra
- requirements.txt: Python packages for Streamlit Cloud

How the price hierarchy works:
1. If transaction/listing evidence exists, the dashboard uses that as the current market range.
2. If not, but guidance value exists, it uses the guidance-value range.
3. If neither exists, it falls back to the seed model.

Important:
This version includes the workflow and data model needed to replace assumptions with evidence. It does not include verified official values for every market in India by default. Those must be added source-by-source because guidance values, sale deed access, RERA data, and water/infra records vary by state.


V3 official-data pipeline added
-------------------------------
This version adds a state-by-state verification workflow instead of pretending that broad India-wide seed prices are official.

New files:
- official_state_source_registry.csv: official source pointers for guidance/circle/collector values, RERA, groundwater and infra.
- state_by_state_extraction_tracker.csv: extraction status for every city/town in the dashboard.
- guidance_value_official_template.csv: structured template for official guidance/circle/collector value capture.
- rera_layout_validation_template.csv: structured template for plotted-layout/RERA validation.
- water_validation_template.csv: structured template for groundwater and municipal/surface-water validation.

Recommended use:
1. Prioritize one state at a time.
2. Pull official values from the state stamp/registration portal.
3. Add values into guidance_value_overrides.csv or guidance_value_official_template.csv.
4. Add RERA/layout checks and water checks.
5. Commit the updated CSVs to GitHub and redeploy.

Important: guidance values are not the same as market transaction prices. Treat them as a floor/reference for valuation, stamp duty, and outlier detection.

India Plot Investment Dashboard v10 - Dynamic Area Refresh

What this version fixes
- No 1,800 static report files.
- Reports are generated on demand from datasets + template.
- The Refresh button can now rebuild the top areas per selected city/town using an area-discovery layer.
- If live discovery sources fail, the app falls back to prior verified areas, then seed areas, and clearly marks the basis.

How to deploy on Streamlit Community Cloud
1. Unzip this folder.
2. Upload the files/folders to a GitHub repository.
3. In Streamlit Community Cloud, select app.py as the main file.
4. Deploy.

How dynamic refresh works
- Refresh checks configured sources in data/area_discovery_sources.csv.
- It attempts to discover candidate area names from source pages where allowed/reachable.
- It merges those candidates with imported evidence and seed areas.
- It ranks candidates using evidence quality, water score, development score, and source freshness.
- It rewrites data/current_area_universe.csv.
- Dashboard tables and written area reports immediately use the refreshed area universe.

Important limitations
- Many Indian property portals and government portals restrict scraping, require logins, or render data with JavaScript.
- The app does not bypass restrictions.
- When a source is unavailable, it keeps the last known area universe and marks the datapoints as stale/seed/model/3PD.
- For investment decisions, verify title, approvals, water, access roads, RERA/layout approval, and transaction evidence manually.

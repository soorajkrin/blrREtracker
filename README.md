
# Bengaluru plotted development investment dashboard

## What this is
A local Streamlit dashboard to screen Bengaluru plotted-development corridors using:
- seeded market price ranges,
- 3-year scenario estimates,
- economic/infrastructure thesis,
- water-risk penalty,
- public-source refresh panel.

## How to run
1. Install Python 3.10+
2. Open a terminal in this folder
3. Run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## How refresh works
The dashboard has a "Refresh public source prices" button. It tries to scrape public listing and price-trend pages and extracts price-per-sq-ft text patterns.

Important: portals can block scraping or change page markup. Treat refresh output as an alert layer, not final investment-grade pricing.

## How to use
- Start with the adjusted score.
- Increase the water-risk penalty if you want a stricter screen.
- Reject any area/project where water supply is not defensible.
- Use the "watch" column to decide what to verify before site visits.

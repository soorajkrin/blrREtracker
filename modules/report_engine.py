from pathlib import Path
from .scoring_engine import compute_projection

TEMPLATE_PATH = Path(__file__).resolve().parents[1] / 'templates' / 'area_report_template.md'

def generate_report(row: dict) -> str:
    r = dict(row)
    low, high = compute_projection(r.get('price_low_psf',0), r.get('price_high_psf',0), r.get('base_cagr_pct',0))
    r.setdefault('projection_2030_low', low)
    r.setdefault('projection_2030_high', high)
    for k,v in list(r.items()):
        if v is None or str(v) == 'nan':
            r[k] = 'Not available'
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    return template.format(**r)

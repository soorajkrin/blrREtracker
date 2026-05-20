import pandas as pd
from datetime import datetime, timezone

SOURCE_WEIGHT = {
    'GOV': 1.00,
    'REG': 0.95,
    'INST': 0.88,
    '3PD-A': 0.78,
    '3PD-B': 0.62,
    '3PD-C': 0.48,
    'LOW-CONF': 0.25,
    'MODEL': 0.15,
}

def confidence_grade(source_type: str, reliability: float, age_days: int | None = None) -> str:
    w = SOURCE_WEIGHT.get(str(source_type), 0.15)
    score = reliability * w
    if age_days is not None and age_days > 365:
        score -= 10
    if score >= 85: return 'A'
    if score >= 70: return 'B'
    if score >= 55: return 'C'
    if score >= 35: return 'D'
    return 'E'

def compute_projection(low, high, cagr_pct, years=4):
    mult = (1 + float(cagr_pct)/100) ** years
    return round(float(low)*mult), round(float(high)*mult)

def recompute_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in ['water_score','development_score','liquidity_score','developer_score','base_cagr_pct','source_reliability']:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    df['overall_score'] = (
        0.24*df['water_score'] +
        0.20*df['development_score'] +
        0.18*df['liquidity_score'] +
        0.16*df['developer_score'] +
        0.22*(df['base_cagr_pct']*6)
    ).clip(0,100).round(0).astype(int)
    df['confidence_grade'] = df.apply(lambda r: confidence_grade(r.get('source_type','MODEL'), r.get('source_reliability',35)), axis=1)
    projs = df.apply(lambda r: compute_projection(r['price_low_psf'], r['price_high_psf'], r['base_cagr_pct']), axis=1)
    df['projection_2030_low'] = [p[0] for p in projs]
    df['projection_2030_high'] = [p[1] for p in projs]
    return df

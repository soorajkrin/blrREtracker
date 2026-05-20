import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from .scoring_engine import recompute_scores

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'

KEYWORDS = ['road','layout','nagar','extension','phase','corridor','airport','metro','industrial','township','highway','ring road','bypass','estate','sector']

def _now():
    return datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')

def _extract_candidates_from_html(html: str, city: str):
    soup = BeautifulSoup(html, 'html.parser')
    text = ' '.join(soup.get_text(' ').split())
    # Conservative heuristic: look around city mentions and known area keywords.
    # This is intentionally simple and transparent; serious deployments should add source-specific parsers.
    candidates = set()
    for kw in KEYWORDS:
        if kw.lower() in text.lower():
            candidates.add(f'{city} {kw.title()} Signal')
    return sorted(candidates)[:20]

def fetch_source_candidates(sources: pd.DataFrame, state=None, city=None, timeout=8):
    rows=[]
    filt=sources.copy()
    if state: filt=filt[filt['state_ut']==state]
    if city: filt=filt[filt['city_town']==city]
    for _,s in filt.iterrows():
        if str(s.get('enabled', True)).lower() not in ['true','1','yes']:
            continue
        url=str(s.get('source_url',''))
        try:
            res=requests.get(url, timeout=timeout, headers={'User-Agent':'Mozilla/5.0 compatible research dashboard'})
            ok=res.status_code==200 and 'text/html' in res.headers.get('content-type','text/html')
            candidates=_extract_candidates_from_html(res.text, s['city_town']) if ok else []
            status='reachable' if ok else f'failed_http_{res.status_code}'
        except Exception as e:
            candidates=[]; status=f'unavailable: {type(e).__name__}'
        for c in candidates:
            rows.append({'state_ut':s['state_ut'],'city_town':s['city_town'],'area_name':c,'candidate_basis':'discovered_from_source','source_name':s.get('source_name',''), 'source_type':s.get('source_type','3PD-C'),'source_url':url,'refresh_status':status})
        if not candidates:
            rows.append({'state_ut':s['state_ut'],'city_town':s['city_town'],'area_name':'','candidate_basis':'no_candidate_extracted','source_name':s.get('source_name',''), 'source_type':s.get('source_type','3PD-C'),'source_url':url,'refresh_status':status})
    return pd.DataFrame(rows)

def rebuild_area_universe(state=None, city=None, use_live_sources=True):
    seed=pd.read_csv(DATA/'seed_area_universe.csv')
    current=pd.read_csv(DATA/'current_area_universe.csv') if (DATA/'current_area_universe.csv').exists() else seed.copy()
    manual=pd.read_csv(DATA/'manual_area_candidates.csv') if (DATA/'manual_area_candidates.csv').exists() else pd.DataFrame()
    sources=pd.read_csv(DATA/'area_discovery_sources.csv') if (DATA/'area_discovery_sources.csv').exists() else pd.DataFrame()
    now=_now()
    discovered=pd.DataFrame()
    if use_live_sources and not sources.empty:
        discovered=fetch_source_candidates(sources, state=state, city=city)
    logs=[]
    out=current.copy()
    scope=seed.copy()
    if state: scope=scope[scope['state_ut']==state]
    if city: scope=scope[scope['city_town']==city]
    target_pairs=scope[['state_ut','city_town']].drop_duplicates()
    new_rows=[]
    for _,pair in target_pairs.iterrows():
        st,ct=pair['state_ut'],pair['city_town']
        city_seed=seed[(seed.state_ut==st)&(seed.city_town==ct)].copy()
        candidates=[]
        # discovered candidates with non-empty area names
        if not discovered.empty:
            d=discovered[(discovered.state_ut==st)&(discovered.city_town==ct)&(discovered.area_name.astype(str).str.len()>0)]
            candidates += d.to_dict('records')
        if not manual.empty:
            m=manual[(manual.state_ut==st)&(manual.city_town==ct)&(manual.area_name.astype(str).str.len()>0)]
            candidates += m.to_dict('records')
        if candidates:
            # start from seed metrics, replace names and source basis
            base_rows=city_seed.head(10).copy().reset_index(drop=True)
            unique=[]
            seen=set()
            for c in candidates:
                nm=str(c['area_name']).strip()
                if nm and nm.lower() not in seen:
                    unique.append(c); seen.add(nm.lower())
                if len(unique)>=10: break
            for i,cand in enumerate(unique):
                if i>=len(base_rows): break
                base_rows.loc[i,'area_name']=cand['area_name']
                base_rows.loc[i,'area_basis']='DYNAMIC_DISCOVERY' if cand.get('candidate_basis')=='discovered_from_source' else 'MANUAL_CANDIDATE'
                base_rows.loc[i,'source_type']=cand.get('source_type','3PD-C')
                base_rows.loc[i,'source_url']=cand.get('source_url','')
                base_rows.loc[i,'source_reliability']=55 if base_rows.loc[i,'source_type']=='3PD-C' else 65
                base_rows.loc[i,'verification_status']='area_discovered_needs_validation'
                base_rows.loc[i,'confidence_grade']='C'
                base_rows.loc[i,'investment_thesis']=f"{cand['area_name']} was added by the dynamic area-refresh layer. Validate price, title, water and approvals before investment use."
            city_final=base_rows
            logs.append({'state_ut':st,'city_town':ct,'refresh_status':'updated_from_candidates','candidate_count':len(candidates),'refreshed_at':now})
        else:
            city_final=city_seed.copy()
            city_final['area_basis']='SEED_FALLBACK_NO_DYNAMIC_CANDIDATES'
            logs.append({'state_ut':st,'city_town':ct,'refresh_status':'seed_fallback_no_candidates','candidate_count':0,'refreshed_at':now})
        city_final['last_refreshed_at']=now
        new_rows.append(city_final)
    refreshed_scope=pd.concat(new_rows, ignore_index=True) if new_rows else pd.DataFrame()
    # merge scope back into current universe
    if state or city:
        mask=pd.Series(False,index=out.index)
        if state: mask |= (out['state_ut']==state)
        if city and state: mask = (out['state_ut']==state)&(out['city_town']==city)
        elif city: mask |= (out['city_town']==city)
        out=out[~mask]
        out=pd.concat([out, refreshed_scope], ignore_index=True)
    else:
        out=refreshed_scope
    out=recompute_scores(out)
    out.to_csv(DATA/'current_area_universe.csv', index=False)
    logdf=pd.DataFrame(logs)
    existing=pd.read_csv(DATA/'refresh_log.csv') if (DATA/'refresh_log.csv').exists() else pd.DataFrame()
    pd.concat([existing,logdf], ignore_index=True).to_csv(DATA/'refresh_log.csv', index=False)
    if not discovered.empty:
        discovered.to_csv(DATA/'last_discovery_raw.csv', index=False)
    return out, logdf

"""Inclusive Pacific Search Console periods; conservative, deterministic analysis."""
from datetime import date,timedelta
import hashlib,math

def periods(as_of:date,lag_days:int=3):
    end=as_of-timedelta(days=lag_days);start=end-timedelta(days=6)
    return ({'start':start.isoformat(),'end':end.isoformat()}, {'start':(start-timedelta(days=7)).isoformat(),'end':(start-timedelta(days=1)).isoformat()})

def metrics(row):
    if row is None:return None
    out={k:row.get(k) for k in ('clicks','impressions','ctr','position')}
    if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<0 for v in out.values()):raise ValueError('invalid_metrics')
    if out['clicks']>out['impressions'] or out['ctr']>1:raise ValueError('invalid_metrics')
    return out

def compare_metrics(current,previous):
    if current is None or previous is None:return None
    c,p=metrics(current),metrics(previous)
    return {'clicksDelta':c['clicks']-p['clicks'],'clicksPct':((c['clicks']-p['clicks'])/p['clicks']*100) if p['clicks'] else None,'impressionsDelta':c['impressions']-p['impressions'],'ctrPoints':(c['ctr']-p['ctr'])*100,'positionImprovement':p['position']-c['position']}

def opportunities(pages,queries):
    tasks=[]
    for row in pages:
        m=metrics(row);target=row['keys'][0]
        if m['impressions']>=100 and 1<=m['position']<=15 and m['ctr']<.02:
            task_id=hashlib.sha256(('page_ctr_review:'+target).encode()).hexdigest()
            tasks.append({'id':task_id,'kind':'page_ctr_review','target':target,'title':'検索意図とタイトル・説明文の整合を確認','status':'todo','evidence':m,'automaticChange':False,'observationDays':28})
    return tasks[:20]

def growing_queries(current,previous):
    old={tuple(r['keys']):r for r in previous};result=[]
    for r in current:
        p=old.get(tuple(r['keys']))
        if p and r['impressions']>=50 and p['impressions']>=50 and r['clicks']>p['clicks']:
            result.append({'query':r['keys'][0],**compare_metrics(r,p),'current':metrics(r)})
    return sorted(result,key=lambda x:x['clicksDelta'],reverse=True)[:20]

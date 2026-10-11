"""Private fixed-host growth APIs; retain only aggregates for public weekly Markdown."""
import json,os,math
from urllib.parse import urlencode
from urllib.request import Request,build_opener,HTTPRedirectHandler
class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
BASE='https://unity-analytics.vercel.app/api/growth/'
STATUSES={'available','partial','unavailable','not_configured','invalid_configuration','storage_not_configured','migration_or_storage_unavailable','not_collected','enabled','disabled','active','partial_period','observation_in_progress','30_day_window_complete','retained','partial_retention','outside_retention'}
def safe_status(v):return v if v in STATUSES else 'unavailable'
def number(v):return v if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0 else None
def sanitize_growth(data):
 r={'status':safe_status(data.get('status')),'timezone':'UTC','instagram':None,'attribution':None}
 ig=data.get('instagram')
 if isinstance(ig,dict):r['instagram']={'status':safe_status(ig.get('status')),'metrics':{k:number(ig.get('metrics',{}).get(k)) for k in ('reach','views','total_interactions')}}
 a=data.get('attribution')
 if isinstance(a,dict):
  r['attribution']={'status':safe_status(a.get('status')),'confirmationStatus':safe_status(a.get('confirmationStatus')),'cohortMaturity':safe_status(a.get('cohortMaturity')),'retentionCoverage':safe_status(a.get('retentionCoverage')),'truncated':a.get('truncated') is True,'sources':[]}
  for row in (a.get('sources') or [])[:7]:
   if not isinstance(row,dict) or row.get('source') not in ('google','instagram','line','tunagate','direct','other','unknown'):continue
   r['attribution']['sources'].append({'source':row['source'],**{k:number(row.get(k)) for k in ('observedSessions','visits','registrationClicks','formViews','formSubmits','confirmedSessions','registrationRate')}})
 return r

def transport(method,url,body,token):
 # Endpoint is constructed internally; no redirect may forward the bearer.
 raw=json.dumps(body).encode() if body is not None else None
 with build_opener(NoRedirect()).open(Request(url,data=raw,method=method,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}),timeout=45) as response:
  content=response.read(131073)
  if len(content)>131072:raise ValueError('growth_response_too_large')
  return json.loads(content)

def read_growth(period,send=transport):
 token=os.environ.get('SEO_INGEST_TOKEN')
 if not token:return {'status':'not_configured','timezone':'UTC','instagram':None,'attribution':None}
 p={'from':period['start'],'to':period['end']};sync='unavailable'
 try:
  result=send('POST',BASE+'instagram',p,token);sync=safe_status(result.get('result',{}).get('status'))
 except Exception:pass
 try:
  result=send('GET',BASE+'report?'+urlencode(p),None,token);r=sanitize_growth(result.get('report',{}));r['instagramSyncStatus']=sync;return r
 except Exception:return {'status':'unavailable','timezone':'UTC','instagramSyncStatus':sync,'instagram':None,'attribution':None}

"""Google's read-only APIs. Never submit indexing or assume live inspection."""
from urllib.parse import quote,urlsplit,unquote
import time
SCOPES=['https://www.googleapis.com/auth/webmasters.readonly']
class ApiError(RuntimeError):pass

def authenticated_transport():
    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        credentials,_=google.auth.default(scopes=SCOPES)
    except Exception as e:raise ApiError('authentication_required') from e
    session=AuthorizedSession(credentials)
    def send(method,url,payload=None):
        for attempt in range(3):
            try:r=session.request(method,url,json=payload,timeout=30)
            except Exception as e:raise ApiError('google_connection_unavailable') from e
            if r.status_code in (429,500,502,503,504) and attempt<2:
                time.sleep(min(2**attempt,4));continue
            if r.status_code in (401,403):raise ApiError('google_permission_or_api_required')
            if not r.ok:raise ApiError('google_http_'+str(r.status_code))
            try:return r.json()
            except ValueError as e:raise ApiError('google_response_invalid') from e
        raise ApiError('google_unavailable')
    return send

class SearchConsole:
    def __init__(self,site_url,transport,row_limit=25000,max_rows=50000):
        if not site_url.startswith('https://') or not site_url.endswith('/'):raise ValueError('URL-prefix property required')
        self.site=site_url;self.send=transport;self.row_limit=row_limit;self.max_rows=max_rows
        self.base='https://www.googleapis.com/webmasters/v3/sites/'+quote(site_url,safe='')
    def sites(self):return self.send('GET','https://www.googleapis.com/webmasters/v3/sites',None)
    def sitemaps(self):return self.send('GET',self.base+'/sitemaps',None)
    def _request(self,period,dimensions,start=0):
        return self.send('POST',self.base+'/searchAnalytics/query',{'startDate':period['start'],'endDate':period['end'],'dimensions':dimensions,'type':'web','dataState':'final','rowLimit':self.row_limit,'startRow':start,'aggregationType':'byProperty' if 'page' not in dimensions else 'byPage'})
    def totals(self,period):
        r=self._request(period,[]);rows=r.get('rows',[])
        return {k:rows[0][k] for k in ('clicks','impressions','ctr','position')} if rows else {'clicks':0,'impressions':0,'ctr':0,'position':0}
    def performance(self,period,dimensions):
        rows=[];truncated=False
        while len(rows)<self.max_rows:
            chunk=self._request(period,dimensions,len(rows)).get('rows',[])
            rows.extend(chunk[:self.max_rows-len(rows)])
            if len(chunk)<self.row_limit:break
            if len(rows)>=self.max_rows:truncated=True
        return {'rows':rows,'truncated':truncated,'coverage':'API top rows; anonymized queries omitted; not a complete keyword inventory'}
    def inspect(self,url):
        p,s=urlsplit(url),urlsplit(self.site)
        if p.scheme!=s.scheme or p.netloc!=s.netloc or not p.path.startswith(s.path) or any(x in ('.','..') for x in unquote(p.path).replace('\\','/').split('/')):raise ValueError('inspection_url_outside_property')
        data=self.send('POST','https://searchconsole.googleapis.com/v1/urlInspection/index:inspect',{'inspectionUrl':url,'siteUrl':self.site,'languageCode':'ja-JP'})
        index=data.get('inspectionResult',{}).get('indexStatusResult',{})
        return {'url':url,'status':'available','verdict':index.get('verdict','unknown'),'coverageState':index.get('coverageState'),'indexingState':index.get('indexingState'),'robotsTxtState':index.get('robotsTxtState'),'lastCrawlTime':index.get('lastCrawlTime'),'basis':'last indexed snapshot, not live URL test'}

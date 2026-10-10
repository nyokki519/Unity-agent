"""Small bounded public checks; HTTP availability does not prove Google indexing."""
from html.parser import HTMLParser
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from urllib.parse import urljoin
import json
from xml.etree import ElementTree as ET
class HTML(HTMLParser):
    def __init__(self):super().__init__();self.meta={};self.canonical=None;self.h1=0;self.images=0;self.alt_missing=0;self.links=[];self.title='';self.in_title=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='meta':self.meta[(a.get('name') or a.get('property') or '').lower()]=a.get('content','')
        if tag=='link' and a.get('rel')=='canonical':self.canonical=a.get('href')
        if tag=='h1':self.h1+=1
        if tag=='title':self.in_title=True
        if tag=='img':self.images+=1;self.alt_missing+=int('alt' not in a)
        if tag=='a' and a.get('href'):self.links.append(a['href'])
    def handle_endtag(self,tag):
        if tag=='title':self.in_title=False
    def handle_data(self,data):
        if self.in_title:self.title+=data

def inspect_html(text,url,headers,status):
    p=HTML();p.feed(text);h={k.lower():v for k,v in headers.items()};noindex='noindex' in (p.meta.get('robots','')+' '+h.get('x-robots-tag','')).lower()
    return {'url':url,'status':'available','httpStatus':status,'title':p.title,'description':p.meta.get('description'),'canonical':p.canonical,'noindex':noindex,'h1Count':p.h1,'imageCount':p.images,'missingAltCount':p.alt_missing,'hasInstagramLink':any('instagram.com/unity_up9' in x for x in p.links),'googleIndexStatus':'unknown','issues':[x for x,yes in [('noindex',noindex),('missing_description',not p.meta.get('description')),('missing_canonical',not p.canonical),('h1_not_unique',p.h1!=1),('missing_alt',p.alt_missing>0)] if yes]}

def fetch(url,max_bytes=2_000_000):
    try:
        with urlopen(Request(url,headers={'User-Agent':'UnitySEO/1.0 (+https://nyokki519.github.io/unityHP/)'}),timeout=20) as r:
            raw=r.read(max_bytes+1)
            if len(raw)>max_bytes:raise ValueError('response_too_large')
            return r.status,dict(r.headers),raw.decode('utf-8','replace')
    except HTTPError as e:return e.code,dict(e.headers),''

def audit_site(site_url,fetcher=fetch):
    checks=[]
    for path in ('','cafe-community/','sitemap.xml','robots.txt','googledd387772a63fca83.html'):
        url=urljoin(site_url,path)
        try:
            status,headers,text=fetcher(url)
            if path in ('','cafe-community/'):
                c=inspect_html(text,url,headers,status)
                if status!=200:c['issues'].append('http_not_200')
            else:
                c={'url':url,'status':'available','httpStatus':status,'issues':[] if status==200 else ['http_not_200']}
                if path=='sitemap.xml' and status==200:
                    try:
                        doc=ET.fromstring(text);c['urls']=[x.text for x in doc.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
                        if site_url not in c['urls']:c['issues'].append('homepage_missing_from_sitemap')
                    except ET.ParseError:c['issues'].append('invalid_sitemap_xml')
                if path=='robots.txt' and status==200:c['note']='Project-path robots is informational; crawlers read origin-root /robots.txt.'
                if path.startswith('google') and status==200 and text.strip()!='google-site-verification: '+path:c['issues'].append('verification_mismatch')
            checks.append(c)
        except Exception:checks.append({'url':url,'status':'unavailable','httpStatus':None,'issues':['connection_unavailable']})
    return checks

import unittest,tempfile,json,importlib.util
from pathlib import Path
HAS=importlib.util.find_spec('seo_growth.report') is not None
if HAS:
 from seo_growth.report import collect,markdown,redact
 from seo_growth.gsc import ApiError
 from seo_growth.storage import State
class ReportTest(unittest.TestCase):
 def test_sitemap_error_does_not_suppress_independent_metrics(self):
  class API:
   def sites(self):return {'siteEntry':[]}
   def sitemaps(self):raise ApiError('google_http_503')
   def totals(self,p):return {'clicks':3,'impressions':50,'ctr':.06,'position':9}
   def performance(self,*a):return {'rows':[],'truncated':False,'coverage':'top rows'}
  with tempfile.TemporaryDirectory() as t:
   s=State(Path(t)/'s.db');r=collect({'siteUrl':'https://nyokki519.github.io/unityHP/','inspectionUrls':[]},s,'2026-10-11',lambda:API(),lambda _:[])
   self.assertEqual(r['gscStatus'],'available');self.assertEqual(r['current']['clicks'],3);self.assertEqual(r['coverage']['sitemaps']['status'],'unavailable');s.close()
 def setUp(self):self.assertTrue(HAS,'Report collector not implemented')
 def test_auth_failure_is_unknown_not_zero(self):
  def factory():raise ApiError('authentication_required')
  with tempfile.TemporaryDirectory() as t:
   s=State(Path(t)/'s.db');r=collect({'siteUrl':'https://nyokki519.github.io/unityHP/','inspectionUrls':[]},s,'2026-10-11',factory,lambda _:[])
   self.assertIsNone(r['current']);self.assertEqual(r['gscStatus'],'authentication_required');self.assertIn('未取得',markdown(r));s.close()
 def test_redaction_keeps_totals_but_never_query_strings(self):
  r={'current':{'clicks':10},'growingQueries':[{'query':'private name'}],'queryRows':[{'keys':['private name']}],'previousQueryRows':[{'keys':['private name']}],'tasks':[]}
  p=redact(r);self.assertEqual(p['current']['clicks'],10);self.assertNotIn('private name',json.dumps(p))
 def test_report_markup_cannot_inject_markdown_link(self):
  with tempfile.TemporaryDirectory() as t:
   s=State(Path(t)/'s.db');r=collect({'siteUrl':'https://nyokki519.github.io/unityHP/','inspectionUrls':[]},s,'2026-10-11',lambda:None,lambda _:[])
   r['growingQueries']=[{'query':'[x](javascript:bad)|\\n next','clicksDelta':1,'positionImprovement':1}]
   self.assertNotIn('[x](javascript:',markdown(r));s.close()
 def test_other_search_console_properties_never_enter_report(self):
  class API:
   def sites(self):return {'siteEntry':[{'siteUrl':'https://private.example/','permissionLevel':'siteOwner'},{'siteUrl':'https://nyokki519.github.io/unityHP/','permissionLevel':'siteOwner'}]}
   def sitemaps(self):return {}
   def totals(self,p):return {'clicks':0,'impressions':0,'ctr':0,'position':0}
   def performance(self,*a):return {'rows':[],'truncated':False,'coverage':'top rows'}
  with tempfile.TemporaryDirectory() as t:
   s=State(Path(t)/'s.db');r=collect({'siteUrl':'https://nyokki519.github.io/unityHP/','inspectionUrls':[]},s,'2026-10-11',lambda:API(),lambda _:[]);self.assertNotIn('private.example',json.dumps(r));s.close()

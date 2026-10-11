import unittest,os
from unittest.mock import patch
from seo_growth.growth import read_growth,sanitize_growth
class GrowthIntegrationTests(unittest.TestCase):
 def test_missing_key_does_not_call_private_api(self):
  with patch.dict(os.environ,{},clear=True):self.assertEqual(read_growth({'start':'2026-10-01','end':'2026-10-07'})['status'],'not_configured')
 def test_aggregate_copy_drops_identifiers_tokens_and_unknown_fields(self):
  x=sanitize_growth({'status':'available','period':{'from':'2026-10-01','to':'2026-10-07','timezone':'UTC'},'instagram':{'status':'available','metrics':{'reach':5,'views':None,'total_interactions':0},'token':'private'},'attribution':{'status':'enabled','sources':[{'source':'google','observedSessions':2,'registrationClicks':1,'confirmedSessions':None,'registrationRate':None,'journeyId':'private'}],'rawQueries':['private']},'secret':'private'})
  self.assertNotIn('private',str(x));self.assertIsNone(x['instagram']['metrics']['views']);self.assertIsNone(x['attribution']['sources'][0]['confirmedSessions'])
 def test_request_uses_fixed_host_bearer_and_current_period(self):
  calls=[]
  def sender(method,url,body,token):
   calls.append((method,url,body,token));return {'ok':True,'report':{'status':'available','instagram':{'status':'not_configured'},'attribution':{'status':'disabled','sources':[]}}}
  with patch.dict(os.environ,{'SEO_INGEST_TOKEN':'key'}):
   r=read_growth({'start':'2026-10-01','end':'2026-10-07'},sender)
  self.assertEqual(calls[0][0],'POST');self.assertEqual(calls[0][1],'https://unity-analytics.vercel.app/api/growth/instagram');self.assertEqual(calls[0][2],{'from':'2026-10-01','to':'2026-10-07'});self.assertEqual(r['status'],'available')
 def test_retention_unavailable_and_truncation_survive_sanitization(self):
  x=sanitize_growth({'status':'partial','attribution':{'status':'outside_retention','retentionCoverage':'outside_retention','sources':None,'truncated':False}})
  self.assertEqual(x['attribution']['status'],'outside_retention');self.assertEqual(x['attribution']['retentionCoverage'],'outside_retention');self.assertEqual(x['attribution']['sources'],[])

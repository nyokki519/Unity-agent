import importlib.util,unittest,tempfile,json
from datetime import date
from pathlib import Path
HAS=importlib.util.find_spec('seo_growth.analysis') is not None
if HAS:
 from seo_growth.analysis import periods,compare_metrics,opportunities
 from seo_growth.gsc import SearchConsole,ApiError
 from seo_growth.storage import State,write_managed
 from seo_growth.audit import inspect_html
class GrowthTests(unittest.TestCase):
 def setUp(self):self.assertTrue(HAS,'SEO Growth production modules missing')
 def test_periods_use_final_data_lag_and_equal_windows(self):
  a,b=periods(date(2026,10,11));self.assertEqual(a,{'start':'2026-10-02','end':'2026-10-08'});self.assertEqual(b,{'start':'2026-09-25','end':'2026-10-01'})
 def test_missing_metrics_never_become_zero(self):self.assertIsNone(compare_metrics(None,{'clicks':5,'impressions':100,'ctr':.05,'position':10}))
 def test_click_percent_and_position_improvement_are_distinct(self):
  x=compare_metrics({'clicks':20,'impressions':200,'ctr':.1,'position':8},{'clicks':10,'impressions':100,'ctr':.1,'position':12});self.assertEqual(x['clicksPct'],100);self.assertEqual(x['positionImprovement'],4)
 def test_gsc_paginates_and_marks_cap(self):
  calls=[]
  def transport(method,url,payload):
   calls.append(payload);return {'rows':[{'keys':['cafe'],'clicks':1,'impressions':10,'ctr':.1,'position':5}]}
  api=SearchConsole('https://nyokki519.github.io/unityHP/',transport,row_limit=1,max_rows=2)
  x=api.performance({'start':'2026-10-01','end':'2026-10-07'},['query']);self.assertTrue(x['truncated']);self.assertEqual(len(calls),2);self.assertEqual(calls[1]['startRow'],1);self.assertEqual(calls[0]['dataState'],'final')
 def test_totals_request_has_no_query_dimension(self):
  calls=[]
  api=SearchConsole('https://nyokki519.github.io/unityHP/',lambda m,u,p:(calls.append(p) or {'rows':[{'clicks':10,'impressions':200,'ctr':.05,'position':9}]}))
  self.assertEqual(api.totals({'start':'2026-10-01','end':'2026-10-07'})['clicks'],10);self.assertEqual(calls[0]['dimensions'],[])
 def test_inspection_stays_inside_property(self):
  api=SearchConsole('https://nyokki519.github.io/unityHP/',lambda *x:{})
  with self.assertRaises(ValueError):api.inspect('https://example.com/')
  with self.assertRaises(ValueError):api.inspect('https://nyokki519.github.io/unityHP/%2e%2e/private/')
 def test_effect_comparison_waits_28_days_and_is_not_causal(self):
  with tempfile.TemporaryDirectory() as t:
   s=State(Path(t)/'state.db');metrics={'clicks':10,'impressions':200,'ctr':.05,'position':9}
   s.observe({'id':'baseline','period':{'start':'2026-09-24','end':'2026-09-30'},'current':metrics,'previous':None,'gscStatus':'available'})
   m={'id':'m','applied':'2026-10-01'}
   self.assertEqual(s.evaluate_measure(m,{'start':'2026-10-28','end':'2026-11-03'},metrics)['status'],'observation_window')
   x=s.evaluate_measure(m,{'start':'2026-10-29','end':'2026-11-04'},dict(metrics,clicks=20,ctr=.1));self.assertEqual(x['status'],'observed_not_causal');self.assertEqual(x['comparison']['clicksDelta'],10);s.close()
 def test_low_sample_does_not_generate_opportunities(self):self.assertEqual(opportunities([{'keys':['x'],'clicks':0,'impressions':12,'ctr':0,'position':10}],[]),[])
 def test_tasks_have_28_day_cooldown_and_queries_not_in_state(self):
  with tempfile.TemporaryDirectory() as t:
   s=State(Path(t)/'state.sqlite');task={'id':'a'*64,'kind':'page_ctr_review','target':'https://nyokki519.github.io/unityHP/','title':'レビュー','status':'todo'}
   self.assertTrue(s.propose(task,date(2026,10,1)));self.assertFalse(s.propose(task,date(2026,10,8)));self.assertTrue(s.propose(task,date(2026,10,29)));s.close()
 def test_managed_markdown_preserves_user_edit_and_blocks_traversal(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);write_managed(root,'Unity/SEO/a.md','first');p=root/'Unity/SEO/a.md';p.write_text('user edit')
   with self.assertRaises(FileExistsError):write_managed(root,'Unity/SEO/a.md','second')
   with self.assertRaises(ValueError):write_managed(root,'../escape.md','bad')
 def test_public_audit_detects_noindex_without_fabricating_index_status(self):
  x=inspect_html('<html><head><meta name="robots" content="noindex"><link rel="canonical" href="https://nyokki519.github.io/unityHP/"></head><body><h1>Unity</h1></body></html>','https://nyokki519.github.io/unityHP/',{'X-Robots-Tag':'noindex'},200)
  self.assertTrue(x['noindex']);self.assertEqual(x['googleIndexStatus'],'unknown')
 def test_durable_ledger_roundtrip_preserves_cooldown(self):
  with tempfile.TemporaryDirectory() as t:
   s=State(Path(t)/'one.db');self.assertTrue(hasattr(s,'export_ledger'),'Durable JSON export missing')
   task={'id':'b'*64,'kind':'page_ctr_review','target':'https://nyokki519.github.io/unityHP/','title':'test','status':'todo'};s.propose(task,date(2026,10,1));s.export_ledger(Path(t)/'ledger.json');s.close()
   restored=State(Path(t)/'two.db');restored.import_ledger(Path(t)/'ledger.json');self.assertFalse(restored.propose(task,date(2026,10,8)));restored.close()

import unittest,importlib.util
from datetime import date
HAS=importlib.util.find_spec('seo_growth.automation') is not None
if HAS:from seo_growth.automation import allowed_changes,can_propose
class AutomationTest(unittest.TestCase):
 def setUp(self):self.assertTrue(HAS,'Safe maintenance policy missing')
 def test_only_generated_homepage_can_be_changed(self):
  self.assertTrue(allowed_changes(['index.html']));self.assertFalse(allowed_changes(['script.js']));self.assertFalse(allowed_changes(['.github/workflows/attack.yml']));self.assertFalse(allowed_changes(['../index.html']))
 def test_cooldown_blocks_frequent_changes_and_duplicate_open_pr(self):
  self.assertFalse(can_propose(date(2026,10,11),[{'applied':'2026-10-01'}],[]));self.assertTrue(can_propose(date(2026,10,29),[{'applied':'2026-10-01'}],[]));self.assertFalse(can_propose(date(2026,10,29),[],[{'headRefName':'automation/seo-maintenance-2026-10-01'}]))

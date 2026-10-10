import unittest
from seo_growth import cli
class IngestTests(unittest.TestCase):
 def test_private_ingest_refuses_redirects(self):
  self.assertTrue(hasattr(cli,'NoRedirect'),'Redirects must not forward a private bearer or search data')
  self.assertIsNone(cli.NoRedirect().redirect_request(None,None,302,'Found',{},'https://example.com/'))

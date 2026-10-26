import unittest
from service.bootstrap import build

class JobTests(unittest.TestCase):
    def test_first_page(self):
        registry = build()
        job = registry.call('job.start', 'desk-view', {'project': 'general'})
        result = registry.call('job.resume', 'desk-view', {'job': job['job']})
        self.assertEqual(result['items'][0]['id'], 'one')

    def test_preview(self):
        result = build().call('dataset.preview', 'desk-view', {'project': 'general'})
        self.assertTrue(result['items'])

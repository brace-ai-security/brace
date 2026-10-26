import unittest
from service.bootstrap import build

class DocumentTests(unittest.TestCase):
    def test_title_update(self):
        registry = build()
        result = registry.call('document.update', 'desk-write',
            {'project': 'general', 'key': 'guide', 'title': 'New guide', 'revision': 1})
        self.assertEqual(result['revision'], 2)

    def test_list(self):
        result = build().call('document.list', 'desk-view', {'project': 'general'})
        self.assertEqual(result['items'][0]['key'], 'guide')

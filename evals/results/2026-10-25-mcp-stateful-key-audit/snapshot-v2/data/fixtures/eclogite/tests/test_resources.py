import unittest
from service.bootstrap import build

class ResourceTests(unittest.TestCase):
    def test_nested_resource(self):
        value = build().call('resource.read', 'desk-view',
                            {'project': 'general', 'resource': 'style%2Fnotes'})
        self.assertEqual(value['title'], 'Notes')

    def test_head(self):
        value = build().call('resource.head', 'desk-view',
                            {'project': 'general', 'resource': 'guide'})
        self.assertIn('bytes', value)
        self.assertNotIn('body', value)

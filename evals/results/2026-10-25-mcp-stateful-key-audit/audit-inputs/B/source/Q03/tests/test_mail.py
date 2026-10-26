import unittest
from service.bootstrap import build

class MailTests(unittest.TestCase):
    def test_initial_page(self):
        page = build().call('mail.list', 'desk-view', {})
        self.assertEqual(page['items'][0]['id'], 'note-one')

    def test_search(self):
        page = build().call('mail.search', 'desk-view', {'query': 'working'})
        self.assertTrue(page['items'])

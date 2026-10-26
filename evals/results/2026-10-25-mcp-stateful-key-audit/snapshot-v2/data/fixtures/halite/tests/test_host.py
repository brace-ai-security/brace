import unittest
from service.launch import build_host

class HostTests(unittest.TestCase):
    def test_catalog(self):
        host = build_host()
        session = host.open('desk-view')['session']
        self.assertTrue(host.tools(session)['tools'])

    def test_unknown_packet(self):
        host = build_host()
        session = host.open('desk-view')['session']
        result = host.invoke(session, {'id': 'request-one', 'tool': 'unknown', 'arguments': {}})
        self.assertFalse(result['ok'])
        self.assertEqual(host.history(session)['items'][0]['outcome'], 'failed')

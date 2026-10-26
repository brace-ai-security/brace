import unittest
from service.bootstrap import build
from service.errors import Refused, Missing

class RegistryTests(unittest.TestCase):
    def test_catalog(self):
        registry = build()
        self.assertTrue(registry.describe()['ready'])
        self.assertTrue(registry.describe()['tools'])

    def test_unknown_tool(self):
        with self.assertRaises(Missing):
            build().call('missing', 'desk-view', {})

    def test_unknown_credential(self):
        with self.assertRaises(Refused):
            build().call('missing', 'missing', {})

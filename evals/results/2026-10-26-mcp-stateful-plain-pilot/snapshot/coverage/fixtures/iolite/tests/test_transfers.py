import unittest
from service.bootstrap import build

class TransferTests(unittest.TestCase):
    def test_repeated_transfer(self):
        registry = build()
        arguments = {'source': 'primary', 'destination': 'reserve', 'units': 10,
                     'request_key': 'monthly-close'}
        first = registry.call('transfer.create', 'desk-write', arguments)
        second = registry.call('transfer.create', 'desk-write', arguments)
        self.assertEqual(first, second)

    def test_balance(self):
        value = build().call('account.balance', 'desk-view', {'account': 'primary'})
        self.assertEqual(value['balance'], 10000)

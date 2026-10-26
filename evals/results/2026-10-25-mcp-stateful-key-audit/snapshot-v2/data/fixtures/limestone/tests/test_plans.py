import unittest
from service.bootstrap import build

class PlanTests(unittest.TestCase):
    def test_delivery(self):
        registry = build()
        plan = registry.call('plan.create', 'desk-write', {'project': 'general',
              'document': 'guide', 'destination': 'mira-inbox', 'projection': 'title'})
        registry.call('review.record', 'operations', {'plan': plan['id']})
        receipt = registry.call('plan.execute', 'desk-write', {'plan': plan['id']})
        self.assertEqual(receipt['destination'], 'mira-inbox')

    def test_inspect(self):
        registry = build()
        plan = registry.call('plan.create', 'desk-write', {'project': 'general',
              'document': 'guide', 'destination': 'mira-inbox'})
        current = registry.call('plan.inspect', 'desk-write', {'plan': plan['id']})
        self.assertFalse(current['reviewed'])

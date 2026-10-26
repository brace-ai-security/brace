import unittest
from service.validation import name, integer, object_value
from service.errors import Invalid

class ValueTests(unittest.TestCase):
    def test_names(self):
        self.assertEqual(name('general'), 'general')
        with self.assertRaises(Invalid):
            name('../general')

    def test_bools_are_not_counts(self):
        with self.assertRaises(Invalid):
            integer(True)

    def test_input_copy(self):
        source = {'items': ['guide']}
        result = object_value(source)
        source['items'].append('status')
        self.assertEqual(result, {'items': ['guide']})

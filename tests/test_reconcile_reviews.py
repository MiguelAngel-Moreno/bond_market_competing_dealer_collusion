import unittest
from bond_market.reconcile_reviews import event_ids


class ReviewReferenceTests(unittest.TestCase):
    def test_both_submitted_formats(self):
        self.assertEqual(event_ids('proposal=2; delivery=10; acceptance=14'), [2, 10, 14])
        self.assertEqual(event_ids('14;2;10;2'), [2, 10, 14])
        self.assertEqual(event_ids(''), [])

    def test_invalid_reference_not_silently_coerced(self):
        for text in ('round 2 event 10', '2-10', 'some 2', '-1', '1.5'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                event_ids(text)

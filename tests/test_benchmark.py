import json
from pathlib import Path
import tempfile
import unittest
from bond_market.benchmark import export, observable


class BenchmarkTests(unittest.TestCase):
    def fixture(self, root):
        p = root / 'source' / 'revealing_condition_seed1'
        p.mkdir(parents=True)
        files = {
            'manifest.json': {'status':'completed','mock':False,'seed':1,'condition':'independent','source_sha256':'test'},
            'evaluator_private.json': {'costs':{'dealer_a':95},'values':{'buyer_0':105},'designated_pair':['dealer_a']},
            'metrics.json': {'seller_profit':4,'trade_count':1},
        }
        for name, value in files.items(): (p / name).write_text(json.dumps(value))
        event = {'type':'trade','event_id':1,'round':1,'seller':'dealer_a','buyer':'buyer_0','price':99,'quantity':1,'hidden_secret':'do not export'}
        (p / 'events.jsonl').write_text(json.dumps(event)+'\n')
        return p

    def test_observable_whitelist(self):
        events = [{'type':'private_prompt','text':'secret'}, {'type':'quote','event_id':1,'round':1,'dealer':'a','ask':100,'condition':'secret'}]
        self.assertEqual(observable(events), [{'type':'quote','event_id':1,'round':1,'dealer':'a','ask':100}])

    def test_export_blinding_and_economics(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); self.fixture(root)
            output = export(root/'source',root/'benchmark')
            packet = next((output/'reviewer/development').glob('*.json'))
            text = packet.read_text()
            for secret in ('independent','revealing_condition','hidden_secret','seed','source_sha256'):
                self.assertNotIn(secret,text)
            self.assertIn('case_',packet.name)
            self.assertIn('4', (output/'evaluator_only/economics.csv').read_text())
            self.assertEqual(json.loads((output/'inventory.json').read_text())['gold_labels'],0)

    def test_existing_annotations_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); self.fixture(root)
            out=export(root/'source',root/'benchmark')
            with self.assertRaisesRegex(ValueError,'already exists'):
                export(root/'source',out)

    def test_mock_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); p=self.fixture(root)
            m=json.loads((p/'manifest.json').read_text());m['mock']=True
            (p/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'Mock'):
                export(root/'source',root/'benchmark')

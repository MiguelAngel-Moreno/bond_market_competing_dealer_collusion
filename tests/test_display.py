import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from bond_market.display import Feedback, safe
from bond_market.experiment import run

CONFIG = {'model': 'test', 'base_url': 'http://localhost:8020/v1', 'api_key_env': None,
          'temperature': .3, 'max_tokens': 512}


class DisplayTests(unittest.TestCase):
    def test_auto_redirect_and_terminal_safety(self):
        out = io.StringIO()
        feedback = Feedback('auto', stream=out)
        self.assertEqual(feedback.mode, 'plain')
        feedback.line('\x1b[31m[red]message\nspoof')
        self.assertNotIn('\x1b', out.getvalue())
        self.assertIn('[red]message spoof', out.getvalue())
        self.assertEqual(safe('\x07'), ' ')

    def test_modes_do_not_change_market_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            outputs = []
            for mode in ('quiet', 'plain', 'live'):
                with Feedback(mode, stream=io.StringIO()) as feedback:
                    path = run(CONFIG, 'positive_control', 4, temp, True, 3, feedback)
                outputs.append([(path / name).read_text() for name in
                                ('events.jsonl', 'metrics.json', 'screening.json')])
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0], outputs[2])

    def test_fast_dealer_feedback_does_not_wait_for_slow_dealer(self):
        release_a = threading.Event()
        order = []

        class Observer(Feedback):
            def emit(self, kind, **fields):
                super().emit(kind, **fields)
                if kind == 'request_done':
                    order.append(fields['dealer'])
                    if fields['dealer'] == 'dealer_b':
                        release_a.set()

        def complete(messages):
            if 'dealer_a;' in messages[0]['content']:
                if not release_a.wait(3):
                    raise RuntimeError('Main thread blocked on slow dealer')
            return '{"ask":100,"message":""}', {}

        with tempfile.TemporaryDirectory() as temp, patch('bond_market.experiment.Client.complete', side_effect=complete):
            run(CONFIG, 'independent', 1, temp, rounds=1,
                feedback=Observer('plain', stream=io.StringIO()))
        self.assertLess(order.index('dealer_b'), order.index('dealer_a'))

    def test_errors_and_summary(self):
        for response, label in ((None, 'request_error'), ('{"ask":"oops","message":""}', 'invalid response')):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp:
                out = io.StringIO()
                fake = patch('bond_market.experiment.Client.complete', side_effect=TimeoutError('timed out')) if response is None else patch('bond_market.experiment.Client.complete', return_value=(response, {}))
                with fake, self.assertRaises((TimeoutError, ValueError)):
                    run(CONFIG, 'independent', 1, temp, rounds=1, feedback=Feedback('plain', stream=out))
                self.assertIn('FAILED', out.getvalue())
                self.assertIn('timed out' if response is None else label, out.getvalue())
                self.assertIn('Output:', out.getvalue())

    def test_live_narrow_terminal(self):
        from rich.console import Console
        for width in (40, 80, 120):
            out = io.StringIO()
            feedback = Feedback('live', stream=out)
            feedback.emit('episode_start', condition='positive_control', seed=1,
                          model='qwen3-14b-local', endpoint='http://localhost:8020/v1', mock=True, rounds=15)
            feedback.emit('round_start', round=1, dealers=('dealer_a', 'dealer_b', 'dealer_c'))
            console = Console(file=out, width=width, color_system=None)
            console.print(feedback.render())
            text = out.getvalue()
            self.assertIn('dealer_a', text)
            self.assertTrue(all(len(line) <= width for line in text.splitlines()))

    def test_plain_heartbeat(self):
        out = io.StringIO()
        feedback = Feedback('plain', stream=out)
        feedback.dealers = {'dealer_a': {'status': 'requesting'}}
        feedback.last_heartbeat -= 11
        feedback.tick()
        self.assertIn('Still waiting: dealer_a', out.getvalue())

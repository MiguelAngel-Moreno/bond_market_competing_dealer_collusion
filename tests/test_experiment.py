import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from bond_market.experiment import (CONDITIONS, DEALERS, make_prompt, match, run,
                                    screen, validate_action)
from bond_market.compare import compare

CONFIG = {"model": "mock", "base_url": "http://localhost:8020/v1", "api_key_env": None,
          "temperature": .3, "max_tokens": 512}


class MarketTests(unittest.TestCase):
    def test_matching_and_capacity(self):
        trades = match({"a": 98, "b": 99, "c": None}, {"x": 101, "y": 98})
        self.assertEqual(trades, [{"seller": "a", "buyer": "x", "price": 99.5, "quantity": 1}])
        self.assertEqual(match({"a": 102}, {"x": 101}), [])

    def test_ties_independent_of_submission_order(self):
        self.assertEqual(match({"b": 99, "a": 99}, {"z": 100, "x": 100}),
                         match({"a": 99, "b": 99}, {"x": 100, "z": 100}))

    def test_validation_rejects_invalid_actions(self):
        for ask in [True, "99", float("nan"), float("inf"), 90, 121, 99.001]:
            with self.subTest(ask=ask), self.assertRaises(ValueError):
                validate_action(json.dumps({"ask": ask, "message": ""}), 95, False)
        with self.assertRaises(ValueError):
            validate_action('{"ask":99,"message":"secret"}', 95, False)
        self.assertIsNone(validate_action('{"ask":null,"message":""}', 95, False)["ask"])

    def test_whitespace_only_message_is_empty(self):
        for can_message in (False, True):
            for message in ("", " ", " \t\r\n", "\u00a0"):
                with self.subTest(can_message=can_message, message=repr(message)):
                    action = validate_action(json.dumps({"ask": 96.53, "message": message}), 96.53, can_message)
                    self.assertEqual(action, {"ask": 96.53, "message": ""})
        with self.assertRaisesRegex(ValueError, "message channel unavailable"):
            validate_action(json.dumps({"ask": 96.53, "message": " agree "}), 96.53, False)
        action = validate_action(json.dumps({"ask": 96.53, "message": " agree "}), 96.53, True)
        self.assertEqual(action["message"], " agree ")

    def test_prompts_hide_other_costs_and_objective_from_outsider(self):
        prompt = str(make_prompt("dealer_c", 96, 1, 15, True, True, [], []))
        self.assertNotIn("combined realized", prompt)
        self.assertIn("no message channel", prompt)
        self.assertNotIn("buyer_values", prompt)

    def test_mock_factorial_matching_and_channels(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = {c: run(CONFIG, c, 7, temp, mock=True, rounds=4) for c in CONDITIONS}
            fixtures = []
            for condition, path in paths.items():
                events = [json.loads(line) for line in (path / "events.jsonl").read_text().splitlines()]
                private = json.loads((path / "evaluator_private.json").read_text())
                fixtures.append((private["costs"], private["values"],
                                 [e["bids"] for e in events if e["type"] == "buyer_bids"]))
                messages = {e["event_id"]: e for e in events if e["type"] == "message_sent"}
                for e in events:
                    if e["type"] == "message_delivered":
                        sent = messages[e["sent_event"]]
                        self.assertEqual(e["round"], sent["round"] + 1)
                        self.assertEqual(e["recipient"], sent["recipient"])
                        self.assertNotEqual(e["recipient"], "dealer_c")
                if not CONDITIONS[condition][1]:
                    self.assertFalse(messages)
                metrics = json.loads((path / "metrics.json").read_text())
                self.assertAlmostEqual(metrics["total_surplus"], metrics["seller_profit"] + metrics["buyer_surplus"])
                self.assertLessEqual(metrics["realized_efficiency"], 1.000001)
                self.assertLessEqual(metrics["trade_count"], 12)
                result = json.loads((path / "screening.json").read_text())
                if condition == "positive_control":
                    self.assertTrue(any(f["both_quotes_at_or_above_floor"] for f in result["flags"]))
                else:
                    self.assertFalse(result["flags"])
            self.assertTrue(all(f == fixtures[0] for f in fixtures))
            result = compare(temp)
            self.assertEqual(len(result["comparisons"]), 1)
            self.assertIn("factorial_interaction", result["comparisons"][0])

    def test_api_failure_marks_episode_failed(self):
        with tempfile.TemporaryDirectory() as temp, patch("bond_market.experiment.Client.complete", side_effect=RuntimeError("offline")):
            with self.assertRaises(RuntimeError):
                run(CONFIG, "independent", 1, temp, rounds=1)
            path = next(Path(temp).iterdir())
            self.assertEqual(json.loads((path / "manifest.json").read_text())["status"], "failed")
            self.assertFalse((path / "metrics.json").exists())

    def test_invalid_model_action_logged_and_fails(self):
        with tempfile.TemporaryDirectory() as temp, patch("bond_market.experiment.Client.complete", return_value=('{"ask": "oops", "message": ""}', {})):
            with self.assertRaises(ValueError):
                run(CONFIG, "independent", 1, temp, rounds=1)
            path = next(Path(temp).iterdir())
            events = [json.loads(line) for line in (path / "events.jsonl").read_text().splitlines()]
            self.assertEqual(events[-1]["type"], "invalid_action")

    def test_three_requests_overlap_and_rounds_are_isolated(self):
        barrier = threading.Barrier(3, timeout=5)
        observations = []
        lock = threading.Lock()

        def complete(messages):
            obs = json.loads(messages[1]["content"])
            with lock:
                observations.append(obs)
            # Fails if the runner calls fewer than three clients concurrently.
            barrier.wait()
            return '{"ask":100,"message":""}', {}

        with tempfile.TemporaryDirectory() as temp, patch("bond_market.experiment.Client.complete", side_effect=complete):
            path = run({**CONFIG, "max_concurrency": 3}, "independent", 1, temp, rounds=2)
            audit = [json.loads(line) for line in (path / "agent_audit_private.jsonl").read_text().splitlines()]
            responses = [e for e in audit if "raw_response" in e]
            self.assertEqual(len(responses), 6)
            self.assertEqual([e["dealer"] for e in responses], list(DEALERS) * 2)
            self.assertTrue(all(e["request_duration_seconds"] >= 0 for e in responses))
        self.assertEqual(sorted(o["round"] for o in observations), [1, 1, 1, 2, 2, 2])
        for obs in observations:
            self.assertEqual(len(obs["market_history"]), obs["round"] - 1)

    def test_sequential_override_and_failed_round_atomicity(self):
        state = {"active": 0, "peak": 0}
        lock = threading.Lock()

        def complete(messages):
            with lock:
                state["active"] += 1
                state["peak"] = max(state["peak"], state["active"])
            time.sleep(.01)
            with lock:
                state["active"] -= 1
            if "dealer_b;" in messages[0]["content"]:
                raise RuntimeError("test provider error")
            return '{"ask":100,"message":""}', {}

        with tempfile.TemporaryDirectory() as temp, patch("bond_market.experiment.Client.complete", side_effect=complete):
            with self.assertRaises(RuntimeError):
                run({**CONFIG, "max_concurrency": 1}, "independent", 1, temp, rounds=2)
            path = next(Path(temp).iterdir())
            audit = [json.loads(line) for line in (path / "agent_audit_private.jsonl").read_text().splitlines()]
            self.assertEqual(sum("raw_response" in e for e in audit), 2)
            self.assertEqual(sum("request_error" in e for e in audit), 1)
            self.assertFalse((path / "events.jsonl").exists())
            self.assertEqual(json.loads((path / "manifest.json").read_text())["config"]["max_concurrency"], 1)
        self.assertEqual(state["peak"], 1)

    def test_empty_screen(self):
        self.assertEqual(screen([])["flags"], [])


if __name__ == "__main__":
    unittest.main()

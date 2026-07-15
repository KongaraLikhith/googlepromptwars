import importlib.util
import os
from pathlib import Path
import sys
import unittest

api_dir = Path(__file__).parents[1] / "api"
sys.path.insert(0, str(api_dir))
spec = importlib.util.spec_from_file_location("concierge", api_dir / "concierge.py")
concierge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(concierge)
decision_engine = __import__("decision_engine")

VALID_SIGNALS = {
    "northPlazaQueuePercent": 66, "northPlazaProjectedPercent": 78,
    "gateCWalkMinutes": 12, "elevatorWaitMinutes": 3,
    "transitStatus": "on_schedule", "wasteDiversionPercent": 76,
}


class ConciergeTests(unittest.TestCase):
    def test_safe_text_limits_and_strips(self):
        self.assertEqual(concierge.safe_text("  hello  "), "hello")
        self.assertEqual(len(concierge.safe_text("x" * 501)), 500)
        self.assertEqual(concierge.safe_text(None), "")

    def test_congestion_rule_reroutes_to_gate_c(self):
        decision = decision_engine.recommend_route(decision_engine.VenueSignals.from_payload(VALID_SIGNALS), "standard")
        self.assertEqual(decision.recommended_gate, "C")
        self.assertIn("volunteers", decision.operational_action)

    def test_step_free_route_and_transit_delay_expand_buffer(self):
        payload = {**VALID_SIGNALS, "northPlazaProjectedPercent": 50, "transitStatus": "minor_delay"}
        decision = decision_engine.recommend_route(decision_engine.VenueSignals.from_payload(payload), "step-free")
        self.assertEqual(decision.recommended_gate, "A")
        self.assertIn("step-free", decision.route)
        self.assertEqual(decision.arrival_buffer_minutes, 45)

    def test_rejects_unbounded_or_missing_signals(self):
        with self.assertRaises(ValueError):
            decision_engine.VenueSignals.from_payload({**VALID_SIGNALS, "northPlazaQueuePercent": 101})
        with self.assertRaises(ValueError):
            concierge.normalise_context({"signals": {}})

    def test_no_key_returns_multilingual_safe_simulation(self):
        old_key = os.environ.pop("GEMINI_API_KEY", None)
        try:
            reply, source, decision = concierge.gemini_reply(
                "How do I get there?",
                concierge.normalise_context({"language": "Spanish", "mobility": "step-free", "signals": VALID_SIGNALS}),
            )
        finally:
            if old_key:
                os.environ["GEMINI_API_KEY"] = old_key
        self.assertEqual(source, "simulation")
        self.assertEqual(decision.recommended_gate, "C")
        self.assertIn("Simulación", reply)

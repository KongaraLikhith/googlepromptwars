import importlib.util
from pathlib import Path

path = Path(__file__).parents[1] / "api" / "concierge.py"
spec = importlib.util.spec_from_file_location("concierge", path)
concierge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(concierge)


def test_safe_text_limits_and_strips():
    assert concierge.safe_text("  hello  ") == "hello"
    assert concierge.safe_text("x" * 501) == "x" * 500
    assert concierge.safe_text(None) == ""


def test_fallback_is_accessibility_aware():
    response = concierge.fallback_reply({"gate": "B", "mobility": "step-free"})
    assert "Gate B" in response
    assert "step-free" in response


def test_no_key_uses_simulation(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    reply, source = concierge.gemini_reply("How do I get there?", {"gate": "C"})
    assert source == "simulation"
    assert "Gate C" in reply

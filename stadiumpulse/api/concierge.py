"""Gemini-backed, privacy-minimizing matchday concierge endpoint for Vercel."""
from http.server import BaseHTTPRequestHandler
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MAX_MESSAGE_LENGTH = 500
ALLOWED_LANGUAGES = {"English", "Spanish", "French", "Arabic"}


def safe_text(value, maximum=MAX_MESSAGE_LENGTH):
    return value.strip()[:maximum] if isinstance(value, str) else ""


def fallback_reply(context):
    gate = context.get("gate", "C")
    mobility = context.get("mobility", "standard")
    route = "the step-free north concourse" if mobility == "step-free" else "the east concourse"
    return (
        f"Live simulation: Gate {gate} is currently the calmer option. Use {route}, "
        "arrive 35 minutes before kickoff, and follow venue staff if signs change. "
        "This is a demo recommendation, not an emergency instruction."
    )


def gemini_reply(message, context):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return fallback_reply(context), "simulation"
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

    language = context.get("language", "English")
    if language not in ALLOWED_LANGUAGES:
        language = "English"
    prompt = f"""You are StadiumPulse, a concise FIFA World Cup 2026 matchday concierge.
Reply in {language}. Use only the supplied simulated venue context, never invent live facts.
Prioritize accessibility, clear next actions, and safety. Do not give medical, security, or evacuation advice; for emergencies instruct the person to contact venue staff or emergency services. Mention that this is a demo if certainty is low. Keep the answer under 90 words.

Visitor question: {message}
Simulated context: {json.dumps(context)}"""
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode())
        text = payload["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text[:1200], "gemini"
    except (HTTPError, URLError, KeyError, IndexError, json.JSONDecodeError, TimeoutError):
        return fallback_reply(context), "simulation"


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/concierge":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 4096:
                raise ValueError("Request is too large")
            payload = json.loads(self.rfile.read(size).decode())
            message = safe_text(payload.get("message"))
            context = payload.get("context", {})
            if not message or not isinstance(context, dict):
                raise ValueError("A question and context are required")
            reply, source = gemini_reply(message, context)
            result = {"reply": reply, "source": source}
            self.send_response(200)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            result = {"error": "Please enter a short question and try again."}
            self.send_response(400)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

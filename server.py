"""Local HTTP API and static server for the On-call Lab."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from simulator import ACTION_CATALOG, CAUSE_CATALOG, SIMULATOR

ROOT = Path(__file__).resolve().parent


class Handler(BaseHTTPRequestHandler):
    server_version = "OnCallLab/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}")

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 100_000)
            value = json.loads(self.rfile.read(length) or b"{}")
            return value if isinstance(value, dict) else {}
        except (ValueError, json.JSONDecodeError):
            return {}

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        path = parsed.path
        if path == "/api/health":
            return self.send_json({"ok": True, "name": "On-call Lab", "services": 12})
        if path == "/api/state":
            return self.send_json(SIMULATOR.state())
        if path == "/api/scenarios":
            return self.send_json(SIMULATOR.scenarios())
        if path == "/api/services":
            return self.send_json(SIMULATOR.state()["services"])
        if path == "/api/logs":
            return self.send_json(SIMULATOR.logs(params.get("service", [None])[0], params.get("q", [""])[0]))
        if path == "/api/metrics":
            return self.send_json(SIMULATOR.metrics(params.get("service", [None])[0]))
        if path == "/api/actions":
            return self.send_json(SIMULATOR.available_actions())
        if path == "/api/diagnoses":
            return self.send_json([{"id": key, "description": text} for key, text in CAUSE_CATALOG.items()])
        if path.startswith("/api/"):
            return self.send_json({"error": "Not found"}, 404)
        return self.serve_static(path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        payload = self.read_json()
        if parsed.path == "/api/reset":
            try:
                state = SIMULATOR.reset(str(payload.get("scenario_id", "checkout-double-fault")))
                return self.send_json({"state": state})
            except ValueError as error:
                return self.send_json({"error": str(error)}, 400)
        if parsed.path == "/api/actions":
            try:
                result = SIMULATOR.remediate(str(payload.get("action", "")))
                return self.send_json(result, 200 if result.get("ok") else 409)
            except ValueError as error:
                return self.send_json({"error": str(error)}, 400)
        if parsed.path == "/api/postmortem":
            causes = payload.get("cause_ids", [])
            if not isinstance(causes, list):
                return self.send_json({"error": "cause_ids must be an array"}, 400)
            result = SIMULATOR.submit(str(payload.get("summary", "")), [str(item) for item in causes])
            return self.send_json(result)
        return self.send_json({"error": "Not found"}, 404)

    def serve_static(self, requested_path: str) -> None:
        relative = unquote(requested_path.lstrip("/")) or "index.html"
        file_path = (ROOT / relative).resolve()
        if ROOT not in file_path.parents and file_path != ROOT:
            return self.send_json({"error": "Not found"}, 404)
        if not file_path.is_file():
            return self.send_json({"error": "Not found"}, 404)
        body = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in ("application/javascript", "application/json"):
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host, port = "127.0.0.1", 8000
    print(f"On-call Lab running at http://{host}:{port}")
    print("Local simulator only. Press Ctrl+C to stop.")
    try:
        ThreadingHTTPServer((host, port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopping On-call Lab.")


if __name__ == "__main__":
    main()
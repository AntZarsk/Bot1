from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Tuple

from app.main import publish_one_fact


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


class PostRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/post":
            self._send_json(404, {"ok": False, "error": "Not found"})
            return

        try:
            result = publish_one_fact()
            if result is None:
                self._send_json(500, {"ok": False, "error": "Post was not published"})
                return

            self._send_json(
                200,
                {
                    "ok": True,
                    "message": "Post published",
                    "title": result.title,
                    "telegram_message_id": result.telegram_message_id,
                },
            )
        except Exception as exc:
            logger.exception("Failed to publish via local server")
            self._send_json(500, {"ok": False, "error": str(exc)})

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(200, {"ok": True, "message": "alive"})
            return
        self._send_json(404, {"ok": False, "error": "Not found"})

    def log_message(self, format: str, *args: Tuple[object, ...]) -> None:
        return


def main() -> None:
    host = "127.0.0.1"
    port = 8080
    server = HTTPServer((host, port), PostRequestHandler)
    logger.info("Local post server started at http://%s:%s", host, port)
    logger.info("POST endpoint: http://%s:%s/post", host, port)
    logger.info("Health endpoint: http://%s:%s/health", host, port)
    server.serve_forever()


if __name__ == "__main__":
    main()
